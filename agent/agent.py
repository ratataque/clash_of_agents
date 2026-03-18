"""
Strands Agent Implementation for AWS Clash of Agents Competition
"""

from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator, current_time
from typing import Optional
import os


@tool
def competition_tool(query: str) -> str:
    """
    Custom competition-specific tool.

    Args:
        query: The user query to process

    Returns:
        Processed response string
    """
    # Add your competition-specific logic here
    return f"Processed query: {query}"


def create_agent(
    model_id: Optional[str] = None,
    region_name: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 64000,
    enable_extended_thinking: bool = False,
    thinking_budget_tokens: int = 10000,
    enable_prompt_caching: bool = True,
    cache_ttl_seconds: int = 3600,
) -> Agent:
    """
    Create and configure the Strands agent with latest Bedrock features.

    Args:
        model_id: Bedrock model ID (default: Claude Sonnet 4.6 with 1M context)
        region_name: AWS region (default: us-west-2)
        temperature: Model temperature for response generation (0.0-1.0)
        max_tokens: Maximum tokens in response (Claude 4+ supports up to 64K)
        enable_extended_thinking: Enable native reasoning/chain-of-thought (Claude 4+)
        thinking_budget_tokens: Max tokens for reasoning when extended thinking enabled
        enable_prompt_caching: Enable 1-hour prompt caching for repeated context (90% cost reduction)
        cache_ttl_seconds: Cache TTL - 300 (5min) or 3600 (1hr) for Claude 4.5+

    Returns:
        Configured Strands Agent instance with Claude Sonnet 4.6 (1M context)

    New Features (Claude 4.6):
        - 1 million token context window (no premium pricing)
        - Extended thinking: Native reasoning API for complex tasks
        - 1-hour prompt caching: 90% cost reduction + 85% latency reduction
        - Enhanced parallel tool use
        - 64K max output tokens (vs 8K in Claude 3.5)
    """
    # Default configuration - Claude Sonnet 4.6 (latest GA model, 1M context)
    model_id = model_id or os.getenv("MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    region_name = region_name or os.getenv("AWS_REGION", "us-west-2")

    model_kwargs = {
        "model_id": model_id,
        "region_name": region_name,
        "temperature": temperature,
    }

    if hasattr(BedrockModel, "max_tokens"):
        model_kwargs["max_tokens"] = max_tokens

    if enable_extended_thinking and hasattr(BedrockModel, "thinking"):
        model_kwargs["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget_tokens,
        }

    if enable_prompt_caching and hasattr(BedrockModel, "cache_control"):
        model_kwargs["cache_control"] = {
            "type": "ephemeral",
            "ttl_seconds": cache_ttl_seconds,
        }

    model = BedrockModel(**model_kwargs)

    system_prompt = """You are a helpful AI agent participating in the AWS Clash of Agents competition.
        
Your goals:
- Provide accurate, secure, and reliable responses
- Use available tools when appropriate
- Maintain conversation context
- Follow AWS best practices for security and observability

Be concise, helpful, and professional in your responses."""

    agent_kwargs = {
        "model": model,
        "tools": [calculator, current_time, competition_tool],
        "system_prompt": system_prompt,
    }

    if enable_prompt_caching and hasattr(Agent, "cache_system_prompt"):
        agent_kwargs["cache_system_prompt"] = True

    agent = Agent(**agent_kwargs)

    return agent


# For local testing
if __name__ == "__main__":
    print("Initializing Strands agent...")
    agent = create_agent()

    # Test conversation
    response = agent("Hello! Can you tell me the current time and calculate 42 * 137?")
    print(f"\nAgent Response:\n{response.message}")
