"""
Test configuration and fixtures
"""
import pytest
import os


@pytest.fixture
def aws_region():
    """AWS region for tests"""
    return "us-west-2"


@pytest.fixture
def model_id():
    """Bedrock model ID for tests"""
    return "us.anthropic.claude-sonnet-4-20250514-v1:0"


# Add more shared fixtures
