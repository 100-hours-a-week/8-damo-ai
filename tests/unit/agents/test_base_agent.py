"""BaseAgent 단위 테스트"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import pytest
from unittest.mock import Mock
from recommendation.features.iterative_discussion.agents.base_agent import BaseAgent


class ConcreteAgent(BaseAgent):
    """테스트용 구체 클래스"""

    async def generate_response(self, context, messages=None):
        return "Test response"


def test_base_agent_initialization():
    """BaseAgent 초기화 테스트"""
    # Given
    mock_llm = Mock()
    name = "test_agent"
    temperature = 0.5

    # When
    agent = ConcreteAgent(llm=mock_llm, name=name, temperature=temperature)

    # Then
    assert agent.llm == mock_llm
    assert agent.name == name
    assert agent.temperature == temperature


def test_base_agent_repr():
    """BaseAgent __repr__ 테스트"""
    # Given
    mock_llm = Mock()
    agent = ConcreteAgent(llm=mock_llm, name="test", temperature=0.7)

    # When
    repr_str = repr(agent)

    # Then
    assert "ConcreteAgent" in repr_str
    assert "test" in repr_str
    assert "0.7" in repr_str


@pytest.mark.asyncio
async def test_base_agent_generate_response():
    """BaseAgent generate_response 추상 메서드 구현 테스트"""
    # Given
    mock_llm = Mock()
    agent = ConcreteAgent(llm=mock_llm, name="test")

    # When
    response = await agent.generate_response(context={})

    # Then
    assert response == "Test response"


def test_base_agent_cannot_instantiate():
    """BaseAgent는 직접 인스턴스화 불가능"""
    # Given
    mock_llm = Mock()

    # When/Then
    with pytest.raises(TypeError):
        BaseAgent(llm=mock_llm, name="test")
