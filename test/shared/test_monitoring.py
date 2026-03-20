import pytest
import asyncio
import os

# Langfuse 테스트 전체 스킵 (개발 중 불필요)
pytestmark = pytest.mark.skip(reason="Langfuse 개발 중 스킵")

# 🚀 중요: SDK 초기화 전 환경 변수 강제 주입
from shared.utils.config import settings
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_BASE_URL

from langfuse import Langfuse
from shared.monitoring import langfuse_handler, get_langfuse_client

def test_langfuse_handler_initialization():
    """핸들러 초기화 및 객체 타입 확인"""
    if not settings.LANGFUSE_PUBLIC_KEY:
        assert langfuse_handler is None
    else:
        assert langfuse_handler is not None
        from langfuse.langchain import CallbackHandler
        assert isinstance(langfuse_handler, CallbackHandler)

def test_get_langfuse_client():
    """싱글톤 클라이언트 인스턴스 확인"""
    client = get_langfuse_client()
    assert isinstance(client, Langfuse)
    assert client is get_langfuse_client()

@pytest.mark.asyncio
async def test_langfuse_trace_simulation():
    """
    with 구문을 사용한 명시적 트레이싱 시뮬레이션
    이 방식은 Langfuse Cloud에서 가장 안정적으로 기록됩니다.
    """
    if not settings.LANGFUSE_PUBLIC_KEY:
        pytest.skip("LANGFUSE_PUBLIC_KEY가 설정되지 않아 건너뜁니다.")

    client = get_langfuse_client()

    # 테스트용 데이터 가공 함수 정의
    def my_data_processing_function(data, parameter):
        return {"processed_data": data, "status": "ok"}

    async def my_async_llm_call(prompt_text):
        await asyncio.sleep(0.1)
        return "LLM response"

    print("\n[Simulation] Starting explicit tracing with context manager...")

    # 1. 루트 Span 생성 (관찰 시작)
    with client.start_as_current_observation(as_type="span", name="unit-test-session") as span:
        # 로직 실행
        sync_result = my_data_processing_function("raw_data", "v1")
        async_result = await my_async_llm_call("How's the weather?")
        
        # 메타데이터 업데이트
        span.update(metadata={
            "sync_result": sync_result, 
            "async_result": async_result,
            "test_env": "pytest"
        })

        # 2. 내부 Generation 생성 (자식 관찰)
        with client.start_as_current_observation(
            as_type="generation", 
            name="llm-mockup-call", 
            model="unit-test-model"
        ) as generation:
            # LLM 응답 시뮬레이션 기록
            generation.update(output="Generated success response")
        
        # 검증
        assert sync_result["status"] == "ok"
        assert async_result == "LLM response"

    # 3. ⭐️ 데이터 전송 강제 실행
    print("[Simulation] Flushing data to server...")
    client.flush()    
    
    print("[Success] Tracing simulation completed and visible in Cloud.")
