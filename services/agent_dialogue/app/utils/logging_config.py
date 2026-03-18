import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """RunPod/컨테이너 환경용 stdout 로깅 설정.

    Python 기본 레벨이 WARNING이므로 INFO 로그가 누락되지 않도록
    basicConfig를 명시적으로 호출하고, stdout으로 강제 출력한다.
    """
    fmt = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    # 외부 라이브러리 verbose 로그 억제
    for noisy_logger in ("httpx", "httpcore", "openai", "urllib3", "asyncio"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
