from langgraph.graph import StateGraph, END
from src.recommendation.features.persona_manager.workflows.state import PersonaState
from src.recommendation.features.persona_manager.workflows.nodes import (
    generate_base_persona_node,
    save_persona_node,
)


def create_persona_workflow():
    """
    페르소나 생성 및 저장 워크플로우 그래프 생성
    """
    workflow = StateGraph(PersonaState)

    # 노드 추가
    workflow.add_node("generate_persona", generate_base_persona_node)
    workflow.add_node("save_persona", save_persona_node)

    # 엣지 연결 (순차 실행)
    workflow.set_entry_point("generate_persona")
    workflow.add_edge("generate_persona", "save_persona")
    workflow.add_edge("save_persona", END)

    return workflow.compile()


# 싱글톤처럼 사용하여 컴파일 비용 절약
persona_workflow = create_persona_workflow()
