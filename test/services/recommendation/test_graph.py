"""TDD: services/recommendation/graph.py 파이프라인 그래프 연결 테스트.

검증 항목:
- allergy_sg 노드가 그래프에 등록되어 있는지
- semantic_rerank 노드가 그래프에 등록되어 있는지
- recommend → allergy_sg → semantic_rerank → bridge 엣지 순서가 맞는지
- refresh → allergy_sg 엣지가 존재하는지
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
    def test_allergy_sg_node_registered(self):
        """allergy_sg 노드가 그래프에 등록되어 있는지."""
        nodes, _ = _get_graph_structure()
        assert "allergy_sg" in nodes

    def test_semantic_rerank_node_registered(self):
        """semantic_rerank 노드가 그래프에 등록되어 있는지."""
        nodes, _ = _get_graph_structure()
        assert "semantic_rerank" in nodes

    def test_existing_nodes_still_present(self):
        """기존 노드들이 유지되는지 (회귀 테스트)."""
        nodes, _ = _get_graph_structure()
        for node in ["recommend", "refresh", "bridge", "persona_factory",
                     "moderator_preselect", "restaurant_dialogue", "score_fallback"]:
            assert node in nodes, f"기존 노드 '{node}'가 사라짐"


class TestGraphEdges:
    def test_recommend_to_allergy_sg(self):
        """recommend → allergy_sg 엣지가 존재하는지."""
        _, edges = _get_graph_structure()
        assert ("recommend", "allergy_sg") in edges

    def test_refresh_to_allergy_sg(self):
        """refresh → allergy_sg 엣지가 존재하는지."""
        _, edges = _get_graph_structure()
        assert ("refresh", "allergy_sg") in edges

    def test_allergy_sg_to_semantic_rerank(self):
        """allergy_sg → semantic_rerank 엣지가 존재하는지 (에러 없을 때)."""
        _, edges = _get_graph_structure()
        assert ("allergy_sg", "semantic_rerank") in edges

    def test_semantic_rerank_to_bridge(self):
        """semantic_rerank → bridge 엣지가 존재하는지 (에러 없을 때)."""
        _, edges = _get_graph_structure()
        assert ("semantic_rerank", "bridge") in edges

    def test_recommend_does_not_go_directly_to_bridge(self):
        """recommend가 더 이상 bridge로 직접 연결되지 않는지."""
        _, edges = _get_graph_structure()
        assert ("recommend", "bridge") not in edges

    def test_refresh_does_not_go_directly_to_bridge(self):
        """refresh가 더 이상 bridge로 직접 연결되지 않는지."""
        _, edges = _get_graph_structure()
        assert ("refresh", "bridge") not in edges
