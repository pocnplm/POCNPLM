import os
import sys
import json
import datetime
import requests
import urllib3
import re  # 정규표현식 모듈

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
    # API 주소가 .../polarion/rest/v1 이라면 .../polarion 까지만 추출
    if "/rest" in api_base_url:
        return api_base_url.split("/rest")[0]
    return api_base_url

# -----------------------------------------------------------
# [중요] Test Case ID 추출 로직 (정규표현식 강화)
# -----------------------------------------------------------
def get_test_case_id_from_record(record_id):
    """
    Record ID 예: Project/TestRun/TestCaseID/ExecutionID
    목표: 'OKS_Agile_Test'(프로젝트)나 'testest'(TestRun) 말고 'OKSA-1601' 같은 패턴을 찾는다.
    """
    try:
        parts = record_id.split('/')
        
        # 정규식 패턴: 알파벳문자들 + 하이픈(-) + 숫자들 (예: OKSA-1234)
        # 언더바(_)가 포함된 프로젝트 ID는 이 패턴에 걸리지 않음
        id_pattern = re.compile(r'^[A-Za-z]+-\d+$')

        for part in parts:
            if id_pattern.match(part):
                return part
        
        debug_log(f"Cannot find pattern 'ID-Number' in {parts}")
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
    
    # [수정] ID가 정확히 추출되면 링크도 정상적으로 생성됨
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
        log(f"Creating Task for Failed Case: {test_case_id}")
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
            return None
    except Exception as e:
        error_log(f"Error creating Task: {e}")
        return None

# -----------------------------------------------------------
# [NEW] 링크 생성 함수 (보내주신 API 사용)
# -----------------------------------------------------------
def link_workitems_direct(base_url, token, project_id, source_task_id, target_testcase_id, role="resolves"):
    """
    User가 제안한 API 엔드포인트 사용:
    PATCH /projects/{projectId}/workitems/{workItemId}/linkedworkitems/{roleId}/{targetProjectId}/{linkedWorkItemId}
    """
    
    # ID에서 Short ID 추출 (Project명 제거)
    # 예: "MyProject/TASK-100" -> "TASK-100"
    if "/" in source_task_id:
        source_short_id = source_task_id.split("/")[-1]
    else:
        source_short_id = source_task_id

    if "/" in target_testcase_id:
        target_short_id = target_testcase_id.split("/")[-1]
    else:
        target_short_id = target_testcase_id

    # [중요] 제안해주신 URL 구조대로 생성
    # base_url 끝에 /rest/v1 등이 있다면 적절히 조절 필요. 보통 API Base URL 바로 뒤에 붙음.
    link_url = (
        f"{base_url}/projects/{project_id}/workitems/{source_short_id}"
        f"/linkedworkitems/{role}/{project_id}/{target_short_id}"
    )
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
        # PATCH지만 Body가 없으므로 Content-Type은 생략 가능하거나 기본값
    }

    try:
        debug_log(f"Linking via Direct API: {source_short_id} --[{role}]--> {target_short_id}")
        debug_log(f"URL: {link_url}")
        
        # Body 없이 호출
        response = requests.patch(link_url, headers=headers, verify=False)
        
        if response.status_code in [200, 201, 204]:
            log(f"[OK] Link Created Successfully!")
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
                
                # 1. [강화된 로직] 정확한 Test Case ID 추출
                test_case_id = get_test_case_id_from_record(item['id'])
                
                if not test_case_id:
                    test_case_id = "UNKNOWN"
                    debug_log(f"WARNING: Could not identify Test Case ID pattern in: {item['id']}")

                # 2. Task 생성
                new_task_id = create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id)
                
                if new_task_id and test_case_id != "UNKNOWN":
                    # 3. [NEW] 사용자 제안 API로 링크 연결
                    link_workitems_direct(base_url, token, project_id, new_task_id, test_case_id, role="resolve")

                    # 4. Test Record 업데이트용 Defect 필드
                    defect_relationship = {
                        "defect": {
                            "data": {
                                "type": "workitems",
                                "id": new_task_id
                            }
                        }
                    }

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