import os
import sys
import json
import subprocess

# 로그용 색상 코드
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log(msg):
    print(f"{GREEN}{BOLD}[POLARION-UPLOAD] {msg}{RESET}")

def main():
    log("Starting Polarion upload process using CURL...")

    # 1. 환경변수 가져오기
    # 배치 파일의 %VAR% 부분을 Python 변수로 매핑
    token = os.getenv('POLARION_TOKEN', '').strip()
    project_id = os.getenv('projectid', '').strip()
    test_run_id = os.getenv('testRunId', '').strip()
    base_url = os.getenv('BASE_URL', '').strip()
    pdf_path = os.getenv('PDF_PATH', '').strip()
    
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    # 필수 값 체크
    if not all([token, project_id, test_run_id, base_url, pdf_path]):
        print("[ERROR] Missing required environment variables.")
        sys.exit(1)

    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found at: {pdf_path}")
        sys.exit(1)

    # 2. JSON 데이터 생성 (배치 파일의 resource 부분)
    target_filename = f"Static_Analysis_{build_number}.pdf"
    title = f"Static Analysis [{job_name} #{build_number}]"

    # Python 객체로 만든 뒤 json.dumps로 문자열화 (이스케이프 자동 처리)
    resource_data = {
        "data": [{
            "type": "testrun_attachments",
            "attributes": {
                "fileName": target_filename,
                "title": title
            }
        }]
    }
    # 공백 없이 문자열로 변환
    resource_json_str = json.dumps(resource_data, separators=(',', ':'), ensure_ascii=False)

    # 3. CURL 명령어 구성
    # 배치 스크립트의 curl 명령어를 리스트 형태로 변환 (보안상 안전하고 인용부호 문제 해결)
    target_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/attachments"
    
    log(f"Target URL: {target_url}")
    log(f"Target File: {pdf_path}")

    cmd = [
        "curl", "-v", "-k",  # -k: SSL 인증서 무시 (혹시 모를 SSL 에러 방지)
        "-X", "POST", target_url,
        "-H", "accept: application/json",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: multipart/form-data",
        "-F", f"resource={resource_json_str}",
        "-F", f"files=@{pdf_path}"
    ]

    # 4. 명령어 실행
    try:
        log("Executing CURL command...")
        
        # subprocess를 이용해 시스템의 curl 호출
        # shell=True는 윈도우에서 명령어를 잘 찾게 도와줌
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        # 5. 결과 확인
        if result.returncode == 0:
            log("[SUCCESS] CURL command executed successfully.")
            print("Response output:")
            print(result.stdout)
        else:
            print(f"[ERROR] CURL execution failed with code {result.returncode}")
            print("STDERR:")
            print(result.stderr)
            print("STDOUT:")
            print(result.stdout)
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()