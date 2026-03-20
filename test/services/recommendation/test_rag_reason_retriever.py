"""TDD: RAG reason retriever (Neo4j 버전) 단위 테스트.

retriever.py의 retrieve_reviews()와 build_query()를 검증한다.
- driver=None 이면 빈 리스트를 반환
- restaurant_id 없으면 빈 리스트를 반환
- build_query()가 빈 restaurant에서 빈 문자열을 반환
- Neo4j 오류 시 빈 리스트를 반환 (예외 전파 안함)
- 반환값은 generator.py 호환 (page_content 속성 보유)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── build_query ──────────────────────────────────────────────────────────────

class TestBuildQuery:
    def test_empty_restaurant_returns_empty_string(self):
        """빈 restaurant dict에서 빈 문자열을 반환하는지."""
        from services.recommendation.rag_reason.retriever import build_query

        result = build_query({})
        assert result == ""

    def test_includes_place_name(self):
        """place_name이 쿼리에 포함되는지."""
        from services.recommendation.rag_reason.retriever import build_query

        result = build_query({"place_name": "한우집"})
        assert "한우집" in result

    def test_includes_category_detail(self):
        """category_detail이 쿼리에 포함되는지."""
        from services.recommendation.rag_reason.retriever import build_query

        result = build_query({"category_detail": "한식"})
        assert "한식" in result

    def test_includes_top_3_menus(self):
        """상위 3개 메뉴가 쿼리에 포함되는지."""
        from services.recommendation.rag_reason.retriever import build_query

        restaurant = {
            "menus": [
                {"title": "삼겹살"},
                {"title": "된장찌개"},
                {"title": "소주"},
                {"title": "제4메뉴"},  # 이건 포함 안 될 수도 있음 (3개 제한)
            ]
        }
        result = build_query(restaurant)
        assert "삼겹살" in result
        assert "된장찌개" in result


# ─── retrieve_reviews — driver=None ──────────────────────────────────────────

class TestRetrieveReviewsNoneDriver:
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_driver_is_none(self):
        """driver=None 이면 빈 리스트를 반환하는지."""
        from services.recommendation.rag_reason.retriever import retrieve_reviews

        result = await retrieve_reviews({"_id": "r1"}, driver=None)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_restaurant_id(self):
        """restaurant_id가 없으면 빈 리스트를 반환하는지."""
        from services.recommendation.rag_reason.retriever import retrieve_reviews

        mock_driver = MagicMock()
        result = await retrieve_reviews({}, driver=mock_driver)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_empty_query(self):
        """build_query 결과가 빈 문자열이면 빈 리스트를 반환하는지."""
        from services.recommendation.rag_reason.retriever import retrieve_reviews

        mock_driver = MagicMock()
        # place_name, category_detail, menus 모두 없는 식당
        result = await retrieve_reviews({"_id": "r1"}, driver=mock_driver)
        assert result == []


# ─── retrieve_reviews — Neo4j 오류 처리 ──────────────────────────────────────

class TestRetrieveReviewsNeo4jError:
    @pytest.mark.asyncio
    async def test_returns_empty_list_on_neo4j_error(self):
        """Neo4j 오류 시 예외를 전파하지 않고 빈 리스트를 반환하는지."""
        from services.recommendation.rag_reason.retriever import retrieve_reviews

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(side_effect=Exception("Neo4j connection error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        restaurant = {
            "_id": "r1",
            "place_name": "테스트 식당",
            "category_detail": "한식",
        }

        with patch(
            "services.recommendation.rag_reason.retriever._get_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ):
            result = await retrieve_reviews(restaurant, driver=mock_driver)

        assert result == []

    @pytest.mark.asyncio
    async def test_no_exception_propagated(self):
        """Neo4j 오류가 호출자에게 전파되지 않는지."""
        from services.recommendation.rag_reason.retriever import retrieve_reviews

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(side_effect=Exception("Unexpected error"))

        restaurant = {
            "_id": "r1",
            "place_name": "테스트 식당",
        }

        with patch(
            "services.recommendation.rag_reason.retriever._get_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ):
            # 예외 없이 빈 리스트 반환되어야 함
            result = await retrieve_reviews(restaurant, driver=mock_driver)

        assert isinstance(result, list)


# ─── retrieve_reviews — 정상 동작 ─────────────────────────────────────────────

class TestRetrieveReviewsNormal:
    @pytest.mark.asyncio
    async def test_returned_items_have_page_content(self):
        """반환 값이 generator.py 호환 (page_content 속성)인지."""
        from services.recommendation.rag_reason.retriever import retrieve_reviews

        # Neo4j session 모킹
        mock_records = [
            {"rev.review_text": "맛있어요"},
            {"rev.review_text": "분위기 좋아요"},
        ]

        async def mock_aiter():
            for r in mock_records:
                yield r

        mock_result = MagicMock()
        mock_result.__aiter__ = lambda self: mock_aiter()

        mock_session = AsyncMock()
        mock_session.run = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_driver = MagicMock()
        mock_driver.session = MagicMock(return_value=mock_session)

        restaurant = {
            "_id": "r1",
            "place_name": "테스트 식당",
            "category_detail": "한식",
        }

        with patch(
            "services.recommendation.rag_reason.retriever._get_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ):
            result = await retrieve_reviews(restaurant, driver=mock_driver)

        assert len(result) == 2
        # generator.py가 doc.page_content를 접근하므로 page_content가 있어야 함
        for doc in result:
            assert hasattr(doc, "page_content")
            assert doc.page_content in ("맛있어요", "분위기 좋아요")


# ─── get_neo4j_driver ─────────────────────────────────────────────────────────

class TestGetNeo4jDriver:
    @pytest.mark.asyncio
    async def test_returns_none_on_connection_error(self):
        """Neo4j 연결 실패 시 None을 반환하는지 (예외 전파 안함)."""
        from services.recommendation.rag_reason.client import get_neo4j_driver

        with patch(
            "services.recommendation.rag_reason.client.Neo4jClient.get_driver",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            result = await get_neo4j_driver()

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_driver_on_success(self):
        """정상 연결 시 드라이버를 반환하는지."""
        from services.recommendation.rag_reason.client import get_neo4j_driver

        mock_driver = MagicMock()
        with patch(
            "services.recommendation.rag_reason.client.Neo4jClient.get_driver",
            new_callable=AsyncMock,
            return_value=mock_driver,
        ):
            result = await get_neo4j_driver()

        assert result is mock_driver
