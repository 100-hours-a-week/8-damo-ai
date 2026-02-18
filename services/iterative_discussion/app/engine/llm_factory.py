from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from shared.utils.config import settings


def get_chat_llm(temperature: float = 0.7) -> BaseChatModel:
    """LLM 인스턴스를 반환하는 팩토리 함수.

    현재는 OpenAI를 사용하며, 나중에 로컬 모델로 교체 시
    이 함수 내부만 변경.
    """
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=temperature,
    )
