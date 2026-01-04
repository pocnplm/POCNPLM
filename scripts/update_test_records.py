import os
import sys
import json
import datetime
import requests
import urllib3

# SSL 인증서 경고 끄기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 윈도우 Jenkins 환경 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

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

# -----------------------------------------------------------
# [함수] Task Work Item 생성
# -----------------------------------------------------------
def create_task_workitem(base_url, project_id, token, build_number):
    """
    Polarion에 'task' 타입의 Work Item을 생성하고 ID를 반환합니다.
    """
    create_url = f"{base_url}/projects/{project_id}/workitems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # [수정 1] Data를 배열([])로 감쌌습니다.
    # BEGIN_ARRAY expected 에러 해결을 위한 조치
    payload = {
        "data": [
            {
                "type": "workitems",
                "attributes": {
                    "type": "task",
                    "title": f"[Auto] Fix Failed Test (Jenkins Build #{build_number})",
                    "description": {
                        "type": "text/html",
                        "value": f"Test failed in Jenkins Build #{build_number}.<br>Please investigate."
                    },
                    "status": "open",
                    "severity": "normal"
                }
            }
        ]
    }

    try:
        log("Attempting to create a 'task' Work Item...")
        response = requests.post(create_url, headers=headers, json=payload, verify=False)
        
        # 201 Created (성공)
        if response.status_code == 201:
            resp_json = response.json()
            
            # [수정 2] 요청을 배열로 보냈으므로 응답도 배열로 옵니다. 첫 번째 요소([0])를 선택합니다.
            if isinstance(resp_json.get('data'), list):
                new_id = resp_json['data'][0]['id']
            else:
                # 만약 서버가 배열로 요청받고 객체로 돌려주는 경우를 대비
                new_id = resp_json['data']['id']

            log(f"[OK] Task Work Item created successfully: {new_id}")
            return new_id
        else:
            error_log(f"[FAIL] Failed to create Task. Status: {response.status_code}")
            error_log(f"Server Response: {response.text}")
            return None
    except Exception as e:
        error_log(f"Error creating Task: {e}")
        return None

# -----------------------------------------------------------
# Main Logic
# -----------------------------------------------------------
def main():
    log("Starting Test Records Update...")

    # 1. 환경변수 로드
    token = os.getenv('POLARION_TOKEN', '').strip()
    project_id = os.getenv('projectid', '').strip()
    test_run_id = os.getenv('testRunId', '').strip()
    base_url = os.getenv('BASE_URL', '').strip()
    plan_type = os.getenv('planType', '').strip()
    
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    if not token:
        error_log("CRITICAL: Token is EMPTY!")
        sys.exit(1)

    if not all([project_id, test_run_id, base_url]):
        error_log("Missing required environment variables.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    api_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/testrecords"
    
    try:
        # Step 1: GET (조회)
        response_get = requests.get(api_url, headers=headers, verify=False)
        if response_get.status_code != 200:
            error_log(f"Failed to fetch records. Status: {response_get.status_code}")
            sys.exit(1)

        records_data = response_get.json().get('data', [])
        if not records_data:
            log("No test records found.")
            sys.exit(0)

        # Step 2: 데이터 가공
        # [수정 3] Datetime 경고 해결 (timezone-aware 사용)
        current_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        clean_data = []
        is_agile_mode = (plan_type == "Agile")
        failed_assigned = False 

        for item in records_data:
            result_status = "passed"
            comment_text = f"Test Passed from Jenkins (#{build_number})"
            defect_relationship = None 

            if is_agile_mode and not failed_assigned:
                result_status = "failed"
                comment_text = f"Test Failed from Jenkins (#{build_number}) - Task Created"
                
                # Task 생성 호출
                new_task_id = create_task_workitem(base_url, project_id, token, build_number)
                
                if new_task_id:
                    defect_relationship = {
                        "defect": {
                            "data": {
                                "type": "workitems",
                                "id": new_task_id
                            }
                        }
                    }
                    debug_log(f"Linking Task {new_task_id} to Test Record {item['id']}")
                else:
                    error_log("[WARNING] Task creation failed, so it will not be linked.")

                failed_assigned = True

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

            if defect_relationship:
                record["relationships"] = defect_relationship

            clean_data.append(record)

        payload = {"data": clean_data}

        # Step 3: PATCH (업데이트)
        log("Sending PATCH request...")
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