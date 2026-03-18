"""Custom tools for the Strands agent"""

from strands import tool


@tool
def example_tool(input: str) -> str:
    """Example tool - replace with your own logic"""
    return f"Processed: {input}"
