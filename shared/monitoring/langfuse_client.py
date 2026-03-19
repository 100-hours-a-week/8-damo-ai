# dev/shared/monitoring/langfuse/client.py
import os
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from shared.utils.config import settings

os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_BASE_URL

class LangfuseManager:
    _instance = None
    _handler = None
    _client = None

    @classmethod
    def get_client(cls) -> Langfuse:
        if cls._client is None:
            cls._client = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_BASE_URL
            )
        return cls._client

    @classmethod
    def get_handler(cls) -> CallbackHandler:
        """LangChain의 config={'callbacks': [handler]} 형태로 사용"""
        if not settings.LANGFUSE_PUBLIC_KEY: 
            return None
            
        if cls._handler is None:
            cls._handler = CallbackHandler(public_key=settings.LANGFUSE_PUBLIC_KEY)
        return cls._handler

# Singleton 인스턴스 생성 프로세스를 단순화하기 위한 유틸리티 함수
def get_langfuse_handler():
    return LangfuseManager.get_handler()

def get_langfuse_client():
    return LangfuseManager.get_client()