import logging
import sys

def setup_logger(name):
    """전문적인 포맷의 로거를 생성합니다."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 포맷: [시간] [레벨] [모듈명] 메시지
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger