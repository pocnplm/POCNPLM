import os
import sys
import json
import datetime
import requests
import urllib3

# SSL 인증서 경고 끄기
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
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
# [NEW] UI Base URL 추출 함수
# -----------------------------------------------------------
def get_ui_base_url(api_base_url):
    """
    API URL (예: https://domain.com/polarion/rest/v1)에서
    UI URL (예: https://domain.com/polarion)을 추출합니다.
    """
    if "/rest" in api_base_url:
        return api_base_url.split("/rest")[0]
    return api_base_url

# -----------------------------------------------------------
# Test Case ID 추출 함수
# -----------------------------------------------------------
def get_test_case_id_from_record(record_id):
    """
    Record ID 구조: ProjectID/TestRunID/TestCaseID/ExecutionID (가변적일 수 있음)
    """
    try:
        parts = record_id.split('/')
        # 데이터 구조에 따라 인덱스가 다를 수 있으므로 확인 필요
        # 보통: Project / Run / TestCase / ...
        if len(parts) >= 3:
            return parts[2]
    except Exception:
        pass
    return None

# -----------------------------------------------------------
# Task 생성 함수 (HTML Link 수정됨)
# -----------------------------------------------------------
def create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id):
    create_url = f"{base_url}/projects/{project_id}/workitems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 1. UI용 Base URL 추출 (rest/v1 제거)
    ui_base_url = get_ui_base_url(base_url)

    # 2. 정확한 포맷의 하이퍼링크 생성
    # 요청하신 포맷: {ui_base_url}/#/project/{project_id}/workitem?id={test_case_id}
    web_link_testcase = f"{ui_base_url}/#/project/{project_id}/workitem?id={test_case_id}"
    web_link_testrun = f"{ui_base_url}/#/project/{project_id}/testrun?id={test_run_id}"

    description_html = (
        f"<b>Test failed in Jenkins Build #{build_number}</b><br><br>"
        f"<b>Test Run:</b> <a href='{web_link_testrun}' target='_blank'>{test_run_id}</a><br>"
        f"<b>Test Case:</b> <a href='{web_link_testcase}' target='_blank'>{test_case_id}</a><br><br>"
        f"Please investigate the failure."
    )

    payload = {
        "data": [
            {
                "type": "workitems",
                "attributes": {
                    "type": "task",
                    "title": f"[Auto] Fix Failed Test: {test_case_id} (Build #{build_number})",
                    "description": {
                        "type": "text/html",
                        "value": description_html
                    },
                    "status": "open",
                    "severity": "normal"
                }
            }
        ]
    }

    try:
        log(f"Attempting to create Task for {test_case_id}...")
        response = requests.post(create_url, headers=headers, json=payload, verify=False)
        
        if response.status_code == 201:
            resp_json = response.json()
            if isinstance(resp_json.get('data'), list):
                new_id = resp_json['data'][0]['id']
            else:
                new_id = resp_json['data']['id']
            log(f"[OK] Task Created: {new_id}")
            return new_id
        else:
            error_log(f"[FAIL] Task Create Failed: {response.status_code}")
            error_log(f"Response: {response.text}")
            return None
    except Exception as e:
        error_log(f"Error creating Task: {e}")
        return None

# -----------------------------------------------------------
# [FIXED] 링크 생성 함수 (POST 방식 사용)
# -----------------------------------------------------------
def link_workitems(base_url, project_id, token, source_task_id, target_testcase_id, role="resolves"):
    """
    Work Item 간의 관계를 생성합니다.
    방식: POST /projects/{proj}/workitems/{id}/relationships/linkedWorkItems
    """
    
    # URL 경로에는 순수 ID만 들어가야 함 (ProjectID 제외)
    # 예: source_task_id가 "MyProj/TASK-100"이라면 "TASK-100"만 추출
    if "/" in source_task_id:
        source_short_id = source_task_id.split("/")[-1]
    else:
        source_short_id = source_task_id

    # Body의 ID에는 "ProjectID/ItemID" 형식이 필요함
    if "/" not in target_testcase_id:
        target_full_id = f"{project_id}/{target_testcase_id}"
    else:
        target_full_id = target_testcase_id

    # 관계 추가 전용 엔드포인트
    link_url = f"{base_url}/projects/{project_id}/workitems/{source_short_id}/relationships/linkedWorkItems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # JSON:API 관계 추가 Payload
    payload = {
        "data": [
            {
                "type": "workitems",
                "id": target_full_id, # 여기는 Project/ID 형식
                "meta": {
                    "role": role
                }
            }
        ]
    }
    
    try:
        debug_log(f"Linking: Task({source_short_id}) --[{role}]--> TestCase({target_full_id})")
        # PATCH 대신 POST 사용 (관계 추가)
        response = requests.post(link_url, headers=headers, json=payload, verify=False)
        
        if response.status_code in [200, 204]: # 204 No Content가 뜨면 성공
            log(f"[OK] Linked successfully.")
        else:
            error_log(f"[FAIL] Link Failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        error_log(f"Error linking items: {e}")

# -----------------------------------------------------------
# Main Logic
# -----------------------------------------------------------
def main():
    log("Starting Test Records Update...")

    token = os.getenv('POLARION_TOKEN', '').strip()
    project_id = os.getenv('projectid', '').strip()
    test_run_id = os.getenv('testRunId', '').strip()
    base_url = os.getenv('BASE_URL', '').strip()
    plan_type = os.getenv('planType', '').strip()
    
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    if not all([token, project_id, test_run_id, base_url]):
        error_log("Missing required env vars.")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    api_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/testrecords"
    
    try:
        response_get = requests.get(api_url, headers=headers, verify=False)
        if response_get.status_code != 200:
            error_log(f"Fetch failed: {response_get.status_code}")
            sys.exit(1)

        records_data = response_get.json().get('data', [])
        if not records_data:
            log("No records found.")
            sys.exit(0)

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
                comment_text = f"Test Failed (See created Task) - Build #{build_number}"
                
                # 1. Test Case ID 추출
                test_case_id = get_test_case_id_from_record(item['id'])
                if not test_case_id:
                    test_case_id = "UNKNOWN"
                    debug_log(f"Could not extract Test Case ID from {item['id']}")

                # 2. Task 생성 (링크 생성 로직 개선됨)
                new_task_id = create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id)
                
                if new_task_id and test_case_id != "UNKNOWN":
                    # 3. [FIXED] Task와 Test Case 연결 (POST 방식)
                    link_workitems(base_url, project_id, token, new_task_id, test_case_id, role="resolves")

                    # 4. Test Record와 Task 연결 (defect 필드)
                    defect_relationship = {
                        "defect": {
                            "data": {
                                "type": "workitems",
                                "id": new_task_id
                            }
                        }
                    }
                else:
                    if not new_task_id:
                        error_log("[WARNING] Task creation failed.")

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

        log("Sending PATCH request to update Test Records...")
        response_patch = requests.patch(api_url, headers=headers, json=payload, verify=False)

        if response_patch.status_code in [200, 204]:
            log(f"[SUCCESS] Update Complete! Status: {response_patch.status_code}")
        else:
            error_log(f"Update Failed. Status: {response_patch.status_code}")
            print(response_patch.text)
            sys.exit(1)

    except Exception as e:
        error_log(f"Exception occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()