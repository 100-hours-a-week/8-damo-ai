import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from shared.utils.config import settings


def get_chat_llm(temperature: float = 0.7, local: bool = False) -> BaseChatModel:
    """LLM 인스턴스를 반환하는 팩토리 함수.

    local=False (기본): OpenAI API 사용 (분석가, 선정 등)
    local=True:         로컬 모델 사용 (페르소나 반응/투표 등)

    각각 OPENAI_BASE_URL / LOCAL_BASE_URL이 설정되면
    해당 엔드포인트로 요청한다.
    (LiteLLM 프록시, vLLM, Ollama 등 OpenAI 호환 서버 지원)

    LLM_NO_KEEPALIVE=1 환경변수 설정 시 httpx keepalive 비활성화.
    asyncio.run()을 반복 호출하는 평가 도구 등에서 이벤트 루프 간
    stale 커넥션 문제를 방지한다.
    """
    if local and settings.LOCAL_MODEL:
        kwargs: dict[str, Any] = {
            "model": settings.LOCAL_MODEL,
            "temperature": temperature,
            "api_key": settings.LOCAL_API_KEY,
            "streaming": True,
            "stream_usage": True,
        }
        if settings.LOCAL_BASE_URL:
            kwargs["base_url"] = settings.LOCAL_BASE_URL
    else:
        kwargs = {
            "model": settings.OPENAI_MODEL,
            "temperature": temperature,
            "api_key": settings.OPENAI_API_KEY,
            "streaming": True,
            "stream_usage": True,
        }
        if settings.OPENAI_BASE_URL:
            kwargs["base_url"] = settings.OPENAI_BASE_URL

    if os.environ.get("LLM_NO_KEEPALIVE"):
        import httpx
        kwargs["http_async_client"] = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=0)
        )

    return ChatOpenAI(**kwargs)
