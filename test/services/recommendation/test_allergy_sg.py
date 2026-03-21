"""TDD: services/recommendation/sub_graphs/allergy.py 단위 테스트."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── helpers ─────────────────────────────────────────────────────────────────

def make_user(uid: int, allergies: list[str]) -> dict:
    return {"id": uid, "allergies": allergies}


def make_restaurant(
    rid: str = "r1",
    menus: list[dict] | None = None,
    allergy_risk_map: dict | None = None,
) -> dict:
    return {
        "_id": rid,
        "place_name": f"식당_{rid}",
        "menus": menus or [],
        "allergy_risk_map": allergy_risk_map or {},
        "total_score": 0.8,
    }


# ─── _calculate_allergy_penalty ──────────────────────────────────────────────

class TestCalculateAllergyPenalty:
    """소프트 패널티 계산 테스트."""

    def test_returns_zero_when_no_users(self):
        """`user_datas`가 비어있으면 (0.0, [])을 반환하는지."""
        from services.recommendation.sub_graphs.allergy import _calculate_allergy_penalty

        penalty, hints = _calculate_allergy_penalty([], make_restaurant())
        assert penalty == 0.0
        assert hints == []

    def test_returns_zero_when_no_allergies(self):
        """유저에 알러지가 없으면 penalty=0.0을 반환하는지."""
        from services.recommendation.sub_graphs.allergy import _calculate_allergy_penalty

        users = [make_user(1, []), make_user(2, [])]
        penalty, hints = _calculate_allergy_penalty(users, make_restaurant())
        assert penalty == 0.0

    def test_applies_cap_of_0_3(self):
        """패널티가 0.3을 초과하지 않는지."""
        from services.recommendation.sub_graphs.allergy import _calculate_allergy_penalty

        # 모든 유저가 높은 위험 → penalty가 0.3 cap에 걸려야 함
        allergy_map = {"PORK": 1.0, "BEEF": 1.0}
        users = [
            make_user(1, ["PORK"]),
            make_user(2, ["PORK"]),
            make_user(3, ["PORK"]),
        ]
        restaurant = make_restaurant(allergy_risk_map=allergy_map)
        penalty, _ = _calculate_allergy_penalty(users, restaurant)

        assert penalty <= 0.3

    def test_uses_allergy_risk_map_when_available(self):
        """allergy_risk_map 값이 있으면 그 값을 사용하는지."""
        from services.recommendation.sub_graphs.allergy import _calculate_allergy_penalty

        allergy_map = {"PORK": 0.9}
        users = [make_user(1, ["PORK"])]
        restaurant = make_restaurant(allergy_risk_map=allergy_map, menus=[])

        penalty, hints = _calculate_allergy_penalty(users, restaurant)
        # PORK 위험도 0.9 → risky_users=1/1, avg_risk=0.9 → penalty=0.9 → cap 0.3
        assert penalty == pytest.approx(0.3)

    def test_returns_zero_when_risk_below_0_5(self):
        """위험도가 0.5 미만이면 penalty가 0.0인지."""
        from services.recommendation.sub_graphs.allergy import _calculate_allergy_penalty

        allergy_map = {"PORK": 0.4}
        users = [make_user(1, ["PORK"])]
        restaurant = make_restaurant(allergy_risk_map=allergy_map)

        penalty, _ = _calculate_allergy_penalty(users, restaurant)
        assert penalty == 0.0

    def test_hints_generated_when_high_risk(self):
        """위험도 0.5 이상이면 hints 리스트에 항목이 생성되는지."""
        from services.recommendation.sub_graphs.allergy import _calculate_allergy_penalty

        allergy_map = {"PORK": 0.8}
        users = [make_user(1, ["PORK"])]
        restaurant = make_restaurant(allergy_risk_map=allergy_map)

        _, hints = _calculate_allergy_penalty(users, restaurant)
        assert len(hints) > 0
        assert any("PORK" in h for h in hints)

    def test_no_hints_when_low_risk(self):
        """위험도 0.5 미만이면 hints가 비어있는지."""
        from services.recommendation.sub_graphs.allergy import _calculate_allergy_penalty

        allergy_map = {"PORK": 0.3}
        users = [make_user(1, ["PORK"])]
        restaurant = make_restaurant(allergy_risk_map=allergy_map)

        _, hints = _calculate_allergy_penalty(users, restaurant)
        assert hints == []


# ─── _is_hard_exclude ────────────────────────────────────────────────────────

class TestIsHardExclude:
    """하드 제외 조건 테스트."""

    def test_returns_false_when_no_menus(self):
        """메뉴가 없으면 False를 반환하는지."""
        from services.recommendation.sub_graphs.allergy import _is_hard_exclude

        users = [make_user(1, ["PORK"])]
        restaurant = make_restaurant(menus=[])
        assert _is_hard_exclude(users, restaurant) is False

    def test_returns_false_when_no_users(self):
        """유저가 없으면 False를 반환하는지."""
        from services.recommendation.sub_graphs.allergy import _is_hard_exclude

        menus = [{"title": "삼겹살"}, {"title": "제육볶음"}, {"title": "돼지국밥"}]
        restaurant = make_restaurant(menus=menus)
        assert _is_hard_exclude([], restaurant) is False

    def test_returns_true_when_majority_high_risk(self):
        """유저 50% 이상이 상위 메뉴 80% 이상 매칭 시 True인지."""
        from services.recommendation.sub_graphs.allergy import _is_hard_exclude

        # 상위 3개 메뉴 모두 돼지고기 계열
        menus = [
            {"title": "삼겹살"},
            {"title": "제육볶음"},
            {"title": "돼지국밥"},
        ]
        users = [
            make_user(1, ["PORK"]),
            make_user(2, ["PORK"]),
        ]
        restaurant = make_restaurant(menus=menus)
        assert _is_hard_exclude(users, restaurant) is True

    def test_returns_false_when_minority_risky(self):
        """위험 유저가 50% 미만이면 False인지."""
        from services.recommendation.sub_graphs.allergy import _is_hard_exclude

        menus = [
            {"title": "삼겹살"},
            {"title": "제육볶음"},
            {"title": "돼지국밥"},
        ]
        users = [
            make_user(1, ["PORK"]),   # 위험
            make_user(2, []),          # 안전
            make_user(3, []),          # 안전
            make_user(4, []),          # 안전
        ]
        restaurant = make_restaurant(menus=menus)
        assert _is_hard_exclude(users, restaurant) is False


# ─── allergy_node ─────────────────────────────────────────────────────────────

class TestAllergyNode:
    """allergy_node 통합 테스트 (DB 모킹)."""

    def _make_state(
        self,
        user_ids: list[int] | None = None,
        restaurants: list[dict] | None = None,
    ) -> dict:
        return {
            "user_ids": user_ids or [1, 2],
            "filtered_restaurant": restaurants or [make_restaurant()],
            "status_message": [],
            "dining_data": {},
            "dining_id": "d1",
        }

    @pytest.mark.asyncio
    async def test_returns_filtered_restaurant_in_state(self):
        """allergy_node가 filtered_restaurant를 state에 포함하여 반환하는지."""
        from services.recommendation.sub_graphs.allergy import allergy_node

        state = self._make_state(
            user_ids=[1],
            restaurants=[make_restaurant("r1")],
        )

        mock_user = make_user(1, [])

        with patch(
            "services.recommendation.sub_graphs.allergy.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(return_value=mock_user)
            MockDB.return_value = mock_db

            result = await allergy_node(state)

        assert isinstance(result, dict)
        assert "filtered_restaurant" in result

    @pytest.mark.asyncio
    async def test_penalty_zero_for_users_with_no_allergies(self):
        """알러지 없는 유저들만 있으면 모든 식당의 allergy_penalty가 0.0인지."""
        from services.recommendation.sub_graphs.allergy import allergy_node

        state = self._make_state(
            user_ids=[1, 2],
            restaurants=[make_restaurant("r1"), make_restaurant("r2")],
        )

        mock_users = {1: make_user(1, []), 2: make_user(2, [])}

        async def mock_read_one(query):
            for uid, user in mock_users.items():
                if uid in query.get("id", {}).get("$in", []):
                    return user
            return None

        with patch(
            "services.recommendation.sub_graphs.allergy.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(side_effect=mock_read_one)
            MockDB.return_value = mock_db

            result = await allergy_node(state)

        for r in result.get("filtered_restaurant", []):
            assert r.get("allergy_penalty", 0.0) == 0.0

    @pytest.mark.asyncio
    async def test_allergy_hints_attached_to_restaurant(self):
        """고위험 알러지가 있으면 allergy_hints가 식당에 첨부되는지."""
        from services.recommendation.sub_graphs.allergy import allergy_node

        allergy_map = {"PORK": 0.9}
        restaurant = make_restaurant("r1", allergy_risk_map=allergy_map)
        state = self._make_state(user_ids=[1], restaurants=[restaurant])

        mock_user = make_user(1, ["PORK"])

        with patch(
            "services.recommendation.sub_graphs.allergy.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(return_value=mock_user)
            MockDB.return_value = mock_db

            result = await allergy_node(state)

        restaurants = result.get("filtered_restaurant", [])
        assert len(restaurants) > 0
        assert "allergy_hints" in restaurants[0]

    @pytest.mark.asyncio
    async def test_hard_excluded_restaurant_removed(self):
        """하드 제외 조건 충족 식당은 filtered_restaurant에서 제거되는지."""
        from services.recommendation.sub_graphs.allergy import allergy_node

        # 상위 3개 메뉴 모두 돼지고기, 유저 2명 모두 PORK 알러지
        menus = [
            {"title": "삼겹살"},
            {"title": "제육볶음"},
            {"title": "돼지국밥"},
        ]
        restaurant = make_restaurant("r1", menus=menus)
        state = self._make_state(
            user_ids=[1, 2],
            restaurants=[restaurant],
        )

        mock_users = {1: make_user(1, ["PORK"]), 2: make_user(2, ["PORK"])}

        async def mock_read_one(query):
            for uid, user in mock_users.items():
                if uid in query.get("id", {}).get("$in", []):
                    return user
            return None

        with patch(
            "services.recommendation.sub_graphs.allergy.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(side_effect=mock_read_one)
            MockDB.return_value = mock_db

            result = await allergy_node(state)

        assert len(result.get("filtered_restaurant", [])) == 0

    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self):
        """정상 완료 시 dict를 반환하는지."""
        from services.recommendation.sub_graphs.allergy import allergy_node

        state = self._make_state()

        with patch(
            "services.recommendation.sub_graphs.allergy.DBManager"
        ) as MockDB:
            mock_db = MagicMock()
            mock_db.read_one = AsyncMock(return_value=make_user(1, []))
            MockDB.return_value = mock_db

            result = await allergy_node(state)

        assert isinstance(result, dict)
        assert "filtered_restaurant" in result


# ─── get_allergy_graph ────────────────────────────────────────────────────────

class TestGetAllergyGraph:
    """서브그래프 팩토리 테스트."""

    def test_returns_compiled_graph(self):
        """get_allergy_graph()가 컴파일된 그래프를 반환하는지."""
        from services.recommendation.sub_graphs.allergy import get_allergy_graph

        graph = get_allergy_graph()
        assert graph is not None

    def test_graph_is_callable(self):
        """반환된 그래프가 호출 가능한지."""
        from services.recommendation.sub_graphs.allergy import get_allergy_graph

        graph = get_allergy_graph()
        assert callable(graph.invoke) or hasattr(graph, "ainvoke")
