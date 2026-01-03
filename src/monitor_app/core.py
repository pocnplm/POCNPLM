import platform
import random
import time
from .utils import setup_logger

log = setup_logger("CoreSystem")

class SystemMonitor:
    def __init__(self, env):
        self.env = env
        self.os_info = platform.system()

    def scan_resources(self):
        log.info(f"시스템 스캔 시작 (Target Environment: {self.env})...")
        time.sleep(1) # 작업하는 척 딜레이
        
        # 복잡한 계산을 하는 척 시뮬레이션
        cpu_usage = random.randint(10, 85)
        memory_usage = random.randint(2048, 8192)
        
        log.info(f"OS 감지됨: {self.os_info}")
        log.info(f"CPU 사용량 분석 완료: {cpu_usage}%")
        log.debug(f"메모리 덤프 분석 중... 할당량: {memory_usage}MB")
        
        return {
            "os": self.os_info,
            "cpu": cpu_usage,
            "memory": memory_usage,
            "status": "STABLE" if cpu_usage < 80 else "CRITICAL"
        }