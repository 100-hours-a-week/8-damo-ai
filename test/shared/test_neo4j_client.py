import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def reset_neo4j_client():
    """각 테스트 전후로 싱글턴 상태를 초기화."""
    from shared.database.neo4j_client import Neo4jClient
    Neo4jClient._driver = None
    yield
    Neo4jClient._driver = None


@pytest.mark.asyncio
async def test_get_driver_returns_singleton():
    """같은 드라이버 인스턴스를 반환하는지 확인 (싱글턴)."""
    from shared.database.neo4j_client import Neo4jClient

    with patch("shared.database.neo4j_client.AsyncGraphDatabase.driver") as mock_driver:
        mock_driver.return_value = MagicMock()

        driver1 = await Neo4jClient.get_driver()
        driver2 = await Neo4jClient.get_driver()

        assert driver1 is driver2
        assert mock_driver.call_count == 1


@pytest.mark.asyncio
async def test_get_driver_uses_settings():
    """settings의 NEO4J_URI, USERNAME, PASSWORD를 사용하는지 확인."""
    from shared.database.neo4j_client import Neo4jClient

    with patch("shared.database.neo4j_client.AsyncGraphDatabase.driver") as mock_driver:
        mock_driver.return_value = MagicMock()

        await Neo4jClient.get_driver()

        call_args = mock_driver.call_args
        assert call_args is not None
        # 첫 번째 positional 인자가 URI
        assert "neo4j" in call_args[0][0] or "neo4j" in str(call_args)
        # auth 튜플 전달 여부
        assert "auth" in call_args[1]


@pytest.mark.asyncio
async def test_close_sets_driver_to_none():
    """close() 호출 후 _driver가 None이 되는지 확인."""
    from shared.database.neo4j_client import Neo4jClient

    with patch("shared.database.neo4j_client.AsyncGraphDatabase.driver") as mock_driver:
        mock_instance = AsyncMock()
        mock_driver.return_value = mock_instance

        await Neo4jClient.get_driver()
        assert Neo4jClient._driver is not None

        await Neo4jClient.close()

        assert Neo4jClient._driver is None
        mock_instance.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_when_no_driver_does_nothing():
    """드라이버 없이 close() 호출해도 예외 없이 동작하는지 확인."""
    from shared.database.neo4j_client import Neo4jClient

    assert Neo4jClient._driver is None
    await Neo4jClient.close()  # 예외 없어야 함
    assert Neo4jClient._driver is None


@pytest.mark.asyncio
async def test_get_driver_propagates_connection_error():
    """드라이버 생성 실패 시 예외가 전파되고 _driver가 None으로 유지되는지 확인."""
    from shared.database.neo4j_client import Neo4jClient

    with patch("shared.database.neo4j_client.AsyncGraphDatabase.driver") as mock_driver:
        mock_driver.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            await Neo4jClient.get_driver()

        assert Neo4jClient._driver is None
