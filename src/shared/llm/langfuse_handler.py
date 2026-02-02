import hashlib
from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler
from src.core.config import settings

# 클라이언트 전역 초기화
langfuse_client = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_BASE_URL
)

def get_langfuse_callback(prefix: str, source_id: any):
    """
    prefix_name: 'recommendation', 'analyze' 등 사람이 읽기 좋은 이름
    source_id: dining_id 등 추적의 기준이 되는 ID (int, str 모두 가능)
    """
    # 1. source_id를 안전하게 문자열로 변환 후 해싱 (28자리)
    str_source_id = str(source_id)
    id_hash = hashlib.md5(str_source_id.encode()).hexdigest()[4:]
    
    # 2. prefix도 해싱하여 16진수 접두어(4자리) 생성
    # 이렇게 하면 'recommendation'이 들어와도 안전한 16진수 '45f1' 등으로 바뀝니다.
    prefix_hex = hashlib.md5(prefix.encode()).hexdigest()[:4]
    
    # 3. 최종 32자리 16진수 trace_id 생성
    trace_id = prefix_hex + id_hash
    
    return CallbackHandler(
        trace_context={"trace_id": trace_id}
    )

def flush_langfuse():
    """Langfuse 전역 클라이언트의 데이터를 전송합니다."""
    langfuse_client.flush()