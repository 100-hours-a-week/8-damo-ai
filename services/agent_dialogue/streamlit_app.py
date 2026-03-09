"""agent_dialogue Streamlit 데모 앱.

식당을 1개씩 발표하고 분석가 → 페르소나 반응 → 투표하는 과정을 시각적으로 확인.
- 유저: 하드코딩 테스트 유저 4명 (DB 조회 X)
- 식당: 실제 MongoDB restaurants 컬렉션에서 $sample으로 랜덤 fetch
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import streamlit as st

st.set_page_config(page_title="agent_dialogue 데모", page_icon="🍽️", layout="wide")

# sys.path 설정 (프로젝트 루트)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import os  # noqa: E402

try:
    from shared.utils.config import settings  # noqa: E402
except Exception as e:
    st.error(f"설정 로드 실패 (.env 파일 확인): {e}")
    st.stop()

os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# 하드코딩 테스트 유저 4명
# ---------------------------------------------------------------------------
SAMPLE_USERS: list[dict[str, Any]] = [
    {
        "id": 1,
        "nickname": "철수",
        "gender": "남성",
        "age_group": "20대",
        "allergies": ["땅콩"],
        "like_food_categories_id": ["한식", "일식"],
        "basePersona": "20대 직장인 남성. 매운 음식을 좋아하고 회식 분위기를 중시함.",
    },
    {
        "id": 2,
        "nickname": "영희",
        "gender": "여성",
        "age_group": "30대",
        "allergies": [],
        "like_food_categories_id": ["일식", "양식"],
        "basePersona": "30대 여성 직장인. 디저트와 분위기 좋은 레스토랑을 선호함.",
    },
    {
        "id": 3,
        "nickname": "민수",
        "gender": "남성",
        "age_group": "20대",
        "allergies": ["갑각류"],
        "like_food_categories_id": ["한식"],
        "basePersona": "20대 남성. 가성비를 중시하고 고기류를 좋아함.",
    },
    {
        "id": 4,
        "nickname": "지은",
        "gender": "여성",
        "age_group": "30대",
        "allergies": ["우유"],
        "like_food_categories_id": ["양식", "한식"],
        "basePersona": "30대 여성. 분위기 좋은 곳을 선호하며 채식 메뉴에 관심 있음.",
    },
]

_USER_AVATARS: list[str] = ["🧑‍🍳", "👩‍💼", "🧑‍💻", "👩‍🎨"]


def _get_avatar(user_id: str) -> str:
    try:
        idx = int(user_id) - 1
    except (ValueError, TypeError):
        idx = 0
    return _USER_AVATARS[idx % len(_USER_AVATARS)]


# ---------------------------------------------------------------------------
# 비동기 파이프라인
# ---------------------------------------------------------------------------
from shared.database.db_manager import DBManager  # noqa: E402
from langfuse import Langfuse  # noqa: E402

import services.agent_dialogue.app.utils.monitoring  # noqa: F401 — Langfuse 환경변수 주입

from services.agent_dialogue.app.engine.graph import build_agent_dialogue_graph  # noqa: E402
from services.agent_dialogue.app.engine.state import create_initial_state  # noqa: E402


async def _fetch_random_restaurants(n: int) -> list[dict[str, Any]]:
    """MongoDB restaurants 컬렉션에서 $sample으로 N개 랜덤 fetch."""
    db = DBManager(col_name="restaurants")
    try:
        pipeline = [{"$sample": {"size": n}}]
        cursor = db.collection.aggregate(pipeline)
        docs = await cursor.to_list(length=None)
        for doc in docs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
        return docs
    finally:
        db.client.close()


async def _run_pipeline(
    container: st.delta_generator.DeltaGenerator,
    selected_users: list[dict[str, Any]],
    restaurant_count: int,
    dining_data: dict[str, Any],
) -> dict[str, Any]:
    """graph.astream()으로 노드별 실시간 렌더링."""
    # 1) 식당 랜덤 fetch
    container.write("🔍 식당 데이터 조회 중...")
    restaurants = await _fetch_random_restaurants(restaurant_count)
    if not restaurants:
        return {"is_error": True, "error_message": "MongoDB에서 식당을 가져올 수 없습니다."}

    restaurant_ids = [r["_id"] for r in restaurants]
    user_ids = [u["id"] for u in selected_users]

    # 2) persona_factory의 DBManager만 mock
    user_map = {u["id"]: u for u in selected_users}

    async def _mock_read_one(query: dict[str, Any]) -> dict[str, Any] | None:
        return user_map.get(query.get("id"))

    with patch(
        "services.agent_dialogue.app.nodes.persona_factory.DBManager"
    ) as mock_cls:
        mock_inst = MagicMock()
        mock_cls.return_value = mock_inst
        mock_inst.read_one = AsyncMock(side_effect=_mock_read_one)

        initial_state = create_initial_state(
            user_ids=user_ids,
            dining_data=dining_data,
            filtered_restaurant_ids=restaurant_ids,
        )

        graph = build_agent_dialogue_graph()
        config: dict[str, Any] = {}

        final_state = dict(initial_state)
        shown_history_len = 0  # 이미 렌더링한 dialogue_history 인덱스

        async for update in graph.astream(
            initial_state, config=config, stream_mode="updates"
        ):
            for node_name, node_output in update.items():
                final_state.update(node_output)

                if node_name == "persona_factory":
                    n_personas = len(node_output.get("persona_prompts", {}))
                    container.success(f"✅ 페르소나 {n_personas}명 생성 완료")

                elif node_name == "moderator_preselect":
                    pool = node_output.get("candidate_pool", [])
                    offset = node_output.get("restaurant_offset", 0)
                    batch_num = offset // 5
                    container.info(f"📋 배치 {batch_num}: 식당 {len(pool)}개 선별")
                    rows = [
                        {
                            "순위": i,
                            "식당명": c.get("place_name", ""),
                            "카테고리": c.get("category_detail", ""),
                            "점수": round(c.get("score", 0), 2),
                        }
                        for i, c in enumerate(pool, 1)
                    ]
                    container.dataframe(rows, hide_index=True)

                elif node_name == "restaurant_dialogue":
                    history = final_state.get("dialogue_history", [])
                    new_entries = history[shown_history_len:]
                    shown_history_len = len(history)

                    # 현재 식당 이름 (첫 번째 analyst 엔트리에서)
                    current_place = next(
                        (e["place_name"] for e in new_entries if e["type"] == "analyst"),
                        "?",
                    )
                    container.markdown(f"---\n#### 🍽️ {current_place}")

                    for entry in new_entries:
                        etype = entry["type"]

                        if etype == "analyst":
                            container.info(f"🔍 **분석가**: {entry['content']}")

                        elif etype == "reaction":
                            uid = str(entry.get("user_id", ""))
                            nickname = entry.get("nickname", "?")
                            avatar = _get_avatar(uid)
                            with container.chat_message(name=nickname, avatar=avatar):
                                st.markdown(entry["content"])

                        elif etype == "vote":
                            uid = str(entry.get("user_id", ""))
                            nickname = entry.get("nickname", "?")
                            avatar = _get_avatar(uid)
                            approve = entry.get("approve", False)
                            reasoning = entry.get("reasoning", "")
                            icon = "✅" if approve else "❌"
                            msg = f"{icon} **{avatar} {nickname}**: {reasoning}"
                            if approve:
                                container.success(msg)
                            else:
                                container.warning(msg)

                    # 이 식당의 투표 결과 요약
                    votes = [e for e in new_entries if e["type"] == "vote"]
                    if votes:
                        approve_count = sum(1 for v in votes if v["approve"])
                        total = len(votes)
                        is_approved = total > 0 and approve_count > total / 2
                        result_msg = (
                            f"🎉 **{current_place}** 추천 확정! ({approve_count}/{total} 찬성)"
                            if is_approved
                            else f"💔 **{current_place}** 미추천 ({approve_count}/{total} 찬성)"
                        )
                        if is_approved:
                            container.success(result_msg)
                        else:
                            container.error(result_msg)

    # 최종 결과
    recommended = final_state.get("recommended_restaurants", [])
    processed = final_state.get("processed_restaurants", [])

    container.markdown("---")
    container.markdown("## 🏆 최종 추천 결과")

    if len(recommended) < 5 and processed:
        container.caption("(5개 미만 — 찬성수 기준 보충)")
        already_ids = {r["restaurant_id"] for r in recommended}
        extras = sorted(
            [r for r in processed if r["restaurant_id"] not in already_ids],
            key=lambda r: (r["approve_count"], r["score"]),
            reverse=True,
        )
        recommended = recommended + extras[: 5 - len(recommended)]

    if recommended:
        rows = [
            {
                "순위": i,
                "식당명": r.get("place_name", ""),
                "비고": "과반수 통과" if i <= len(final_state.get("recommended_restaurants", [])) else "보충",
            }
            for i, r in enumerate(recommended[:5], 1)
        ]
        container.dataframe(rows, hide_index=True)
    else:
        container.warning("추천 식당이 없습니다.")

    Langfuse().flush()
    final_state["_restaurants"] = restaurants
    return final_state


# ---------------------------------------------------------------------------
# 사이드바
# ---------------------------------------------------------------------------
def _sidebar() -> tuple[list[dict[str, Any]], int, dict[str, Any], bool]:
    with st.sidebar:
        st.header("설정")

        st.subheader("참여 유저")
        selected_users: list[dict[str, Any]] = []
        for user in SAMPLE_USERS:
            avatar = _get_avatar(str(user["id"]))
            label = f"{avatar} {user['nickname']} ({user['age_group']}, {user['gender']})"
            if st.checkbox(label, value=True, key=f"user_{user['id']}"):
                selected_users.append(user)

        if len(selected_users) < 2:
            st.warning("최소 2명 이상 선택해야 합니다.")

        st.divider()

        st.subheader("식당 후보 수")
        n_restaurants: int = st.slider(
            "$sample 크기",
            min_value=5,
            max_value=50,
            value=10,
            help="MongoDB에서 랜덤으로 가져올 식당 수. 배치(5개)씩 처리됩니다.",
        )

        st.divider()

        st.subheader("회식 정보")
        dining_id: str = st.text_input("Dining ID", value="demo-001")
        col_lng, col_lat = st.columns(2)
        with col_lng:
            longitude: float = st.number_input("경도", value=127.0276, format="%.4f")
        with col_lat:
            latitude: float = st.number_input("위도", value=37.4979, format="%.4f")
        budget: int = st.number_input("1인당 예산 (원)", value=30000, step=5000)

        dining_data: dict[str, Any] = {
            "diningId": dining_id,
            "x": longitude,
            "y": latitude,
            "budget": budget,
        }

        st.divider()

        run_clicked: bool = st.button(
            "agent_dialogue 실행",
            type="primary",
            disabled=len(selected_users) < 2,
        )

        st.divider()
        st.subheader("연결 상태")
        st.caption(f"DB: `{settings.DB_NAME}`")
        if settings.LOCAL_MODEL:
            st.caption(f"페르소나 Model: `{settings.LOCAL_MODEL}`")
            st.caption(f"분석가 Model: `{settings.OPENAI_MODEL}`")
        else:
            st.caption(f"Model: `{settings.OPENAI_MODEL}`")
        st.caption(f"Langfuse: `{'연결됨' if settings.LANGFUSE_PUBLIC_KEY else '비활성'}`")

        st.warning("실행 시 API 호출이 발생합니다.", icon="⚠️")

    return selected_users, n_restaurants, dining_data, run_clicked


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main() -> None:
    st.title("🍽️ agent_dialogue 데모")
    st.caption("식당을 1개씩 분석하고 페르소나들이 투표하여 추천 목록을 만듭니다.")

    selected_users, n_restaurants, dining_data, run_clicked = _sidebar()

    if run_clicked and len(selected_users) >= 2:
        live = st.container()
        live.info(
            f"🚀 {len(selected_users)}명의 유저로 agent_dialogue 실행 중... "
            f"(식당 {n_restaurants}개, 배치 5개씩)"
        )
        try:
            result = asyncio.run(
                _run_pipeline(live, selected_users, n_restaurants, dining_data)
            )
        except Exception as e:
            st.error(f"실행 중 오류: {e}")
            result = None

        if result and result.get("is_error"):
            st.error(f"에러: {result.get('error_message', '알 수 없는 오류')}")
        elif result:
            st.session_state["result"] = result

    result = st.session_state.get("result")
    if result:
        with st.expander("Raw 데이터 (디버그)", expanded=False):
            display = {
                k: f"[{len(v)}개]" if isinstance(v, list) else v
                for k, v in result.items()
                if k != "_restaurants"
            }
            st.json(display)
    elif not run_clicked:
        st.info("왼쪽 사이드바에서 유저를 선택하고 'agent_dialogue 실행' 버튼을 눌러주세요.")


main()
