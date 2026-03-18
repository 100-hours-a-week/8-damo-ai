"""Langfuse Prompt Management 연동 유틸리티.

Langfuse 대시보드에서 프롬프트를 가져오고 로컬 상수를 fallback으로 사용한다.
Langfuse SDK는 내부적으로 60초 TTL 캐시를 사용하므로 매 호출마다 API를 치지 않는다.
"""
import logging
from typing import Any, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler


def make_callback_handler() -> LangfuseCallbackHandler:
    """LangfuseCallbackHandler 인스턴스 반환.
    prompt 링크는 ChatPromptTemplate.metadata 방식으로 처리한다.
    """
    return LangfuseCallbackHandler()


logger = logging.getLogger(__name__)


def _get_client():
    from langfuse import get_client
    return get_client()


def get_prompt(
    name: str,
    fallback: str,
    **variables: Any,
) -> Tuple[str, Any]:
    """Langfuse에서 프롬프트를 가져와 컴파일. 실패 시 로컬 상수 fallback.

    Args:
        name: Langfuse 대시보드에 등록한 프롬프트 이름
        fallback: Langfuse 연결 실패 시 사용할 로컬 프롬프트 문자열 ({variable} 포맷)
        **variables: 프롬프트 변수 (Langfuse: {{variable}}, fallback: {variable})

    Returns:
        (compiled_text, prompt_obj | None)
        prompt_obj는 LangfuseCallbackHandler(prompt=prompt_obj)로 generation에 연결할 때 사용.
    """
    try:
        prompt = _get_client().get_prompt(name)
        compiled = prompt.compile(**variables)
        logger.info("[Prompt] Langfuse '%s' v%s 로드 성공", name, prompt.version)
        return compiled, prompt
    except Exception as e:
        logger.warning("[Prompt] Langfuse '%s' 로드 실패 — fallback 사용: %s", name, e)
        return fallback.format(**variables), None


def _to_langchain_messages(messages: list[dict]) -> List[BaseMessage]:
    role_map: dict[str, type] = {
        "system": SystemMessage,
        "user": HumanMessage,
        "assistant": AIMessage,
    }
    return [role_map[m["role"]](content=m["content"]) for m in messages]


def get_chat_prompt(
    name: str,
    fallback_messages: list[dict],
    **variables: Any,
) -> Tuple[List[BaseMessage], Any]:
    """Chat 타입 프롬프트를 Langfuse에서 fetch하여 LangChain 메시지 리스트로 반환.

    Args:
        name: Langfuse 대시보드에 등록한 chat 타입 프롬프트 이름
        fallback_messages: Langfuse 연결 실패 시 사용할 메시지 리스트
            [{"role": "user", "content": "..."}, ...]
            content은 str.format(**variables)로 렌더링됨
        **variables: 프롬프트 변수

    Returns:
        (lc_messages, prompt_obj | None)
    """
    try:
        prompt = _get_client().get_prompt(name, type="chat")
        compiled = prompt.compile(**variables)
        lc_messages = _to_langchain_messages(
            [
                {
                    "role": m["role"] if isinstance(m, dict) else m.role,
                    "content": m["content"] if isinstance(m, dict) else m.content,
                }
                for m in compiled
            ]
        )
        logger.info("[Prompt] Langfuse '%s' v%s (chat) 로드 성공", name, prompt.version)
        return lc_messages, prompt
    except Exception as e:
        logger.warning("[Prompt] Langfuse '%s' 로드 실패 — fallback 사용: %s", name, e)
        str_vars = {k: v for k, v in variables.items() if not isinstance(v, list)}
        rendered: list[dict] = []
        for m in fallback_messages:
            if m["role"] == "placeholder":
                rendered.extend(variables.get(m["variable_name"], []))
            else:
                rendered.append({"role": m["role"], "content": m["content"].format(**str_vars)})
        return _to_langchain_messages(rendered), None
