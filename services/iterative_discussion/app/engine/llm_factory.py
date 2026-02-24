from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from shared.utils.config import settings


def get_chat_llm(temperature: float = 0.7, local: bool = False) -> BaseChatModel:
    """LLM 인스턴스를 반환하는 팩토리 함수.

    local=False (기본): OpenAI API 사용 (사회자, 투표 등)
    local=True:         로컬 모델 사용 (페르소나 대화 등)

    각각 OPENAI_BASE_URL / LOCAL_BASE_URL이 설정되면
    해당 엔드포인트로 요청한다.
    (LiteLLM 프록시, vLLM, Ollama 등 OpenAI 호환 서버 지원)
    """
    if local and settings.LOCAL_MODEL:
        kwargs: dict[str, Any] = {
            "model": settings.LOCAL_MODEL,
            "temperature": temperature,
            "api_key": settings.LOCAL_API_KEY,
        }
        if settings.LOCAL_BASE_URL:
            kwargs["base_url"] = settings.LOCAL_BASE_URL
    else:
        kwargs = {
            "model": settings.OPENAI_MODEL,
            "temperature": temperature,
        }
        if settings.OPENAI_BASE_URL:
            kwargs["base_url"] = settings.OPENAI_BASE_URL
    return ChatOpenAI(**kwargs)
