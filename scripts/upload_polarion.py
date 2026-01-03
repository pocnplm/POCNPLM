import os
import sys
import json
import requests

# 로그용 색상 코드
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log(msg):
    print(f"{GREEN}{BOLD}[POLARION-UPLOAD] {msg}{RESET}")

def sanitize(value):
    """
    문자열에 포함된 한글, 특수문자, 공백 등을 강제로 제거하고 순수 영어/숫자만 남김.
    Header에 들어갈 토큰이나 경로가 오염되는 것을 방지함.
    """
    if not value:
        return ""
    # 1. 문자열로 변환
    s = str(value)
    # 2. 양쪽 공백 제거
    s = s.strip()
    # 3. ASCII가 아닌 문자(한글 등)는 무시하고 제거 (errors='ignore')
    return s.encode('ascii', errors='ignore').decode('ascii')

def main():
    log("Starting Polarion upload process...")

    # 1. 환경변수 가져오기 및 '청소(Sanitize)' 수행
    # 토큰이나 URL에 숨어있는 특수문자를 제거합니다.
    token = sanitize(os.getenv('POLARION_TOKEN'))
    project_id = sanitize(os.getenv('projectid'))
    test_run_id = sanitize(os.getenv('testRunId'))
    base_url = sanitize(os.getenv('BASE_URL'))
    
    # PDF 경로는 한글이 있을 수 있으므로 sanitize 하지 않고 그대로 둡니다 (OS가 처리)
    pdf_path = os.getenv('PDF_PATH')
    
    job_name = sanitize(os.getenv('JOB_NAME', 'UnknownJob'))
    build_number = sanitize(os.getenv('BUILD_NUMBER', '0'))

    # 필수 값 체크
    if not all([token, project_id, test_run_id, base_url, pdf_path]):
        print("[ERROR] Missing required environment variables.")
        sys.exit(1)

    # 2. PDF 파일 확인
    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found at: {pdf_path}")
        sys.exit(1)

    log(f"Target PDF: {pdf_path}")

    # 3. API URL 생성
    target_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/attachments"
    log(f"API Endpoint: {target_url}")

    # 4. JSON 메타데이터 생성
    target_filename = f"Static_Analysis_{build_number}.pdf"
    title = f"Static Analysis [{job_name} #{build_number}]"

    resource_data = {
        "data": [{
            "type": "testrun_attachments",
            "attributes": {
                "fileName": target_filename,
                "title": title
            }
        }]
    }

    # 5. 헤더 설정 (토큰은 이미 sanitize 되었으므로 안전)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    # 6. Body 데이터 준비 (가장 중요!)
    # json.dumps 후 .encode('utf-8')을 하여 'bytes'로 변환
    json_bytes = json.dumps(resource_data, ensure_ascii=True).encode('utf-8')

    # files 구조를 명확하게 변경: ('파일명', 데이터, '컨텐츠타입')
    # 여기서 'blob'은 실제 파일명이 아니라, 폼 데이터의 이름일 뿐입니다.
    files = {
        'resource': ('blob', json_bytes, 'application/json'), 
        'files': (target_filename, open(pdf_path, 'rb'), 'application/pdf')
    }

    try:
        log("Sending request to Polarion...")
        # verify=False는 SSL 인증서 에러 무시 (필요시 사용)
        response = requests.post(target_url, headers=headers, files=files, verify=False)
        
        if response.status_code in [200, 201]:
            log(f"[SUCCESS] Upload Complete! Status: {response.status_code}")
            print(response.text)
        else:
            print(f"[ERROR] Upload Failed. Status: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        # 에러 발생 시 어떤 변수 때문인지 힌트 출력
        print("DEBUG INFO:")
        print(f"Token Length: {len(token)}")
        print(f"URL: {target_url}")
        sys.exit(1)

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # SSL 경고 끄기
    main()