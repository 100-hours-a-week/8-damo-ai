"""LLM 초기화 및 설정 유틸리티"""

from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings


def get_llm(temperature: float = 0.7, model: str = None) -> ChatGoogleGenerativeAI:
    """LLM 인스턴스 생성

    Args:
        temperature: LLM temperature (0.0 ~ 1.0)
            - 0.0: 결정적, 일관된 응답
            - 1.0: 창의적, 다양한 응답
        model: 사용할 모델 이름 (기본값: settings.GEMINI_MODEL)

    Returns:
        ChatGoogleGenerativeAI 인스턴스

    Example:
        >>> llm = get_llm(temperature=0.5)
        >>> response = await llm.ainvoke("Hello")
    """
    return ChatGoogleGenerativeAI(
        model=model or settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,  # Gemini는 system 메시지를 human으로 변환 필요
    )


def get_moderator_llm() -> ChatGoogleGenerativeAI:
    """Moderator Agent용 LLM 인스턴스 생성

    중재자는 객관적이고 일관된 응답이 필요하므로 낮은 temperature 사용

    Returns:
        ChatGoogleGenerativeAI 인스턴스 (temperature=0.3)
    """
    return get_llm(temperature=0.3)


def get_persona_llm() -> ChatGoogleGenerativeAI:
    """PersonaAgent용 LLM 인스턴스 생성

    페르소나는 다양하고 개성있는 응답이 필요하므로 높은 temperature 사용

    Returns:
        ChatGoogleGenerativeAI 인스턴스 (temperature=0.8)
    """
    return get_llm(temperature=0.8)
