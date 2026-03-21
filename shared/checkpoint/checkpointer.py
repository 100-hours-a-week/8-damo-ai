"""LangGraph 체크포인터 싱글톤 관리.

AsyncSqliteSaver를 앱 수명 동안 단일 연결로 유지한다.
재시작 시 dining_id(thread_id) 기준으로 중단된 그래프를 이어서 실행할 수 있다.
"""
import asyncio
import logging

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger(__name__)

_checkpointer: AsyncSqliteSaver | None = None
_conn: aiosqlite.Connection | None = None
_init_lock: asyncio.Lock | None = None


def _get_init_lock() -> asyncio.Lock:
    global _init_lock
    if _init_lock is None:
        _init_lock = asyncio.Lock()
    return _init_lock


async def init_checkpointer(db_path: str = "checkpoints.db") -> AsyncSqliteSaver:
    """앱 시작 시 호출. SQLite 연결을 열고 체크포인터 테이블을 생성한다."""
    global _checkpointer, _conn
    async with _get_init_lock():
        if _checkpointer is not None:
            return _checkpointer

        _conn = await aiosqlite.connect(db_path)
        # WAL 모드: 동시 읽기/쓰기 성능 향상
        await _conn.execute("PRAGMA journal_mode=WAL")
        await _conn.commit()

        _checkpointer = AsyncSqliteSaver(_conn)
        await _checkpointer.setup()  # checkpoint 테이블 생성
        logger.info("LangGraph 체크포인터 초기화 완료: %s", db_path)
        return _checkpointer


async def close_checkpointer() -> None:
    """앱 종료 시 호출. SQLite 연결을 닫는다."""
    global _checkpointer, _conn
    if _conn is not None:
        await _conn.close()
        _conn = None
        _checkpointer = None
        logger.info("LangGraph 체크포인터 종료")


def get_checkpointer() -> AsyncSqliteSaver | None:
    """현재 체크포인터 인스턴스를 반환. 초기화 전이면 None."""
    return _checkpointer
