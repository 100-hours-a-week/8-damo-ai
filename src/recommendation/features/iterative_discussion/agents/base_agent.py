"""기본 Agent 추상 클래스

모든 에이전트(Moderator, PersonaAgent 등)의 공통 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class BaseAgent(ABC):
    """모든 에이전트의 기본 추상 클래스

    Attributes:
        llm: LangChain LLM 인스턴스
        name: 에이전트 이름
        temperature: LLM temperature 설정
    """

    def __init__(
        self, llm: ChatGoogleGenerativeAI, name: str, temperature: float = 0.7
    ):
        """BaseAgent 초기화

        Args:
            llm: LangChain LLM 인스턴스
            name: 에이전트 이름
            temperature: LLM temperature (기본값: 0.7)
        """
        self.llm = llm
        self.name = name
        self.temperature = temperature

    @abstractmethod
    async def generate_response(
        self, context: Dict[str, Any], messages: Optional[List[BaseMessage]] = None
    ) -> str:
        """에이전트 응답 생성 (추상 메서드)

        Args:
            context: 컨텍스트 정보 (상태, 후보 등)
            messages: 이전 대화 메시지 목록

        Returns:
            생성된 응답 텍스트
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', temperature={self.temperature})"
