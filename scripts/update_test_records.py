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
# UI Base URL 추출 함수
# -----------------------------------------------------------
def get_ui_base_url(api_base_url):
    """
    API URL (예: .../polarion/rest/v1) -> UI URL (예: .../polarion)
    """
    if "/rest" in api_base_url:
        return api_base_url.split("/rest")[0]
    return api_base_url

# -----------------------------------------------------------
# [FIXED] Test Case ID 추출 로직 개선
# -----------------------------------------------------------
def get_test_case_id_from_record(record_id, project_id):
    """
    Record ID 문자열을 분석하여 실제 Test Case ID를 추출합니다.
    기존: 무조건 3번째 요소(parts[2])를 가져와서 Project ID가 걸리는 문제 발생
    개선: Project ID 위치를 찾고 그 다음 요소를 가져오거나, Work Item ID 형식(하이픈 포함)을 찾음
    """
    try:
        parts = record_id.split('/')
        
        # 1. Project ID가 경로 안에 명시적으로 있다면, 그 다음 요소가 Test Case ID일 확률이 매우 높음
        if project_id in parts:
            p_index = parts.index(project_id)
            if p_index + 1 < len(parts):
                candidate = parts[p_index + 1]
                # 반복 횟수(0, 1) 같은 숫자가 아니면 리턴
                if not candidate.isdigit():
                    return candidate

        # 2. Project ID를 못 찾았다면, 역순으로 탐색하여 하이픈(-)이 있는 요소를 찾음 (예: OKSA-1234)
        # 보통 마지막은 실행횟수(0), 그 앞이 ID
        for part in reversed(parts):
            if '-' in part and not part.startswith('Link'): # 간단한 Work Item ID 패턴 체크
                return part

        # 3. Fallback: 기존보다 한 칸 뒤(parts[3])를 시도 (구조가 Group/Run/Project/Case 인 경우 대비)
        if len(parts) >= 4:
            return parts[3]
        if len(parts) >= 3:
            return parts[2]
            
    except Exception as e:
        debug_log(f"Error parsing ID: {e}")
    return None

# -----------------------------------------------------------
# Task 생성 함수
# -----------------------------------------------------------
def create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id):
    create_url = f"{base_url}/projects/{project_id}/workitems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    ui_base_url = get_ui_base_url(base_url)

    # 링크 생성 (여기서 test_case_id가 올바르면 링크도 정상 작동함)
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
# 링크 생성 함수 (POST)
# -----------------------------------------------------------
def link_workitems(base_url, project_id, token, source_task_id, target_testcase_id, role="resolve"):
    if "/" in source_task_id:
        source_short_id = source_task_id.split("/")[-1]
    else:
        source_short_id = source_task_id

    # Target ID는 Full ID (Project/ID)가 안전함
    if "/" not in target_testcase_id:
        target_full_id = f"{project_id}/{target_testcase_id}"
    else:
        target_full_id = target_testcase_id

    link_url = f"{base_url}/projects/{project_id}/workitems/{source_short_id}/relationships/linkedWorkItems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "data": [
            {
                "type": "workitems",
                "id": target_full_id,
                "meta": {
                    "role": role
                }
            }
        ]
    }
    
    try:
        debug_log(f"Linking: Task({source_short_id}) --[{role}]--> TestCase({target_full_id})")
        response = requests.post(link_url, headers=headers, json=payload, verify=False)
        
        if response.status_code in [200, 204]:
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
                
                # 1. [UPDATED] Test Case ID 추출 시 project_id를 전달하여 제외시킴
                test_case_id = get_test_case_id_from_record(item['id'], project_id)
                
                if not test_case_id or test_case_id == project_id:
                    # 만약 여전히 Project ID와 같다면 한번 더 fallback 시도
                    debug_log(f"ID extraction warning: Got {test_case_id}, trying fallback...")
                    test_case_id = "UNKNOWN"

                # 2. Task 생성
                new_task_id = create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id)
                
                if new_task_id and test_case_id != "UNKNOWN":
                    # 3. 링크 연결
                    link_workitems(base_url, project_id, token, new_task_id, test_case_id, role="resolves")

                    # 4. Defect 필드 추가
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