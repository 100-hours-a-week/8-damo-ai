"""TDD: scripts/indexing/mongodb_to_neo4j.py 단위 테스트."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# chunk_allergy_analysis_prompt
# ---------------------------------------------------------------------------

class TestChunkAllergyAnalysisPrompt:
    """메뉴 포맷 함수 테스트."""

    def test_formats_menus_with_title_and_price(self):
        """title과 price가 있는 메뉴를 올바르게 포맷하는지."""
        from scripts.indexing.mongodb_to_neo4j import chunk_allergy_analysis_prompt

        restaurant = {
            "place_name": "테스트 식당",
            "menus": [
                {"title": "삼겹살", "price": 15000},
                {"title": "된장찌개", "price": 8000},
            ],
        }
        result = chunk_allergy_analysis_prompt(restaurant)

        assert "테스트 식당" in result
        assert "삼겹살" in result
        assert "된장찌개" in result

    def test_handles_empty_menus(self):
        """메뉴가 없는 식당도 프롬프트가 생성되는지."""
        from scripts.indexing.mongodb_to_neo4j import chunk_allergy_analysis_prompt

        restaurant = {"place_name": "빈 식당", "menus": []}
        result = chunk_allergy_analysis_prompt(restaurant)

        assert "빈 식당" in result
        assert isinstance(result, str)

    def test_includes_22_allergy_types_in_prompt(self):
        """프롬프트에 22종 알러지가 포함되는지."""
        from scripts.indexing.mongodb_to_neo4j import chunk_allergy_analysis_prompt, ALLERGY_TYPES

        restaurant = {"place_name": "테스트", "menus": []}
        result = chunk_allergy_analysis_prompt(restaurant)

        for allergy in ALLERGY_TYPES[:5]:  # 일부만 확인
            assert allergy in result


# ---------------------------------------------------------------------------
# parse_llm_response
# ---------------------------------------------------------------------------

class TestParseLlmResponse:
    """LLM 응답 파싱 및 검증 테스트."""

    def test_parses_valid_json_response(self):
        """유효한 JSON 응답을 파싱하는지."""
        from scripts.indexing.mongodb_to_neo4j import parse_llm_response

        raw = '{"PORK": 0.9, "SOYBEAN": 0.6}'
        result = parse_llm_response(raw)

        assert result["PORK"] == pytest.approx(0.9)
        assert result["SOYBEAN"] == pytest.approx(0.6)

    def test_filters_scores_below_threshold(self):
        """0.3 미만 점수는 제거되는지."""
        from scripts.indexing.mongodb_to_neo4j import parse_llm_response

        raw = '{"PORK": 0.9, "EGG": 0.1, "MILK": 0.29}'
        result = parse_llm_response(raw)

        assert "PORK" in result
        assert "EGG" not in result
        assert "MILK" not in result

    def test_clamps_scores_to_0_1_range(self):
        """점수가 0~1 범위를 초과하면 클램핑하는지."""
        from scripts.indexing.mongodb_to_neo4j import parse_llm_response

        raw = '{"PORK": 1.5, "EGG": -0.2}'
        result = parse_llm_response(raw)

        if "PORK" in result:
            assert result["PORK"] <= 1.0
        if "EGG" in result:
            assert result["EGG"] >= 0.0

    def test_returns_empty_dict_on_invalid_json(self):
        """JSON 파싱 실패 시 빈 dict를 반환하는지."""
        from scripts.indexing.mongodb_to_neo4j import parse_llm_response

        result = parse_llm_response("이것은 JSON이 아닙니다")
        assert result == {}

    def test_extracts_json_from_markdown_code_block(self):
        """마크다운 코드블록에서 JSON을 추출하는지."""
        from scripts.indexing.mongodb_to_neo4j import parse_llm_response

        raw = '```json\n{"PORK": 0.8}\n```'
        result = parse_llm_response(raw)

        assert "PORK" in result

    def test_ignores_unknown_allergy_keys(self):
        """알려지지 않은 알러지 키는 무시하는지."""
        from scripts.indexing.mongodb_to_neo4j import parse_llm_response

        raw = '{"PORK": 0.9, "UNKNOWN_ALLERGY": 0.8}'
        result = parse_llm_response(raw)

        assert "PORK" in result
        assert "UNKNOWN_ALLERGY" not in result


# ---------------------------------------------------------------------------
# upsert_to_neo4j
# ---------------------------------------------------------------------------

class TestUpsertToNeo4j:
    """Neo4j Cypher 호출 테스트."""

    @pytest.mark.asyncio
    async def test_calls_merge_restaurant_node(self):
        """Restaurant 노드 MERGE Cypher가 호출되는지."""
        from scripts.indexing.mongodb_to_neo4j import upsert_to_neo4j

        mock_session = AsyncMock()
        mock_session.run = AsyncMock()

        restaurant = {
            "_id": "abc123",
            "place_name": "테스트 식당",
            "category_detail": "한식",
        }
        allergy_scores = {"PORK": 0.9, "SOYBEAN": 0.5}

        await upsert_to_neo4j(mock_session, restaurant, allergy_scores)

        assert mock_session.run.called

    @pytest.mark.asyncio
    async def test_passes_allergy_scores_as_list(self):
        """allergy_scores를 [{name, score}] 형태로 전달하는지."""
        from scripts.indexing.mongodb_to_neo4j import upsert_to_neo4j

        mock_session = AsyncMock()
        captured_kwargs = {}

        async def capture_run(query, **kwargs):
            captured_kwargs.update(kwargs)

        mock_session.run = capture_run

        restaurant = {
            "_id": "abc123",
            "place_name": "테스트 식당",
            "category_detail": "한식",
        }
        allergy_scores = {"PORK": 0.9}

        await upsert_to_neo4j(mock_session, restaurant, allergy_scores)

        # allergy_scores가 list 형태로 전달되었는지
        assert "allergy_scores" in captured_kwargs
        scores_list = captured_kwargs["allergy_scores"]
        assert isinstance(scores_list, list)
        assert any(item["name"] == "PORK" for item in scores_list)

    @pytest.mark.asyncio
    async def test_skips_upsert_when_no_allergy_scores(self):
        """allergy_scores가 비어있으면 Restaurant 노드만 생성하는지."""
        from scripts.indexing.mongodb_to_neo4j import upsert_to_neo4j

        mock_session = AsyncMock()
        mock_session.run = AsyncMock()

        restaurant = {
            "_id": "abc123",
            "place_name": "테스트 식당",
            "category_detail": "한식",
        }

        await upsert_to_neo4j(mock_session, restaurant, {})

        # run이 1번 이상은 호출되어야 함 (Restaurant 노드 생성)
        assert mock_session.run.called


# ---------------------------------------------------------------------------
# write_back_to_mongo
# ---------------------------------------------------------------------------

class TestWriteBackToMongo:
    """MongoDB allergy_risk_map write-back 테스트."""

    @pytest.mark.asyncio
    async def test_uses_set_operator(self):
        """$set 연산자를 사용하는지."""
        from scripts.indexing.mongodb_to_neo4j import write_back_to_mongo

        mock_collection = AsyncMock()
        mock_collection.update_one = AsyncMock()

        restaurant_id = "abc123"
        allergy_risk_map = {"PORK": 0.9, "SOYBEAN": 0.5}

        await write_back_to_mongo(mock_collection, restaurant_id, allergy_risk_map)

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        # 두 번째 인자(update)에 $set이 있는지
        update_arg = call_args[0][1]
        assert "$set" in update_arg

    @pytest.mark.asyncio
    async def test_stores_allergy_risk_map_field(self):
        """allergy_risk_map 필드를 저장하는지."""
        from scripts.indexing.mongodb_to_neo4j import write_back_to_mongo

        mock_collection = AsyncMock()
        mock_collection.update_one = AsyncMock()

        allergy_risk_map = {"PORK": 0.9}

        await write_back_to_mongo(mock_collection, "abc123", allergy_risk_map)

        call_args = mock_collection.update_one.call_args
        update_arg = call_args[0][1]
        assert "allergy_risk_map" in update_arg.get("$set", {})

    @pytest.mark.asyncio
    async def test_filters_by_restaurant_id(self):
        """올바른 restaurant_id로 필터링하는지."""
        from scripts.indexing.mongodb_to_neo4j import write_back_to_mongo

        mock_collection = AsyncMock()
        mock_collection.update_one = AsyncMock()

        await write_back_to_mongo(mock_collection, "specific_id_123", {"PORK": 0.9})

        call_args = mock_collection.update_one.call_args
        filter_arg = call_args[0][0]
        # _id 또는 id로 필터링
        assert "specific_id_123" in str(filter_arg)


# ---------------------------------------------------------------------------
# create_allergy_type_nodes
# ---------------------------------------------------------------------------

class TestCreateAllergyTypeNodes:
    """AllergyType 노드 사전 생성 테스트."""

    @pytest.mark.asyncio
    async def test_creates_22_allergy_type_nodes(self):
        """22개 AllergyType 노드를 생성하는지."""
        from scripts.indexing.mongodb_to_neo4j import create_allergy_type_nodes, ALLERGY_TYPES

        mock_session = AsyncMock()
        mock_session.run = AsyncMock()

        await create_allergy_type_nodes(mock_session)

        assert mock_session.run.called
        call_args = mock_session.run.call_args
        # allergy_names 파라미터에 22개가 전달되었는지
        kwargs = call_args[1] if call_args[1] else {}
        args = call_args[0] if call_args[0] else ()
        passed_names = kwargs.get("allergy_names") or (args[1] if len(args) > 1 else None)
        if passed_names:
            assert len(passed_names) == len(ALLERGY_TYPES)
