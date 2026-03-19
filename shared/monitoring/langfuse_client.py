# dev/shared/monitoring/langfuse/client.py
import logging
import os
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from shared.utils.config import settings

logger = logging.getLogger(__name__)

os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_BASE_URL

logger.info(
    "[Langfuse] env 설정: host=%s, public_key=%s",
    settings.LANGFUSE_BASE_URL or "MISSING",
    f"{settings.LANGFUSE_PUBLIC_KEY[:6]}..." if settings.LANGFUSE_PUBLIC_KEY else "MISSING",
)

class LangfuseManager:
    _handler = None

    @classmethod
    def get_client(cls):
        return get_client()

    @classmethod
    def get_handler(cls) -> CallbackHandler:
        """LangChain의 config={'callbacks': [handler]} 형태로 사용"""
        if not settings.LANGFUSE_PUBLIC_KEY:
            return None

        if cls._handler is None:
            # 인수 없이 생성 — os.environ에서 public_key, secret_key, host 모두 읽음
            cls._handler = CallbackHandler()
        return cls._handler

# Singleton 인스턴스 생성 프로세스를 단순화하기 위한 유틸리티 함수
def get_langfuse_handler():
    return LangfuseManager.get_handler()

def get_langfuse_client():
    return LangfuseManager.get_client()
