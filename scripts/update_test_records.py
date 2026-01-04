import os
import sys
import json
import datetime
import requests
import urllib3
import re

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
    if "/rest" in api_base_url:
        return api_base_url.split("/rest")[0]
    return api_base_url

# -----------------------------------------------------------
# Test Case ID 추출 로직 (정규표현식)
# -----------------------------------------------------------
def get_test_case_id_from_record(record_id, project_id, test_run_id):
    try:
        parts = record_id.split('/')
        # 프로젝트ID와 TestRunID를 제외하고 검색
        filtered_parts = [p for p in parts if p != project_id and p != test_run_id]

        # 정규식: 문자-숫자 패턴 (예: OKSA-1703)
        id_pattern = re.compile(r'^[A-Za-z]+-\d+$')

        for part in filtered_parts:
            if id_pattern.match(part):
                return part
        
        # 패턴 매칭 실패 시 fallback
        for part in filtered_parts:
            if not part.isdigit() and not part.startswith('Link'):
                return part
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
            # 배열 응답 처리
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
# [CORRECTED] 링크 생성 함수 (POST - Relationships API)
# -----------------------------------------------------------
def link_workitems(base_url, project_id, token, source_task_id, target_testcase_id, role="resolves"):
    """
    POST /projects/{proj}/workitems/{id}/relationships/linkedWorkItems 사용
    """
    
    # URL 경로용 Short ID (예: TASK-100)
    if "/" in source_task_id:
        source_short_id = source_task_id.split("/")[-1]
    else:
        source_short_id = source_task_id

    # Body Payload용 Full ID (예: MyProject/OKSA-1234)
    # [중요] 타겟 ID에 프로젝트 ID가 없으면 붙여줘야 함
    if "/" not in target_testcase_id:
        target_full_id = f"{project_id}/{target_testcase_id}"
    else:
        target_full_id = target_testcase_id

    # [중요] Relationship 엔드포인트
    link_url = f"{base_url}/projects/{project_id}/workitems/{source_short_id}/relationships/linkedWorkItems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # [중요] Relationship POST Payload 구조
    # data는 반드시 리스트([])여야 합니다.
    payload = {
        "data": [
            {
                "type": "workitems",
                "id": target_full_id, # 반드시 Project/ID 형식
                "meta": {
                    "role": role      # 연결 역할 (기본: resolves)
                }
            }
        ]
    }
    
    try:
        debug_log(f"Linking (POST): {source_short_id} --[{role}]--> {target_full_id}")
        response = requests.post(link_url, headers=headers, json=payload, verify=False)
        
        # 204 No Content가 성공(추가됨)을 의미함
        if response.status_code in [200, 201, 204]:
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
                
                # 1. ID 추출 (정규식 사용)
                test_case_id = get_test_case_id_from_record(item['id'], project_id, test_run_id)
                
                if not test_case_id:
                    test_case_id = "UNKNOWN"
                    debug_log(f"Could not extract Test Case ID from {item['id']}")
                else:
                    debug_log(f"Extracted Test Case ID: {test_case_id}")

                # 2. Task 생성
                new_task_id = create_task_workitem(base_url, project_id, token, build_number, test_run_id, test_case_id)
                
                if new_task_id and test_case_id != "UNKNOWN":
                    # 3. 링크 연결 (POST Relationship)
                    link_workitems(base_url, project_id, token, new_task_id, test_case_id, role="resolve")

                    # 4. Defect 필드 설정
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