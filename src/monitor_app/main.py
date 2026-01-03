import sys
import time
from .core import SystemMonitor
from .utils import setup_logger

log = setup_logger("MainEntry")

def main():
    # 파라미터 없이 내부적으로 기본값 설정
    target_env = "dev" 

    log.info(">>> Initializing Monitoring Agent...")
    log.info(f"Target Environment: {target_env} (Default)")
    
    try:
        monitor = SystemMonitor(target_env)
        result = monitor.scan_resources()
        
        log.info(f"Diagnostics Result: {result}")
        log.info("Process completed successfully.")
        
    except Exception as e:
        log.error(f"Fatal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()