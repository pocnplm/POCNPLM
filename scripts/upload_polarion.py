import os
import sys
import json
import subprocess

# 로그용 색상 코드
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'
RED = '\033[91m'

def log(msg):
    print(f"{GREEN}{BOLD}[POLARION-UPLOAD] {msg}{RESET}")

def error_log(msg):
    print(f"{RED}{BOLD}[ERROR] {msg}{RESET}")

def main():
    log("Starting Polarion upload process using CURL...")

    # 1. 환경변수 가져오기 (양옆 공백 제거 .strip() 필수)
    token = os.getenv('POLARION_TOKEN', '')
    project_id = os.getenv('projectid', '')
    test_run_id = os.getenv('testRunId', '')
    base_url = os.getenv('BASE_URL', '')
    pdf_path = os.getenv('PDF_PATH', '')
    
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    # 필수 값 체크
    if not all([token, project_id, test_run_id, base_url, pdf_path]):
        error_log("Missing required environment variables.")
        sys.exit(1)

    if not os.path.exists(pdf_path):
        error_log(f"PDF file not found at: {pdf_path}")
        sys.exit(1)

    # 2. JSON 데이터 생성
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
    # JSON 문자열 생성 (공백 최소화)
    resource_json_str = json.dumps(resource_data, separators=(',', ':'), ensure_ascii=False)

    # 3. CURL 명령어 구성
    target_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/attachments"
    
    log(f"Target URL: {target_url}")
    log(f"Target File: {pdf_path}")

    # -H "Authorization: Bearer {token}" 부분에서 토큰에 줄바꿈이나 공백이 있으면 401 발생함
    cmd = [
        "curl", "-v", "-k",
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
        
        # 명령어 실행 결과 캡처
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

        # [중요 수정] curl 자체의 성공 여부뿐만 아니라, 응답 내용(Body)을 검사해야 함
        response_body = result.stdout
        
        print("--- Response Output ---")
        print(response_body)
        print("-----------------------")

        # 5. 성공/실패 판정 로직 강화
        # Case A: curl 명령어 자체가 실패 (네트워크 오류 등)
        if result.returncode != 0:
            error_log(f"CURL execution failed with exit code {result.returncode}")
            sys.exit(1)

        # Case B: curl은 돌았지만 서버가 에러(401, 404, 500 등)를 줌
        # Polarion 에러 메시지 패턴 체크 ("errors": [...] 혹은 status code 체크)
        if '"errors":' in response_body or '"status":"401"' in response_body or '"status":"403"' in response_body:
            error_log("Server returned an ERROR response!")
            sys.exit(1) # 여기서 1을 반환해야 Jenkins가 'Failure'로 인식함

        log("[SUCCESS] Upload confirmed.")

    except Exception as e:
        error_log(f"Exception occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()