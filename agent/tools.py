"""
Custom tools for the Strands agent
"""
from strands import tool
from typing import Dict, Any, List
import json


@tool
def get_competition_info() -> str:
    """
    Get information about the AWS Clash of Agents competition.
    
    Returns:
        Competition information and guidelines
    """
    return """AWS Clash of Agents Competition:
    - Focus: Building production-ready, secure, reliable, and observable agents
    - Platform: AWS Bedrock with Strands Agents SDK
    - Key Requirements: Security, reliability, observability, performance
    - Deployment: AWS CDK, AgentCore Runtime, Lambda integration
    """


@tool
def analyze_request(user_input: str) -> Dict[str, Any]:
    """
    Analyze user request and extract intent, entities, and required actions.
    
    Args:
        user_input: The user's input text
        
    Returns:
        Dictionary with analysis results
    """
    # Add your NLP/intent analysis logic here
    return {
        "input": user_input,
        "intent": "general_query",
        "confidence": 0.8,
        "entities": [],
        "suggested_actions": ["respond_with_info"]
    }


@tool
def search_knowledge_base(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search the agent's knowledge base for relevant information.
    
    Args:
        query: Search query
        top_k: Number of top results to return
        
    Returns:
        List of relevant knowledge base entries
    """
    # Placeholder - integrate with your knowledge base (S3, DynamoDB, etc.)
    return [
        {
            "title": "AWS Best Practices",
            "content": "Security, reliability, and performance guidelines",
            "relevance": 0.95
        }
    ]


@tool
def format_response(data: Dict[str, Any], format_type: str = "json") -> str:
    """
    Format data according to specified format type.
    
    Args:
        data: Data to format
        format_type: Output format (json, markdown, text)
        
    Returns:
        Formatted string
    """
    if format_type == "json":
        return json.dumps(data, indent=2)
    elif format_type == "markdown":
        # Convert to markdown format
        return f"# Response\n\n{json.dumps(data, indent=2)}"
    else:
        return str(data)


# Add more custom tools as needed for your competition entry
