from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from src.core.config import settings


class Database:
    client: AsyncIOMotorClient = None


db_wrapper = Database()


def get_client() -> AsyncIOMotorClient:
    """MongoDB Client 싱글톤 반환"""
    if db_wrapper.client is None:
        # 이벤트 루프 이슈 방지를 위해 여기서 생성하거나, lifespan에서 생성 권장
        db_wrapper.client = AsyncIOMotorClient(settings.MONGODB_URI)
    return db_wrapper.client


def get_db() -> AsyncIOMotorDatabase:
    """기본 데이터베이스(damo) 반환"""
    client = get_client()
    return client[settings.DB_NAME]
