import logging
from typing import Any, Dict, List

from langfuse import observe

from services.agent_dialogue.app.engine.state import AgentDialogueState

logger = logging.getLogger(__name__)

_TARGET = 5


@observe(name="score_fallback")
def score_fallback(state: AgentDialogueState) -> dict:
    """모든 대화 완료 후 추천이 5개 미만이면 preselect score 순으로 채운다."""
    recommended: List[Dict[str, Any]] = list(state.get("recommended_restaurants", []))
    needed = _TARGET - len(recommended)

    if needed <= 0:
        return {}

    recommended_ids = {r["restaurant_id"] for r in recommended}
    processed: List[Dict[str, Any]] = state.get("processed_restaurants", [])

    candidates = sorted(
        [p for p in processed if p["restaurant_id"] not in recommended_ids],
        key=lambda x: (x.get("score", 0.0),),
        reverse=True,
    )

    added = []
    for r in candidates[:needed]:
        recommended.append({"restaurant_id": r["restaurant_id"], "place_name": r["place_name"]})
        added.append(r["place_name"])

    if added:
        logger.info(
            "[Fallback] score 기반 %d개 추가: %s",
            len(added),
            ", ".join(added),
        )

    return {"recommended_restaurants": recommended}
