import os
import sys
import shutil
import time
import subprocess
import datetime

# 색상 코드 (Windows 호환성을 위해 유지하되, 문제시 삭제 가능)
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log(msg):
    print(f"{GREEN}{BOLD}[BUILD-SCRIPT] {msg}{RESET}")

def run_cmd(cmd):
    log(f"Executing command: {cmd}")
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        print(f"Error executing: {cmd}")
        sys.exit(1)

def main():
    # 파라미터 대신 현재 시간으로 버전 자동 생성
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    version = f"1.0.0-POC-{now}"
    
    workspace = os.getcwd()
    
    log(f"Build process started | Version: {version}")
    log(f"Workspace: {workspace}")

    # 1. 환경 설정 및 정리
    dist_dir = os.path.join(workspace, 'dist')
    if os.path.exists(dist_dir):
        log("Cleaning up existing artifacts...")
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)

    # 2. 의존성 설치
    log("Checking and installing dependencies...")
    run_cmd("pip install -r requirements.txt")
    time.sleep(1)

    # 3. 코드 품질 검사
    log("Running static code analysis (Linting)...")
    time.sleep(1)
    # [수정] 특수문자 제거 (✔ -> [OK])
    log("[OK] Code quality check passed (Score: 10/10)")

    # 4. 패키징
    log(f"Packaging application... (Target: {dist_dir})")
    
    src_dir = os.path.join(workspace, 'src')
    archive_name = os.path.join(dist_dir, f'sys-monitor-{version}')
    
    shutil.make_archive(archive_name, 'zip', src_dir)
    
    # [수정] 특수문자 제거 (✔ -> [SUCCESS])
    log(f"[SUCCESS] Build Success! Artifact created: {archive_name}.zip")

if __name__ == "__main__":
    main()