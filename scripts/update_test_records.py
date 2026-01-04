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

    # [중요] Task 생성을 위한 Payload
    # 프로젝트 설정에 따라 필수 필드(severity, priority 등)가 다를 수 있습니다.
    payload = {
        "data": {
            "type": "workitems",
            "attributes": {
                "type": "task",  # 요청하신 대로 'task' 타입으로 설정
                "title": f"[Auto] Fix Failed Test (Jenkins Build #{build_number})",
                "description": {
                    "type": "text/html",
                    "value": f"Test failed in Jenkins Build #{build_number}.<br>Please investigate."
                },
                "status": "open",    # 워크플로우 초기 상태 (설정에 따라 다를 수 있음)
                "severity": "normal" # 필수 필드일 가능성이 높아 추가
            }
        }
    }

    try:
        log("Attempting to create a 'task' Work Item...")
        response = requests.post(create_url, headers=headers, json=payload, verify=False)
        
        if response.status_code == 201: # 201 Created
            new_id = response.json()['data']['id']
            log(f"✅ Task Work Item created successfully: {new_id}")
            return new_id
        else:
            # 생성 실패 시 상세 원인 출력
            error_log(f"Failed to create Task. Status: {response.status_code}")
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

    # 필수 값 체크
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
        current_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        clean_data = []
        
        is_agile_mode = (plan_type == "Agile")
        failed_assigned = False 

        for item in records_data:
            result_status = "passed"
            comment_text = f"Test Passed from Jenkins (#{build_number})"
            defect_relationship = None 

            # [Agile 모드 로직]
            if is_agile_mode and not failed_assigned:
                result_status = "failed"
                comment_text = f"Test Failed from Jenkins (#{build_number}) - Task Created"
                
                # 1. Task Work Item 생성 시도
                new_task_id = create_task_workitem(base_url, project_id, token, build_number)
                
                # 2. 생성 성공 시 관계 설정
                if new_task_id:
                    # [주의] Task여도 Test Record의 필드명은 'defect'입니다.
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
                    error_log("Task creation failed, so it will not be linked.")

                failed_assigned = True

            # Record 객체 구성
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

            # 관계 정보가 있으면 추가 (E-Signature 우회를 위해 defect 필드만 추가)
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