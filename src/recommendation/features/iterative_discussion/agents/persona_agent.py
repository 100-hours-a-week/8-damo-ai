"""PersonaAgent 클래스

사용자 페르소나를 기반으로 토론에 참여하는 에이전트입니다.
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent
from .llm_config import get_persona_llm
from ..prompts.persona_prompts import (
    PERSONA_DISCUSSION_PROMPT,
    PERSONA_VOTE_PROMPT,
    format_persona_info,
)


class PersonaAgent(BaseAgent):
    """사용자 페르소나를 대변하는 에이전트

    사용자의 음식 취향, 선호도, 제약사항을 기반으로
    토론에 참여하고 투표를 진행합니다.

    Attributes:
        user_id: 사용자 ID
        persona_data: 페르소나 정보 (선호도, 제약사항 등)
        discussion_chain: 토론 참여용 LLM 체인
        vote_chain: 투표용 LLM 체인
    """

    def __init__(
        self,
        user_id: int,
        persona_data: Optional[Dict[str, Any]] = None,
        llm: Optional[ChatGoogleGenerativeAI] = None,
    ):
        """PersonaAgent 초기화

        Args:
            user_id: 사용자 ID
            persona_data: 페르소나 정보 (선호도, 제약사항 등)
            llm: LLM 인스턴스 (None이면 기본 Persona LLM 사용)
        """
        if llm is None:
            llm = get_persona_llm()

        super().__init__(
            llm=llm,
            name=f"agent_{user_id}",
            temperature=0.8,  # 창의적이고 자연스러운 응답
        )

        self.user_id = user_id
        self.persona_data = persona_data or self._get_default_persona()

        # LLM 체인 초기화
        self.discussion_chain = PERSONA_DISCUSSION_PROMPT | self.llm
        self.vote_chain = PERSONA_VOTE_PROMPT | self.llm

    def _get_default_persona(self) -> Dict[str, Any]:
        """기본 페르소나 데이터 반환

        실제 구현에서는 DB에서 조회하거나 API로 가져옴

        Returns:
            기본 페르소나 데이터
        """
        return {
            "name": f"User {self.user_id}",
            "preferences": {
                "likes": ["한식", "고기"],
                "dislikes": ["생선회"],
            },
            "constraints": [],
            "personality": "친근하고 솔직함",
        }

    async def generate_response(
        self,
        context: Dict[str, Any],
        messages: Optional[List[BaseMessage]] = None,
    ) -> str:
        """토론 참여 응답 생성

        Args:
            context: 토론 컨텍스트 (라운드, 후보 등)
            messages: 이전 대화 메시지

        Returns:
            생성된 응답 메시지
        """
        round_num = context.get("round", 1)
        max_rounds = context.get("max_rounds", 3)
        topic = context.get("topic", "식당 선정")
        candidates = context.get("candidates", [])

        # 페르소나 정보 포맷팅
        persona_info = format_persona_info(self.persona_data)

        # 후보 정보 포맷팅
        candidates_info = self._format_candidates(candidates)

        # 대화 히스토리 포맷팅
        conversation_history = self._format_conversation(messages or [])

        # LLM 호출
        response = await self.discussion_chain.ainvoke(
            {
                "persona_info": persona_info,
                "round_num": round_num,
                "max_rounds": max_rounds,
                "topic": topic,
                "candidates_info": candidates_info,
                "conversation_history": conversation_history,
            }
        )

        return response.content

    async def participate_discussion(
        self,
        round_num: int,
        candidates: List[Dict[str, Any]],
        topic: str,
        previous_messages: List[BaseMessage],
        max_rounds: int = 3,
    ) -> AIMessage:
        """토론에 참여하여 의견 제시

        Args:
            round_num: 현재 라운드 번호
            candidates: 후보 식당 목록
            topic: 토론 주제
            previous_messages: 이전 대화 메시지
            max_rounds: 최대 라운드 수

        Returns:
            생성된 의견 메시지
        """
        context = {
            "round": round_num,
            "max_rounds": max_rounds,
            "topic": topic,
            "candidates": candidates,
        }

        response_content = await self.generate_response(
            context=context,
            messages=previous_messages,
        )

        return AIMessage(
            content=response_content,
            name=self.name,
        )

    async def vote(
        self,
        candidates: List[Dict[str, Any]],
        discussion_summary: str,
    ) -> Dict[str, str]:
        """최종 투표 진행

        Args:
            candidates: 최종 후보 식당 목록
            discussion_summary: 토론 요약

        Returns:
            투표 결과 {"restaurant_id": str, "reason": str}
        """
        # 페르소나 정보 포맷팅
        persona_info = format_persona_info(self.persona_data)

        # 후보 정보 포맷팅
        candidates_info = self._format_candidates(candidates)

        # LLM 호출
        response = await self.vote_chain.ainvoke(
            {
                "persona_info": persona_info,
                "candidates_info": candidates_info,
                "discussion_summary": discussion_summary,
            }
        )

        # 응답 파싱
        vote_result = self._parse_vote_response(response.content, candidates)

        return vote_result

    def _format_candidates(self, candidates: List[Dict[str, Any]]) -> str:
        """후보 식당 목록을 포맷팅

        Args:
            candidates: 후보 식당 목록 (RestaurantCandidate)

        Returns:
            포맷팅된 문자열
        """
        if not candidates:
            return "후보 식당 없음"

        # entities.restaurant의 format_restaurants_for_prompt 사용
        from ..entities import format_restaurants_for_prompt

        return format_restaurants_for_prompt(candidates)

    def _format_conversation(self, messages: List[BaseMessage]) -> str:
        """대화 히스토리를 포맷팅

        Args:
            messages: 메시지 목록

        Returns:
            포맷팅된 대화 히스토리
        """
        if not messages:
            return "이전 대화 없음"

        # 최근 10개 메시지만 사용
        recent_messages = messages[-10:]

        formatted = []
        for msg in recent_messages:
            speaker = getattr(msg, "name", "unknown")
            content = msg.content.strip()
            formatted.append(f"[{speaker}]: {content}")

        return "\n".join(formatted)

    def _parse_vote_response(
        self,
        response: str,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """투표 응답 파싱

        Args:
            response: LLM 응답
            candidates: 후보 목록

        Returns:
            {"restaurant_id": str, "reason": str}
        """
        lines = response.strip().split("\n")

        restaurant_id = None
        reason = ""

        for line in lines:
            line = line.strip()
            if line.startswith("선택:"):
                restaurant_id = line.replace("선택:", "").strip()
            elif line.startswith("이유:"):
                reason = line.replace("이유:", "").strip()

        # 유효성 검증
        if not restaurant_id:
            # 첫 번째 후보로 폴백
            restaurant_id = (
                candidates[0].get("id", "unknown") if candidates else "unknown"
            )
            reason = "파싱 실패로 인한 기본 선택"

        return {
            "restaurant_id": restaurant_id,
            "reason": reason or "이유 없음",
        }
