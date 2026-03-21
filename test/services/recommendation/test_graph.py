"""TDD: services/recommendation/graph.py 파이프라인 그래프 연결 테스트.

검증 항목:
- 주요 노드들이 그래프에 등록되어 있는지
- score_by_budget → filter_meal_category → apply_allergy_penalty 순서가 맞는지
- apply_allergy_penalty → rerank_by_semantic_score 엣지가 존재하는지
- load_remaining_candidates → apply_allergy_penalty 엣지가 존재하는지
"""
import pytest


def _get_graph_structure():
    """컴파일된 그래프를 빌드하고 (nodes, edges) 반환."""
    from services.recommendation.graph import build_pipeline_graph

    compiled = build_pipeline_graph()
    raw = compiled.get_graph()
    node_keys = set(raw.nodes.keys())
    edge_pairs = {(e.source, e.target) for e in raw.edges}
    return node_keys, edge_pairs


class TestGraphNodes:
    def test_filter_meal_category_node_registered(self):
        """filter_meal_category 노드가 그래프에 등록되어 있는지."""
        nodes, _ = _get_graph_structure()
        assert "filter_meal_category" in nodes

    def test_apply_allergy_penalty_node_registered(self):
        """apply_allergy_penalty 노드가 그래프에 등록되어 있는지."""
        nodes, _ = _get_graph_structure()
        assert "apply_allergy_penalty" in nodes

    def test_rerank_by_semantic_score_node_registered(self):
        """rerank_by_semantic_score 노드가 그래프에 등록되어 있는지."""
        nodes, _ = _get_graph_structure()
        assert "rerank_by_semantic_score" in nodes

    def test_existing_nodes_still_present(self):
        """기존 노드들이 유지되는지 (회귀 테스트)."""
        nodes, _ = _get_graph_structure()
        expected = [
            "fetch_nearby_restaurants",
            "score_by_budget",
            "filter_meal_category",
            "apply_allergy_penalty",
            "rerank_by_semantic_score",
            "initialize_dialogue_state",
            "create_group_personas",
            "select_candidate_batch",
            "run_persona_discussion",
            "apply_dialogue_fallback",
            "persist_voting_records",
            "persist_dialogue_history",
            "generate_recommendation_reasons",
            "validate_user_group",
            "load_remaining_candidates",
            "rescue_from_error",
        ]
        for node in expected:
            assert node in nodes, f"노드 '{node}'가 그래프에 없음"


class TestGraphEdges:
    def test_score_by_budget_to_filter_meal_category(self):
        """score_by_budget → filter_meal_category 엣지가 존재하는지."""
        _, edges = _get_graph_structure()
        assert ("score_by_budget", "filter_meal_category") in edges

    def test_filter_meal_category_to_apply_allergy_penalty(self):
        """filter_meal_category → apply_allergy_penalty 엣지가 존재하는지."""
        _, edges = _get_graph_structure()
        assert ("filter_meal_category", "apply_allergy_penalty") in edges

    def test_score_by_budget_does_not_go_directly_to_allergy(self):
        """score_by_budget이 더 이상 apply_allergy_penalty로 직접 연결되지 않는지."""
        _, edges = _get_graph_structure()
        assert ("score_by_budget", "apply_allergy_penalty") not in edges

    def test_apply_allergy_penalty_to_rerank(self):
        """apply_allergy_penalty → rerank_by_semantic_score 엣지가 존재하는지 (에러 없을 때)."""
        _, edges = _get_graph_structure()
        assert ("apply_allergy_penalty", "rerank_by_semantic_score") in edges

    def test_rerank_to_initialize_dialogue_state(self):
        """rerank_by_semantic_score → initialize_dialogue_state 엣지가 존재하는지."""
        _, edges = _get_graph_structure()
        assert ("rerank_by_semantic_score", "initialize_dialogue_state") in edges

    def test_load_remaining_to_allergy(self):
        """load_remaining_candidates → apply_allergy_penalty 엣지가 존재하는지."""
        _, edges = _get_graph_structure()
        assert ("load_remaining_candidates", "apply_allergy_penalty") in edges
