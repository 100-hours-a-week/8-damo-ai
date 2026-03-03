import json
import logging
import os
from faststream.asgi import AsgiResponse, get
from faststream.asgi.types import Scope

LOG_FILE = "faststream_web.log"

def setup_web_logging():
    # [변경] 서버 시작 시 기존 로그 파일 초기화 (모드 'w'로 열어서 비움)
    try:
        with open(LOG_FILE, 'w') as f:
            f.write("--- Log Initialized (New Session) ---\n")
    except Exception as e:
        print(f"Failed to clear log file: {e}")
    root_logger = logging.getLogger()
    if any(isinstance(h, logging.FileHandler) and h.baseFilename.endswith(LOG_FILE) for h in root_logger.handlers):
        return
    # [중요] 'a' 모드로 열어야 여러 워커가 동시에 쓸 때 꼬이지 않습니다.
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8', delay=False)
    formatter = logging.Formatter('%(asctime)s - [%(process)d] - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    
    fs_logger = logging.getLogger("faststream")
    fs_logger.addHandler(file_handler)
    fs_logger.propagate = True
# 2. 실행 시 로그 초기화 및 설정
setup_web_logging()

@get
async def health_check(scope: Scope) -> AsgiResponse:
    data = {"status": "ok", "service": "damo-ai-server"}
    body = json.dumps(data).encode("utf-8")
    return AsgiResponse(
        body, 
        status_code=200,
        headers={"content-type": "application/json"}
    )

@get
async def log_check(scope: Scope) -> AsgiResponse:
    if not os.path.exists(LOG_FILE):
        return AsgiResponse(b"No logs recorded yet.", status_code=200)
    
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            # [변경] 로그의 역순 정렬 (최신이 맨 위로)
            lines.reverse()
            # 최대 100줄만 보여주기
            logs_text = "".join(lines[:200])
            
        return AsgiResponse(
            logs_text.encode("utf-8"),
            status_code=200,
            headers={"content-type": "text/plain; charset=utf-8"}
        )
    except Exception as e:
        return AsgiResponse(f"Error reading logs: {e}".encode("utf-8"), status_code=500)
