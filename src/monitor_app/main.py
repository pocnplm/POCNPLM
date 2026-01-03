import sys
import time
# argparse 제거
from .core import SystemMonitor
from .utils import setup_logger

log = setup_logger("MainEntry")

def main():
    # 파라미터 없이 내부적으로 기본값 설정
    target_env = "dev" 

    log.info(">>> 모니터링 에이전트 초기화 중...")
    log.info(f"설정된 환경: {target_env} (Default)")
    
    try:
        monitor = SystemMonitor(target_env)
        result = monitor.scan_resources()
        
        log.info(f"진단 결과: {result}")
        log.info("프로세스가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        log.error(f"치명적인 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()