INPUT_FILE = "stm_datasheet_all.pdf"  # 다운로드 받은 원본 파일명
OUTPUT_FILE = "stm32_uart_extract.pdf" # 결과 파일명

import re
from pypdf import PdfReader, PdfWriter

def smart_extract_sections(input_path, output_path, section_keywords):
    """
    input_path: 원본 PDF 경로
    output_path: 저장할 PDF 경로
    section_keywords: 찾을 챕터의 제목 키워드 리스트 (순서대로 검색됨)
                      예: ["Memory map", "Power control"]
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()
    total_pages = len(reader.pages)
    
    print(f"[{input_path}] 파일 로드 중... (총 {total_pages} 페이지)")
    print("섹션 위치를 자동으로 탐색합니다. 잠시만 기다려주세요...")

    # 결과를 저장할 딕셔너리 {키워드: 시작페이지}
    found_pages = {}
    
    # 1. 페이지를 순회하며 키워드 찾기 (속도를 위해 앞부분 텍스트만 검사)
    for i in range(total_pages):
        try:
            # 페이지의 텍스트 추출
            page_text = reader.pages[i].extract_text()
            if not page_text: continue
            
            # 페이지의 첫 200글자만 확인 (제목은 보통 맨 위에 있으므로)
            header_text = page_text[:200] 
            
            for keyword in section_keywords:
                # 이미 찾은 키워드는 건너뜀
                if keyword in found_pages: continue
                
                # 키워드가 헤더에 포함되어 있으면 저장 (대소문자 무시)
                if keyword.lower() in header_text.lower():
                    print(f"  -> 찾음! '{keyword}': {i+1} 페이지")
                    found_pages[keyword] = i
                    
        except Exception as e:
            # 이미지 페이지만 있는 경우 등 에러 무시
            continue

    # 2. 찾은 페이지부터 일정량 추출 (챕터 길이를 모르므로 여유있게 20페이지씩 or 다음 챕터 전까지)
    #    STM32 매뉴얼은 챕터가 꽤 길 수 있으므로, 여기서는 
    #    "찾은 페이지부터 ~ 15페이지"를 기본으로 추출하도록 설정합니다.
    #    (필요하면 이 길이를 늘리세요)
    
    EXTRACT_LENGTH = 20  # 각 섹션 당 추출할 페이지 수 (넉넉하게 설정)

    pages_to_extract = set() # 중복 방지용

    for keyword in section_keywords:
        if keyword in found_pages:
            start_idx = found_pages[keyword]
            end_idx = min(start_idx + EXTRACT_LENGTH, total_pages)
            
            # 페이지 인덱스 추가
            for p in range(start_idx, end_idx):
                pages_to_extract.add(p)
        else:
            print(f"  [주의] '{keyword}' 섹션을 찾지 못했습니다. 키워드를 확인해주세요.")

    # 3. 페이지 번호 순서대로 정렬하여 PDF 생성
    if not pages_to_extract:
        print("추출할 페이지를 찾지 못했습니다.")
        return

    sorted_pages = sorted(list(pages_to_extract))
    
    for p_idx in sorted_pages:
        writer.add_page(reader.pages[p_idx])

    # 저장
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"\n[성공] '{output_path}' 파일 생성 완료! (총 {len(sorted_pages)} 페이지)")

# 찾고 싶은 챕터의 핵심 단어들 (Reference Manual 목차에 나오는 단어여야 함)
TARGET_KEYWORDS = [
    "Memory map",           # 1. 메모리 맵
    "Power control (PWR)",  # 2. 전원 제어
    "Backup registers",     # 3. 백업 레지스터
    "UART",
]

if __name__ == "__main__":
    smart_extract_sections(INPUT_FILE, OUTPUT_FILE, TARGET_KEYWORDS)