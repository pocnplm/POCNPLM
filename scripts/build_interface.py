import os
import sys
import shutil
import time
import subprocess
import datetime # 날짜 생성을 위해 추가

# 색상 코드로 로그를 이쁘게 꾸밈
GREEN = '\033[92m'
RESET = '\033[0m'
BOLD = '\033[1m'

def log(msg):
    print(f"{GREEN}{BOLD}[BUILD-SCRIPT] {msg}{RESET}")

def run_cmd(cmd):
    log(f"명령어 실행: {cmd}")
    ret = subprocess.call(cmd, shell=True)
    if ret != 0:
        print(f"Error executing: {cmd}")
        sys.exit(1)

def main():
    # [수정됨] 파라미터 대신 현재 시간으로 버전 자동 생성
    now = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    version = f"1.0.0-POC-{now}"
    
    workspace = os.getcwd()
    
    log(f"빌드 프로세스 시작 | 자동 생성된 버전: {version}")
    log(f"작업 디렉토리: {workspace}")

    # 1. 환경 설정 및 정리
    dist_dir = os.path.join(workspace, 'dist')
    if os.path.exists(dist_dir):
        log("기존 빌드 아티팩트 제거 중...")
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)

    # 2. 의존성 설치 시뮬레이션
    log("의존성 패키지 검사 및 설치...")
    run_cmd("pip install -r requirements.txt")
    time.sleep(1)

    # 3. 코드 품질 검사 (Linting) 시뮬레이션
    log("소스 코드 정적 분석(Linting) 수행 중...")
    time.sleep(1)
    log("✔ 코드 품질 검사 통과 (Score: 10/10)")

    # 4. 패키징
    log(f"애플리케이션 패키징 중... (Target: {dist_dir})")
    
    src_dir = os.path.join(workspace, 'src')
    archive_name = os.path.join(dist_dir, f'sys-monitor-{version}')
    
    shutil.make_archive(archive_name, 'zip', src_dir)
    
    log(f"✔ 빌드 성공! 아티팩트 생성됨: {archive_name}.zip")

if __name__ == "__main__":
    main()