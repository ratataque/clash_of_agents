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
) -> Agent:
    """
    Create and configure the Strands agent.
    
    Args:
        model_id: Bedrock model ID (default: Claude Sonnet 4)
        region_name: AWS region (default: us-west-2)
        temperature: Model temperature for response generation
        
    Returns:
        Configured Strands Agent instance
    """
    # Default configuration
    model_id = model_id or os.getenv(
        "MODEL_ID",
        "us.anthropic.claude-sonnet-4-20250514-v1:0"
    )
    region_name = region_name or os.getenv("AWS_REGION", "us-west-2")
    
    # Initialize Bedrock model
    model = BedrockModel(
        model_id=model_id,
        region_name=region_name,
        temperature=temperature,
    )
    
    # Create agent with tools
    agent = Agent(
        model=model,
        tools=[
            calculator,
            current_time,
            competition_tool,
        ],
        system_prompt="""You are a helpful AI agent participating in the AWS Clash of Agents competition.
        
Your goals:
- Provide accurate, secure, and reliable responses
- Use available tools when appropriate
- Maintain conversation context
- Follow AWS best practices for security and observability

Be concise, helpful, and professional in your responses.""",
    )
    
    return agent


# For local testing
if __name__ == "__main__":
    print("Initializing Strands agent...")
    agent = create_agent()
    
    # Test conversation
    response = agent("Hello! Can you tell me the current time and calculate 42 * 137?")
    print(f"\nAgent Response:\n{response.message}")
