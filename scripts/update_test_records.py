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
# [NEW] Test Case ID 추출 함수
# -----------------------------------------------------------
def get_test_case_id_from_record(record_id):
    """
    Record ID 구조: ProjectID/TestRunID/TestCaseID/ExecutionID
    예: elibrary/MyTestRun/OKSA-1601/0 -> 반환값: OKSA-1601
    """
    try:
        parts = record_id.split('/')
        if len(parts) >= 3:
            return parts[2] # 3번째 요소가 Test Case ID
    except Exception:
        pass
    return None

# -----------------------------------------------------------
# [UPDATE] Task 생성 함수 (Description 강화)
# -----------------------------------------------------------
def create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id):
    create_url = f"{base_url}/projects/{project_id}/workitems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 1. Description에 들어갈 링크 생성 (Polarion 웹 UI 주소 추정)
    # 실제 주소 포맷은 Polarion 버전에 따라 다를 수 있으니 확인 필요
    # 보통: {base_url}/polarion/#/project/{project}/workitem?id={id}
    # 또는: {base_url}/polarion/redirect/project/{project}/workitem?id={id}
    
    # 더 안전한 방법: 단순 텍스트보다 HTML 링크 삽입
    web_link_testcase = f"{base_url}/polarion/#/project/{project_id}/workitem?id={test_case_id}"
    web_link_testrun = f"{base_url}/polarion/#/project/{project_id}/testrun?id={test_run_id}"

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
# [NEW] 링크 생성 함수 (Task -> Test Case)
# -----------------------------------------------------------
def link_workitems(base_url, project_id, token, source_id, target_id, role="resolves"):
    """
    두 Work Item을 연결합니다. (기본 역할: resolves)
    source_id: 새로 만든 Task (예: Project/TASK-100)
    target_id: 실패한 Test Case (예: Project/OKSA-1601)
    """
    # Polarion API에서 링크를 추가하는 엔드포인트는 보통 POST /workitems/{id}/relationships/linkedWorkItems
    # 또는 PATCH로 relationships를 업데이트합니다. 가장 확실한 PATCH 방법을 사용합니다.
    
    # ID 포맷 확인 (Project/ID 형태여야 함)
    if "/" not in target_id:
        target_id = f"{project_id}/{target_id}"
    if "/" not in source_id:
        source_id = f"{project_id}/{source_id}"

    link_url = f"{base_url}/projects/{project_id}/workitems/{source_id.split('/')[-1]}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # JSON:API 표준에 따른 링크 추가 Payload
    payload = {
        "data": {
            "type": "workitems",
            "id": source_id,
            "relationships": {
                "linkedWorkItems": {
                    "data": [
                        {
                            "type": "workitems",
                            "id": target_id,
                            "meta": {
                                "role": role
                            }
                        }
                    ]
                }
            }
        }
    }
    
    try:
        debug_log(f"Linking {source_id} --({role})--> {target_id}")
        # PATCH를 사용하여 기존 정보에 링크 정보를 '병합'하거나 추가
        response = requests.patch(link_url, headers=headers, json=payload, verify=False)
        
        if response.status_code in [200, 204]:
            log(f"[OK] Linked successfully.")
        else:
            error_log(f"[FAIL] Link Failed: {response.status_code}")
            print(response.text)
            
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
                
                # 2. Task 생성 (test_case_id, test_run_id 전달)
                new_task_id = create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id)
                
                if new_task_id:
                    # 3. [중요] Task와 Test Case 연결 (Linked Work Items)
                    if test_case_id:
                        link_workitems(base_url, project_id, token, new_task_id, test_case_id, role="resolve")

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

        log("Sending PATCH request...")
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