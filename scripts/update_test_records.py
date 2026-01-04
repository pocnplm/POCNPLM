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

# -----------------------------------------------------------
# [NEW] Defect 생성 함수
# -----------------------------------------------------------
def create_defect(base_url, project_id, token, build_number):
    """
    Polarion에 새로운 Defect Work Item을 생성하고 ID를 반환합니다.
    """
    create_url = f"{base_url}/projects/{project_id}/workitems"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Defect 생성 페이로드
    payload = {
        "data": {
            "type": "workitems",
            "attributes": {
                "type": "defect",  # Work Item 타입 (Polarion 설정에 따라 'issue'일 수도 있음)
                "title": f"[Auto] Test Failed in Jenkins Build #{build_number}",
                "description": {
                    "type": "text/html",
                    "value": f"This defect was automatically created by Jenkins CI/CD.<br>Build Number: {build_number}"
                },
                "severity": "major", # 필수 필드일 경우 설정 필요
                "status": "open"
            }
        }
    }

    try:
        log("Creating a new Defect Work Item...")
        response = requests.post(create_url, headers=headers, json=payload, verify=False)
        
        if response.status_code == 201: # 201 Created
            new_id = response.json()['data']['id']
            log(f"Defect created successfully: {new_id}")
            return new_id
        else:
            error_log(f"Failed to create defect. Status: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        error_log(f"Error creating defect: {e}")
        return None

# -----------------------------------------------------------
# Main Logic
# -----------------------------------------------------------
def main():
    log("Starting Test Records Update with Defect Creation...")

    # 1. 토큰 및 환경변수 로드
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
        # Step 2: Data Transformation
        # =========================================================
        current_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        clean_data = []
        
        is_agile_mode = (plan_type == "Agile")
        failed_assigned = False 

        for item in records_data:
            result_status = "passed"
            comment_text = f"Test Passed from Jenkins (#{build_number})"
            defect_relationship = None # Defect 연결 정보

            # [Agile 모드일 경우: 첫 번째 건만 Failed + Defect 생성]
            if is_agile_mode and not failed_assigned:
                result_status = "failed"
                comment_text = f"Test Failed from Jenkins (#{build_number}) - Defect Created"
                
                # 1. Defect 생성 호출
                new_defect_id = create_defect(base_url, project_id, token, build_number)
                
                # 2. Defect ID가 정상적으로 반환되면 관계(relationship) 데이터 생성
                if new_defect_id:
                    defect_relationship = {
                        "defect": {
                            "data": {
                                "type": "workitems",
                                "id": new_defect_id
                            }
                        }
                    }
                
                failed_assigned = True

            # Payload 구성
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

            # Defect가 생성된 경우에만 relationships 필드 추가
            if defect_relationship:
                record["relationships"] = defect_relationship

            clean_data.append(record)

        payload = {"data": clean_data}

        # =========================================================
        # Step 3: PATCH (업데이트 요청 전송)
        # =========================================================
        log("Sending PATCH request to update records...")
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