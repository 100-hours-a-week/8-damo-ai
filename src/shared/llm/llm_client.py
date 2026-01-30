from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from src.core.config import settings


def get_llm(temperature: float = 0.7) -> ChatGoogleGenerativeAI:
    """
    Gemini LLM 인스턴스를 반환합니다.
    """

    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        temperature=temperature,
        google_api_key=settings.GOOGLE_API_KEY,
        convert_system_message_to_human=True,  # 시스템 메시지 호환성 옵션
    )

def get_openai_llm(temperature: float = 0.7) -> ChatOpenAI:
    """
    OpenAI LLM 인스턴스를 반환합니다.
    """
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        openai_api_key=settings.OPENAI_API_KEY,
    )
