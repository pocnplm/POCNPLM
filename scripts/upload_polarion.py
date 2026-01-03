import os
import sys
import json
import requests
import datetime

# Color codes
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log(msg):
    print(f"{GREEN}{BOLD}[POLARION-UPLOAD] {msg}{RESET}")

def main():
    log("Starting Polarion upload process...")

    # 1. Get Parameters
    token = os.getenv('POLARION_TOKEN')
    project_id = os.getenv('projectid')
    test_run_id = os.getenv('testRunId')
    base_url = os.getenv('BASE_URL')
    pdf_path = os.getenv('PDF_PATH')
    
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    if not all([token, project_id, test_run_id, base_url, pdf_path]):
        print("[ERROR] Missing required environment variables.")
        sys.exit(1)

    # 2. Check PDF
    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found at: {pdf_path}")
        sys.exit(1)

    log(f"Target PDF: {pdf_path}")

    # 3. Construct API URL
    target_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/attachments"
    log(f"API Endpoint: {target_url}")

    # 4. Prepare Metadata
    target_filename = f"Static_Analysis_{build_number}.pdf"
    title = f"Static Analysis [{job_name} #{build_number}]"

    resource_data = {
        "data": [{
            "type": "testrun_attachments",
            "attributes": {
                "fileName": target_filename,
                "title": title
            }
        }]
    }

    # 5. Execute Request
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    # [수정됨] json 문자열을 .encode('utf-8')을 통해 '바이트(bytes)'로 직접 변환
    # 이렇게 하면 requests가 내부적으로 latin-1 인코딩을 시도하지 않아 에러가 발생하지 않음
    json_bytes = json.dumps(resource_data).encode('utf-8')

    files = {
        'resource': (None, json_bytes), 
        'files': (target_filename, open(pdf_path, 'rb'), 'application/pdf')
    }

    try:
        log("Sending request to Polarion...")
        response = requests.post(target_url, headers=headers, files=files)
        
        if response.status_code in [200, 201]:
            log(f"[SUCCESS] Upload Complete! Status: {response.status_code}")
            print(response.text)
        else:
            print(f"[ERROR] Upload Failed. Status: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] Exception occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()