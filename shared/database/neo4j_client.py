import logging

from neo4j import AsyncGraphDatabase

from shared.utils.config import get_settings

logger = logging.getLogger("faststream")


class Neo4jClient:
    _driver = None

    @classmethod
    async def get_driver(cls):
        if cls._driver is None:
            settings = get_settings()
            cls._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            )
        return cls._driver

    @classmethod
    async def close(cls):
        if cls._driver:
            await cls._driver.close()
            cls._driver = None
