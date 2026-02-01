"""Moderator Agent 구현

토론 중재자 역할을 수행하는 LLM 기반 에이전트입니다.
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .base_agent import BaseAgent
from .llm_config import get_moderator_llm
from ..prompts.moderator_prompts import (
    TOPIC_PROPOSAL_PROMPT,
    SUMMARIZE_PROMPT,
    CONSENSUS_GUIDE_PROMPT,
    RANK_CANDIDATES_PROMPT,
)
from langchain_core.output_parsers import JsonOutputParser


class ModeratorAgent(BaseAgent):
    """토론 중재자 에이전트

    멀티에이전트 토론에서 중재자 역할을 수행합니다:
    - 라운드 시작 발제
    - 토론 내용 요약
    - 합의 유도

    Attributes:
        llm: LangChain LLM 인스턴스
        name: 에이전트 이름 (기본값: "moderator")
        topic_chain: 발제용 LLM Chain
        summary_chain: 요약용 LLM Chain
        consensus_chain: 합의 유도용 LLM Chain
    """

    def __init__(self, llm: Optional[ChatGoogleGenerativeAI] = None):
        """ModeratorAgent 초기화

        Args:
            llm: LangChain LLM 인스턴스 (None이면 자동 생성)
        """
        if llm is None:
            llm = get_moderator_llm()

        super().__init__(llm=llm, name="moderator", temperature=0.3)

        # LLM Chain 초기화
        self.topic_chain = TOPIC_PROPOSAL_PROMPT | self.llm
        self.summary_chain = SUMMARIZE_PROMPT | self.llm
        self.consensus_chain = CONSENSUS_GUIDE_PROMPT | self.llm
        self.rank_chain = RANK_CANDIDATES_PROMPT | self.llm | JsonOutputParser()

    async def generate_response(
        self, context: Dict[str, Any], messages: Optional[List[BaseMessage]] = None
    ) -> str:
        """에이전트 응답 생성 (BaseAgent 추상 메서드 구현)

        Note: ModeratorAgent는 특화된 메서드(propose_topic, summarize_discussion 등)를
        사용하므로 이 메서드는 직접 호출되지 않습니다.

        Args:
            context: 컨텍스트 정보
            messages: 이전 대화 메시지

        Returns:
            생성된 응답 텍스트
        """
        # 기본 구현 (실제로는 특화된 메서드 사용)
        return "Moderator response"

    def _format_candidates(self, candidates: List[Dict[str, Any]]) -> str:
        """후보 식당 목록을 포맷팅

        Args:
            candidates: 후보 식당 목록

        Returns:
            포맷팅된 문자열
        """
        if not candidates:
            return "후보 식당이 없습니다."

        formatted = []
        for i, candidate in enumerate(candidates, 1):
            name = candidate.get("name", "Unknown")
            category = candidate.get("category", "N/A")
            location = candidate.get("location", "N/A")
            formatted.append(f"{i}. {name} (카테고리: {category}, 위치: {location})")

        return "\n".join(formatted)

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """메시지 목록을 포맷팅

        Args:
            messages: 메시지 목록

        Returns:
            포맷팅된 문자열
        """
        if not messages:
            return "토론 내용이 없습니다."

        formatted = []
        for msg in messages:
            speaker = getattr(msg, "name", "unknown")
            content = msg.content.strip()
            formatted.append(f"[{speaker}]: {content}")

        return "\n\n".join(formatted)

    async def propose_topic(
        self,
        round_num: int,
        candidates: List[Dict[str, Any]],
        max_rounds: int = 3,
        previous_summary: Optional[str] = None,
    ) -> AIMessage:
        """라운드 시작 발제

        Args:
            round_num: 현재 라운드 번호
            candidates: 후보 식당 목록
            max_rounds: 최대 라운드 수
            previous_summary: 이전 라운드 요약 (2라운드 이상인 경우)

        Returns:
            발제 메시지 (AIMessage)
        """
        candidates_info = self._format_candidates(candidates)
        previous_summary_text = previous_summary or "첫 번째 라운드입니다."

        # LLM 호출
        response = await self.topic_chain.ainvoke(
            {
                "round_num": round_num,
                "max_rounds": max_rounds,
                "candidates_info": candidates_info,
                "previous_summary": previous_summary_text,
            }
        )

        return AIMessage(content=response.content, name=self.name)

    async def summarize_discussion(
        self,
        round_num: int,
        messages: List[BaseMessage],
        candidates: List[Dict[str, Any]],
    ) -> AIMessage:
        """토론 내용 요약

        Args:
            round_num: 현재 라운드 번호
            messages: 토론 메시지 목록
            candidates: 후보 식당 목록

        Returns:
            요약 메시지 (AIMessage)
        """
        # 에이전트 메시지만 추출 (moderator 메시지 제외)
        agent_messages = [
            msg
            for msg in messages
            if hasattr(msg, "name") and msg.name and msg.name.startswith("agent_")
        ]

        candidates_info = self._format_candidates(candidates)
        discussion_text = self._format_messages(agent_messages)
        num_participants = len(
            set(msg.name for msg in agent_messages if hasattr(msg, "name") and msg.name)
        )

        # LLM 호출
        response = await self.summary_chain.ainvoke(
            {
                "round_num": round_num,
                "num_participants": num_participants,
                "candidates_info": candidates_info,
                "discussion_messages": discussion_text,
            }
        )

        return AIMessage(content=response.content, name=self.name)

    async def guide_consensus(
        self,
        round_num: int,
        max_rounds: int,
        messages: List[BaseMessage],
        candidates: List[Dict[str, Any]],
        votes: Optional[Dict[str, str]] = None,
    ) -> AIMessage:
        """합의 유도

        Args:
            round_num: 현재 라운드 번호
            max_rounds: 최대 라운드 수
            messages: 토론 메시지 목록
            candidates: 후보 식당 목록
            votes: 현재 투표 현황 (있는 경우)

        Returns:
            합의 유도 메시지 (AIMessage)
        """
        candidates_info = self._format_candidates(candidates)

        # 토론 요약 추출 (마지막 요약 메시지 찾기)
        summary_messages = [
            msg
            for msg in messages
            if hasattr(msg, "name") and msg.name == self.name and "요약" in msg.content
        ]
        discussion_summary = (
            summary_messages[-1].content
            if summary_messages
            else "토론 요약이 없습니다."
        )

        # 투표 현황 포맷팅
        if votes:
            vote_lines = [
                f"- {agent}: {restaurant_id}" for agent, restaurant_id in votes.items()
            ]
            current_votes = "\n".join(vote_lines)
        else:
            current_votes = "아직 투표가 없습니다."

        # LLM 호출
        response = await self.consensus_chain.ainvoke(
            {
                "round_num": round_num,
                "max_rounds": max_rounds,
                "candidates_info": candidates_info,
                "discussion_summary": discussion_summary,
                "current_votes": current_votes,
            }
        )

        return AIMessage(content=response.content, name=self.name)

    async def rank_candidates(
        self,
        messages: List[BaseMessage],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """토론 내용을 바탕으로 후보 식당 순위 선정

        Args:
            messages: 토론 메시지 목록
            candidates: 후보 식당 목록

        Returns:
            순위 정보 (ranked_restaurant_ids, reasoning)
        """
        candidates_info = self._format_candidates(candidates)

        # 토론 요약 추출 (마지막 요약 메시지 찾기)
        summary_messages = [
            msg
            for msg in messages
            if hasattr(msg, "name") and msg.name == self.name and "요약" in msg.content
        ]
        discussion_summary = (
            summary_messages[-1].content
            if summary_messages
            else "토론 요약이 없습니다."
        )

        # 에이전트들의 실제 대화 내용 추출
        agent_messages = [
            msg
            for msg in messages
            if hasattr(msg, "name") and msg.name and msg.name.startswith("agent_")
        ]
        discussion_text = self._format_messages(agent_messages)

        # LLM 호출
        try:
            response = await self.rank_chain.ainvoke(
                {
                    "candidates_info": candidates_info,
                    "discussion_summary": discussion_summary,
                    "messages": discussion_text,
                }
            )
            return response
        except Exception as e:
            # 파싱 에러 또는 기타 오류 발생 시 로깅하고 빈 결과 반환
            print(f"Error ranking candidates: {e}")
            return {"ranked_restaurant_ids": [], "reasoning": "랭킹 생성 실패"}
