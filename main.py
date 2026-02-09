import os
import sys
import re
import time
import threading
import itertools
from langchain_ollama import ChatOllama

import warnings
import logging

# Remove warning log
warnings.filterwarnings("ignore")
try:
    from transformers import logging as hf_logging
    hf_logging.set_verbosity_error()
except ImportError:
    pass
logging.getLogger("langchain").setLevel(logging.ERROR)

# Show processing spinner
class Spinner:
    def __init__(self, message="Processing..."):
        self.message = message
        self.stop_running = False
        self.thread = threading.Thread(target=self._animate)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_running = True
        self.thread.join()
        sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()

    def _animate(self):
        chars = itertools.cycle(['|', '/', '-', '\\'])
        while not self.stop_running:
            sys.stdout.write(f'\r{self.message} {next(chars)}')
            sys.stdout.flush()
            time.sleep(0.1)

try:
    import pymupdf4llm
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_community.chat_models import ChatOllama
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough
except ImportError as e:
    print(f"Error load library: {e}")
    sys.exit(1)

TASK_REGISTRY = {
    "rtc": {
        "pdf_path": "stm32_rtc_extract.pdf",
        "md_cache": "stm32_rtc_cache.md",
        "baseline_file": "baseline_rtc.c",
        "agent_file": "agent_rtc.c",
        "question": "STM32F103에서 LSE(외부 저속 클럭)를 사용하여 RTC를 초기화하고 1초마다 인터럽트를 발생시키는 코드를 작성해줘.",

        # RTC
        "verifier_rules": """
        [필수 점검 항목]
        1. **Clock Enable**: `RCC_APB1` 버스에서 `PWR`(Power) 및 `BKP`(Backup) 클럭을 활성화하는 코드를 추가하세요.
        2. **Access Enable**: 백업 도메인 쓰기 보호를 해제(Backup Access Cmd)하세요.
        """
    },

    "uart": {
        "pdf_path": "stm32_uart_extract.pdf",
        "md_cache": "stm32_uart_cache.md",
        "baseline_file": "baseline_uart.c",
        "agent_file": "agent_uart.c",
        "question": "STM32F103 USART1(PA9, PA10)을 9600bps로 초기화하고 RX 인터럽트에서 에코백(Echo-back)하는 코드를 작성해줘.",

        # USART
        "verifier_rules": """
        [필수 점검 항목]
        1. **Clock Enable**: `RCC_APB2` 버스에서 `GPIOA` (핀용)와 `USART1` (통신용) 클럭을 둘 다 켰는가?
        2. **GPIO Mode (TX)**: PA9(TX) 핀의 모드가 `GPIO_Mode_AF_PP` (Alternate Function)로 설정되었는가? (일반 Out_PP 금지)
        3. **GPIO Mode (RX)**: PA10(RX) 핀의 모드가 `GPIO_Mode_IN_FLOATING` 또는 `GPIO_Mode_IPU`인가?
        4. **Interrupt**: `NVIC` 설정과 `USART_IT_RXNE` 활성화가 되어 있는가?
        """
    }
}

MODEL_NAME = "llama3"
EMBEDDING_DEVICE = "cpu"

def extract_code_block(text):
    pattern = r"```c(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

def save_to_file(content, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[System] File save complete: {filename}")

def load_and_process_data(pdf_path, md_path):
    if not os.path.exists(pdf_path):
        print(f"\n[Error] PDF file not found: {pdf_path}")
        print("Please place the file in the same folder as the script.")
        sys.exit(1)

    if not os.path.exists(md_path):
        print(f"[System] PDF conversion started: {pdf_path}")
        md_text = pymupdf4llm.to_markdown(pdf_path)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_text)

    with open(md_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    headers = [("#", "H1"), ("##", "H2"), ("###", "H3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
    md_splits = markdown_splitter.split_text(full_text)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return text_splitter.split_documents(md_splits)

def initialize_agent(splits):
    print("[System] Vector DB(RAG) building...")
    embedding_model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': EMBEDDING_DEVICE}
    )
    vectorstore = FAISS.from_documents(documents=splits, embedding=embedding_model)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
    llm = ChatOllama(model=MODEL_NAME, temperature=0)
    return retriever, llm

def main():
    # 1. User input
    print("\n==========================================")
    print(" STM32 Code Generator Agent ")
    print("==========================================")
    print("Choose generation task:")
    for key in TASK_REGISTRY.keys():
        print(f" - {key}")

    selected_task = input("\nInput > ").strip().lower()

    if selected_task not in TASK_REGISTRY:
        print("[Error] Invalid input. Exiting program.")
        return

    # Load selected configuration
    config = TASK_REGISTRY[selected_task]
    print(f"\n[System] '{selected_task}' mode started.")
    print(f"[System] Reference document: {config['pdf_path']}")

    # 2. Load data and initialize agent
    splits = load_and_process_data(config['pdf_path'], config['md_cache'])
    retriever, llm = initialize_agent(splits)

    # ---------------------------------------------------------
    # [Phase 1] Baseline Generation
    # ---------------------------------------------------------
    coder_template = """
    당신은 임베디드 C 언어 개발자입니다. 
    제공된 문서를 참고하여 아래 요구사항에 맞는 코드를 작성하세요.

    [User Request]
    {question}

    [Context]
    {context}

    [지침]
    1. 레지스터 직접 제어보다는 SPL(Standard Peripheral Library) 스타일을 선호합니다.
    2. 코드는 ```c 블록 안에 작성하세요.
    """
    coder_prompt = ChatPromptTemplate.from_template(coder_template)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    coder_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | coder_prompt
        | llm
        | StrOutputParser()
    )

    print(f"\n[Phase 1] Generate baseline code...")
    start_base = time.time()
    with Spinner("Thinking"): 
        baseline_response = coder_chain.invoke(config['question'])
    end_base = time.time()

    baseline_code = extract_code_block(baseline_response)
    save_to_file(baseline_code, config['baseline_file'])

    # ---------------------------------------------------------
    # [Phase 2] Agent Verification
    # ---------------------------------------------------------
    print(f"\n[Phase 2] Verification and Self-Correction...")

    verifier_template = """
    당신은 '임베디드 코드 통합 컴파일러'입니다. 
    제공된 [Generated Code]를 검토하고, 다음 필수 규칙을 확인하세요.

    {rules}

    [출력 지침] - **매우 중요 (엄격 준수)**
    1. 규칙을 위반하여 코드를 수정해야 할 경우, **반드시 파일의 첫 줄(#include)부터 파일의 끝까지 모든 코드를 출력하세요.**
    2. 절대로 `// ... (rest of code)` 나 `// ... same as above` 와 같은 주석으로 코드를 생략하지 마세요. 생략된 코드는 컴파일 에러를 유발합니다.
    3. 수정 사항이 단 한 줄이라도 있다면, **전체 소스 코드(Full Source Code)**를 다시 생성해야 합니다.
    4. 수정할 내용이 완벽하게 없다면 "PASS"라고만 답하세요.
    5. 코드는 반드시 ```c 블록 안에 작성하세요.

    [Generated Code]
    {code}
    """

    # Insert rules from config
    final_verifier_prompt = verifier_template.format(
        rules=config['verifier_rules'], 
        code="{code}"
    )

    # Create promptTemplate
    verifier_prompt_obj = ChatPromptTemplate.from_template(final_verifier_prompt)

    verifier_chain = (
        verifier_prompt_obj
        | llm
        | StrOutputParser()
    )

    start_agent = time.time()
    with Spinner("Verifying"):
        agent_response = verifier_chain.invoke({"code": baseline_response})
    end_agent = time.time()

    print("\n[Verifier Report]")
    print(agent_response)

    if "```c" in agent_response:
        final_code = extract_code_block(agent_response)
        save_to_file(final_code, config['agent_file'])
        print(f"-> Result: {config['agent_file']} (Modified)")
    else:
        save_to_file(baseline_code, config['agent_file'])
        print(f"-> Result: {config['agent_file']} (No changes)")

    # ---------------------------------------------------------
    # Result Report
    # ---------------------------------------------------------
    base_time = end_base - start_base
    agent_time = end_agent - start_agent
    total_time = base_time + agent_time

    print("\n==========================================")
    print(f"[Performance Report - {selected_task.upper()}]")
    print(f"1. Baseline generation : {base_time:.2f}s")
    print(f"2. Agent verification  : {agent_time:.2f}s")
    print(f"3. Total              : {total_time:.2f}s")
    print("==========================================")

if __name__ == "__main__":
    main()