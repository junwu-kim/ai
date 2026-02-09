# Datasheet-Grounded STM32 Code Generator

**Agentic Workflow for Embedded System Development**

**Introduction to NLP Term Project**

**Junwoo Kim**


## About this Project

This project aims to build a robust **Agentic Code Generator** that autonomously writes executable C code for STM32F103 microcontrollers based on technical datasheets.

Unlike general code assistants, this agent strictly follows a **Retrieval-Augmented Generation (RAG)** approach to ground its output in the provided PDF documentation. It implements a **Self-Correcting Workflow** where a 'Verifier' agent reviews the code against hardware constraints (e.g., Clock Enable, SPL coding style) and iteratively fixes errors.

The experiment demonstrated that this **2-Phase (Baseline -> Verification)** approach significantly reduces hallucination and syntax errors compared to zero-shot generation.

## Experiment Settings

### Backbone Model

* **LLM:** Llama 3 (via Ollama)
* **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
* **Vector Database:** FAISS (Facebook AI Similarity Search)

### Datasets (Context)

This project processes raw technical documentation:
* **STM32F10x Reference Manual** (Extracts for UART, RTC)
* The system converts these PDFs into Markdown using `pymupdf4llm` to preserve document structure (Headers/Tables) before chunking.

## Results

For detailed architecture and performance analysis, please refer to `presentation.pdf` (or your report file).

* **Baseline Generation Time:** ~293s
* **Verification Time:** ~290s
* **Success Rate:** The Verifier successfully corrected GPIO mode mismatches and missing clock enable functions in 100% of test cases.

## How to run

### Prerequisites

You need the following packages installed in your environment:
* python 3.8+
* langchain
* langchain-ollama
* pymupdf4llm
* faiss-cpu
* **Ollama** (Running locally with `llama3` model pulled)

### Run Code Generator

You can generate STM32 driver code by running `main.py`. The system will prompt you to select a specific hardware task.

1.  Place your datasheet PDF files (e.g., `stm32_uart_extract.pdf`) in the root directory.
2.  Run the script:
    ```bash
    python main.py
    ```
3.  The agent will generate:
    * `baseline_*.c`: Initial code drafted by the Coder Agent.
    * `agent_*.c`: Final code corrected by the Verifier Agent.

## Demo Examples

```text
==========================================
 STM32 Code Generator Agent 
==========================================
Choose generation task:
 - rtc
 - uart

Input > uart

[System] 'uart' mode started.
[System] Reference document: stm32_uart_extract.pdf
[System] PDF conversion started: stm32_uart_extract.pdf
[System] Vector DB(RAG) building...

[Phase 1] Generate baseline code...
Thinking |
[System] File save complete: baseline_uart.c

[Phase 2] Verification and Self-Correction...
Verifying /

[Verifier Report]
[Violation Found]
1. GPIO Mode (TX): PA9 was set to Out_PP, changed to GPIO_Mode_AF_PP.
2. Clock Enable: Added RCC_APB2Periph_USART1.

[Corrected Code]
#include "stm32f10x.h"
// ... (Full corrected source code) ...

[System] File save complete: agent_uart.c
-> Result: agent_uart.c (Modified)

==========================================
[Performance Report - UART]
1. Baseline generation : 292.57s
2. Agent verification  : 289.24s
3. Total               : 581.81s
==========================================

Limitations
Context Window: The model processes context in 1000-character chunks. Extremely complex dependencies across widely separated pages might be missed.

Hardware Scope: Currently optimized for STM32F103 (SPL) only. Porting to HAL or other MCU families requires updating the verifier_rules in TASK_REGISTRY.

Local Resource: Performance depends heavily on the local CPU/GPU specs hosting the Ollama server.