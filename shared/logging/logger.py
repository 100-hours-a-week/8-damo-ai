import logging
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI

correlation_id_ctx_var: ContextVar[str] = ContextVar("correlation_id", default="")

def get_correlation_id() -> str:
    return correlation_id_ctx_var.get()

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id_ctx_var.set(correlation_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        return response

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = get_correlation_id()
        return True

def setup_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(correlation_id)s] [%(name)s] %(message)s')
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())
    if not logger.handlers:
        logger.addHandler(handler)
    return logger

def setup_prometheus(app: FastAPI, endpoint: str = "/ai/metrics"):
    """
    FastAPI 앱에 Prometheus 모니터링을 설정합니다.
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,   # 200, 201 등을 2xx로 묶어서 보여줄지 여부
        should_ignore_untemplated=True,  # 템플릿화 되지 않은 경로는 무시
        should_respect_env_var=True,     # 환경변수 설정 존중
        env_var_name="ENABLE_METRICS",   # 메트릭 활성/비활성 환경변수명
    )
    
    # 1. 앱과 연결 (Instrumentation)
    instrumentator.instrument(app)
    
    # 2. 메트릭 노출 경로 설정
    instrumentator.expose(app, endpoint=endpoint)
    
    return instrumentator