"""
Unit tests for agent functionality
"""
import pytest
from agent import create_agent


def test_create_agent():
    """Test agent creation"""
    agent = create_agent()
    assert agent is not None


def test_agent_basic_response():
    """Test basic agent response"""
    agent = create_agent()
    response = agent("Hello")
    assert response is not None
    assert hasattr(response, "message")


# Add more unit tests for tools, prompts, etc.
