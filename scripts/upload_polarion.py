import os
import sys
import json
import requests
import datetime

# Color codes for logs
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log(msg):
    print(f"{GREEN}{BOLD}[POLARION-UPLOAD] {msg}{RESET}")

def main():
    log("Starting Polarion upload process...")

    # 1. Get Parameters from Jenkins Environment Variables
    # (Matches the parameter names in your Jenkins image)
    token = os.getenv('POLARION_TOKEN')
    project_id = os.getenv('projectid')       # Note: lowercase from image
    test_run_id = os.getenv('testRunId')      # Note: camelCase from image
    base_url = os.getenv('BASE_URL')
    pdf_path = os.getenv('PDF_PATH')
    
    # Jenkins default variables
    job_name = os.getenv('JOB_NAME', 'UnknownJob')
    build_number = os.getenv('BUILD_NUMBER', '0')

    # Validate essential inputs
    if not all([token, project_id, test_run_id, base_url, pdf_path]):
        print("[ERROR] Missing required environment variables.")
        sys.exit(1)

    # 2. Check PDF File Existence
    if not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found at: {pdf_path}")
        sys.exit(1)

    log(f"Target PDF: {pdf_path}")

    # 3. Construct API URL
    # Format: BASE_URL/projects/PROJECT_ID/testruns/TESTRUN_ID/attachments
    target_url = f"{base_url}/projects/{project_id}/testruns/{test_run_id}/attachments"
    log(f"API Endpoint: {target_url}")

    # 4. Prepare Metadata (JSON)
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

    # 5. Execute Request (Multipart Upload)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
        # 'Content-Type': 'multipart/form-data' is set automatically by requests
    }

    files = {
        'resource': (None, json.dumps(resource_data), 'application/json'),
        'files': (target_filename, open(pdf_path, 'rb'), 'application/pdf')
    }

    try:
        log("Sending request to Polarion...")
        response = requests.post(target_url, headers=headers, files=files)
        
        # Check Response
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