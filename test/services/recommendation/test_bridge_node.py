"""bridge_node 단위 테스트."""
import pytest

from services.recommendation.bridge_node import bridge_node


def _make_restaurant(oid: str, name: str) -> dict:
    return {"_id": oid, "place_name": name}


class TestBridgeNode:
    def test_extracts_ids_from_filtered_restaurant(self):
        state = {
            "filtered_restaurant": [
                _make_restaurant("aaa111", "식당A"),
                _make_restaurant("bbb222", "식당B"),
            ]
        }
        result = bridge_node(state)

        assert result["filtered_restaurant_ids"] == ["aaa111", "bbb222"]

    def test_skips_restaurants_without_id(self):
        state = {
            "filtered_restaurant": [
                _make_restaurant("aaa111", "식당A"),
                {"place_name": "ID없는식당"},  # _id 없음
            ]
        }
        result = bridge_node(state)

        assert result["filtered_restaurant_ids"] == ["aaa111"]

    def test_empty_filtered_restaurant(self):
        state = {"filtered_restaurant": []}
        result = bridge_node(state)

        assert result["filtered_restaurant_ids"] == []

    def test_initializes_agent_dialogue_fields(self):
        state = {"filtered_restaurant": []}
        result = bridge_node(state)

        assert result["user_data_list"] == []
        assert result["persona_prompts"] == {}
        assert result["candidate_pool"] == []
        assert result["restaurant_offset"] == 0
        assert result["restaurant_index"] == 0
        assert result["recommended_restaurants"] == []
        assert result["processed_restaurants"] == []
        assert result["persona_votes"] == []
        assert result["dialogue_history"] == []
        assert result["is_error"] is False
        assert result["error_message"] is None

    def test_missing_filtered_restaurant_key(self):
        """filtered_restaurant 키가 없어도 안전하게 동작."""
        result = bridge_node({})

        assert result["filtered_restaurant_ids"] == []
