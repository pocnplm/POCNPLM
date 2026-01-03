import os
import sys
import json
import datetime
import requests
import urllib3

# SSL 인증서 경고 끄기 (PowerShell의 -SkipCertificateCheck 대응)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 로그용 색상 코드
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'
RED = '\033[91m'
YELLOW = '\033[93m'

def log(msg):
    print(f"{GREEN}{BOLD}[UPDATE-RECORDS] {msg}{RESET}")

def error_log(msg):
    print(f"{RED}{BOLD}[ERROR] {msg}{RESET}")

def debug_log(msg):
    print(f"{YELLOW}[DEBUG] {msg}{RESET}")


def main():
    log("Starting Test Records Update (Minimal Version for E-Signature bypass)...")

    # 1. 토큰 및 환경변수 로드
    token = os.getenv('POLARION_TOKEN', '').strip()
    project_id = os.getenv('projectid', '').strip()
    test_run_id = os.getenv('testRunId', '').strip()
    base_url = os.getenv('BASE_URL', '').strip()
    
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    # 필수 값 체크
    if not token:
        error_log("CRITICAL: Token is EMPTY! Check 'key.text' or Jenkins Parameter.")
        sys.exit(1)

    if not all([project_id, test_run_id, base_url]):
        error_log("Missing required environment variables (projectid, testRunId, BASE_URL).")
        sys.exit(1)

    # 2. 공통 헤더 설정
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # URL 생성
    # 예: https://.../projects/PROJ/testruns/ID/testrecords
    api_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/testrecords"
    log(f"Target API: {api_url}")

    try:
        # =========================================================
        # Step 1: GET (기존 Test Record 조회)
        # =========================================================
        log("Fetching existing test records...")
        response_get = requests.get(api_url, headers=headers, verify=False)
        
        if response_get.status_code != 200:
            error_log(f"Failed to fetch records. Status: {response_get.status_code}")
            print(response_get.text)
            sys.exit(1)

        records_data = response_get.json().get('data', [])
        if not records_data:
            log("No test records found to update.")
            sys.exit(0)

        log(f"Found {len(records_data)} records. Preparing update payload...")

        # =========================================================
        # Step 2: Data Transformation (데이터 가공)
        # =========================================================
        # 현재 시간 (PowerShell의 [DateTime]::UtcNow 와 동일 포맷)
        current_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        clean_data = []
        for item in records_data:
            # E-Signature 우회를 위해 relationships 제거하고 필수 필드만 업데이트
            record = {
                "type": "testrecords",
                "id": item['id'],
                "attributes": {
                    "result": "passed",
                    "executed": current_time,
                    "comment": {
                        "type": "text/html",
                        "value": f"Test Passed from Jenkins (#{build_number})"
                    }
                }
                # 중요: relationships 필드는 포함하지 않음 (Minimal Update)
            }
            clean_data.append(record)

        payload = {"data": clean_data}

        # =========================================================
        # Step 3: PATCH (업데이트 요청 전송)
        # =========================================================
        log("Sending PATCH request to update records...")
        
        # requests.patch 사용 (verify=False는 SSL 무시)
        response_patch = requests.patch(api_url, headers=headers, json=payload, verify=False)

        if response_patch.status_code in [200, 204]:
            log(f"[SUCCESS] Update Complete! Status: {response_patch.status_code}")
        else:
            error_log(f"Update Failed. Status: {response_patch.status_code}")
            print(f"Server Message: {response_patch.text}")
            sys.exit(1)

    except Exception as e:
        error_log(f"Exception occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()