import sys
import argparse
from .core import SystemMonitor
from .utils import setup_logger

log = setup_logger("MainEntry")

def main():
    # 커맨드라인 인자 파싱 (전문적인 툴 느낌)
    parser = argparse.ArgumentParser(description="System Monitor Agent")
    parser.add_argument("--env", type=str, default="dev", help="실행 환경 (dev/prod)")
    args = parser.parse_args()

    log.info(">>> 모니터링 에이전트 초기화 중...")
    
    try:
        monitor = SystemMonitor(args.env)
        result = monitor.scan_resources()
        
        log.info(f"진단 결과: {result}")
        log.info("프로세스가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        log.error(f"치명적인 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()