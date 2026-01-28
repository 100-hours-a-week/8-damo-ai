import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.recommendation.features.persona_manager.workflows.nodes import (
    generate_base_persona_node,
    save_persona_node,
)
from src.recommendation.features.persona_manager.workflows.state import PersonaState
from src.recommendation.schemas.update_persona_db_request import UpdatePersonaDBRequest
from src.recommendation.schemas.user_data import UserData
from src.recommendation.enums import Gender, AgeGroup, AllergyType


@pytest.fixture
def mock_request_data():
    user = UserData(
        id=1,
        nickname="test_user",
        gender=Gender.MALE,
        age_group=AgeGroup.TWENTIES,
        allergies=[AllergyType.PEACH],
        like_food_categories_id=["KOREAN"],
        categories_id=["KOREAN"],
        other_characteristics="Quiet atmosphere",
    )
    return UpdatePersonaDBRequest(user_data=user, review_data=[])


@pytest.mark.asyncio
async def test_generate_base_persona_node(mock_request_data):
    # Mock LLM response
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Generated Persona Content"
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=mock_response)

    # Mock pipe operator (|) behavior
    # chain = prompt | llm 구조에서 prompt | llm 이 mock_chain을 반환하도록 설정
    # 하지만 실제 코드에서는 prompt | llm 수행 후 .ainvoke를 하므로
    # get_llm()이 반환하는 객체가 __ror__ (오른쪽 연산자) 등을 처리하거나
    # 단순히 chain.ainvoke를 mocking하는 것이 까다로울 수 있음.
    # 여기서는 get_llm() 자체를 patch하고, prompt | llm 결과물을 mock_chain으로 대체하는 방식을 사용해야 함.

    with patch(
        "src.recommendation.features.persona_manager.workflows.nodes.get_llm"
    ) as mock_get_llm:
        # prompt | llm 연산의 결과를 모킹하기 위해, prompt 객체의 __or__를 제어하기 어려우므로
        # nodes.py 내부의 로직을 수행시킬 때 chain.ainvoke가 호출되는 것을 확인.

        # 실제로는 LangChain의 pipe 동작을 unit test에서 완벽히 모킹하기 복잡하므로,
        # nodes.py의 `chain = prompt | llm` 부분 이후의 `chain.ainvoke`를 모킹하기 위해
        # ChatPromptTemplate의 __or__가 반환하는 객체(RunnableBinding)를 모킹해야 함.

        # 더 쉬운 방법: nodes.py에서 import한 get_llm이 반환하는 mock 객체를 설정

        # 하지만 | 연산자는 PromptTemplate 객체 메서드임.
        # 따라서 prompt | llm 구문이 실행되면 RunnableSequence가 나옴.
        # 이를 위해 RunnableSequence를 patch 하거나,
        # 간단하게 chain.ainvoke 호출 여부만 검증하는 것이 목표라면 integration style에 가까워짐.

        # Unit Test의 목적: 입력값이 프롬프트 변수에 잘 매핑되었는지 확인.
        # 따라서 우리는 `chain.ainvoke`에 전달된 인자(dictionary)를 검사하면 됨.

        # Mocking logic setup:
        mock_llm_instance = MagicMock()
        mock_get_llm.return_value = mock_llm_instance

        # prompt | llm 의 결과가 mock_chain이 되도록 해야 함.
        # 이를 위해 ChatPromptTemplate.from_messages를 patch해서 mock_prompt를 반환하게 하고
        # mock_prompt | mock_llm_instance -> mock_chain 이 되도록 설정.

        with patch(
            "src.recommendation.features.persona_manager.workflows.nodes.BASE_PERSONA_PROMPT"
        ) as mock_prompt:
            mock_prompt.__or__.return_value = mock_chain

            state = PersonaState(
                request_data=mock_request_data,
                generated_base_persona=None,
                final_document=None,
            )
            result = await generate_base_persona_node(state)

            assert result["generated_base_persona"] == "Generated Persona Content"

            # Verify arguments passed to chain.ainvoke
            # 프롬프트 변수들이 제대로 매핑되었는지 확인
            calls = mock_chain.ainvoke.call_args
            args, kwargs = calls
            passed_input = args[0]

            assert passed_input["nickname"] == "test_user"
            assert passed_input["age_group"] == AgeGroup.TWENTIES
            assert passed_input["preferred_ingredients"] == "KOREAN"
            assert passed_input["like_food_categories"] == "KOREAN"


@pytest.mark.asyncio
async def test_save_persona_node(mock_request_data):
    mock_base_persona = "Test Persona"

    with patch(
        "src.recommendation.features.persona_manager.workflows.nodes.PersonaRepository"
    ) as MockRepo:
        mock_repo_instance = AsyncMock()
        MockRepo.return_value = mock_repo_instance

        # Mock save return value
        mock_saved_doc = MagicMock()
        mock_saved_doc.id = 1
        mock_repo_instance.save.return_value = mock_saved_doc

        state = PersonaState(
            request_data=mock_request_data,
            generated_base_persona=mock_base_persona,
            final_document=None,
        )

        result = await save_persona_node(state)

        assert result["final_document"].id == 1

        # Verify save called with correct document
        mock_repo_instance.save.assert_called_once()
        saved_arg = mock_repo_instance.save.call_args[0][0]
        assert saved_arg.base_persona == mock_base_persona
        assert saved_arg.nickname == "test_user"
