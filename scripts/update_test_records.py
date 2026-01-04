import os
import sys
import json
import datetime
import requests
import urllib3

# SSL 인증서 경고 끄기
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

def main():
    log("Starting Test Records Update...")

    # 1. 토큰 및 환경변수 로드
    token = os.getenv('POLARION_TOKEN', '').strip()
    project_id = os.getenv('projectid', '').strip()
    test_run_id = os.getenv('testRunId', '').strip()
    base_url = os.getenv('BASE_URL', '').strip()
    plan_type = os.getenv('planType', '').strip()  # Plan Type 확인
    
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    # 필수 값 체크
    if not token:
        error_log("CRITICAL: Token is EMPTY!")
        sys.exit(1)

    if not all([project_id, test_run_id, base_url]):
        error_log("Missing required environment variables.")
        sys.exit(1)

    # 2. 공통 헤더 설정
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    api_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/testrecords"
    log(f"Target API: {api_url}")
    log(f"Plan Type detected: '{plan_type}'")

    try:
        # =========================================================
        # Step 1: GET (기존 Test Record 조회)
        # =========================================================
        response_get = requests.get(api_url, headers=headers, verify=False)
        
        if response_get.status_code != 200:
            error_log(f"Failed to fetch records. Status: {response_get.status_code}")
            sys.exit(1)

        records_data = response_get.json().get('data', [])
        if not records_data:
            log("No test records found to update.")
            sys.exit(0)

        log(f"Found {len(records_data)} records. Preparing payload...")

        # =========================================================
        # Step 2: Data Transformation (데이터 가공 - 조건 추가됨)
        # =========================================================
        current_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        clean_data = []
        
        # Agile 모드인지 확인 (대소문자 구분 없이 처리하려면 .lower() 사용 가능)
        is_agile_mode = (plan_type == "Agile")
        failed_assigned = False  # 실패가 이미 할당되었는지 체크하는 플래그

        for item in records_data:
            # 기본값: Passed
            result_status = "passed"
            comment_text = f"Test Passed from Jenkins (#{build_number})"

            # [조건 변경 로직]
            # Plan Type이 Agile이고, 아직 실패 처리된 건이 없다면 이번 건을 실패로 처리
            if is_agile_mode and not failed_assigned:
                result_status = "failed"
                comment_text = f"Test Failed from Jenkins (#{build_number}) - Agile Simulation"
                failed_assigned = True  # 플래그를 True로 변경하여 이후 레코드는 Passed가 되게 함

            record = {
                "type": "testrecords",
                "id": item['id'],
                "attributes": {
                    "result": result_status,
                    "executed": current_time,
                    "comment": {
                        "type": "text/html",
                        "value": comment_text
                    }
                }
            }
            clean_data.append(record)

        payload = {"data": clean_data}

        # =========================================================
        # Step 3: PATCH (업데이트 요청 전송)
        # =========================================================
        if is_agile_mode:
            log(f"Applying Agile Logic: 1 Failed, {len(clean_data)-1} Passed.")
        else:
            log("Applying Standard Logic: All Passed.")

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