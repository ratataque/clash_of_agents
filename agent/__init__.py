"""
Agent module for Strands agent implementation
"""
from .agent import create_agent, competition_tool
from .tools import (
    get_competition_info,
    analyze_request,
    search_knowledge_base,
    format_response,
)
from .prompts import (
    SYSTEM_PROMPT,
    ERROR_HANDLING_PROMPT,
    CONVERSATION_CONTEXT_PROMPT,
    get_task_specific_prompt,
)

__all__ = [
    "create_agent",
    "competition_tool",
    "get_competition_info",
    "analyze_request",
    "search_knowledge_base",
    "format_response",
    "SYSTEM_PROMPT",
    "ERROR_HANDLING_PROMPT",
    "CONVERSATION_CONTEXT_PROMPT",
    "get_task_specific_prompt",
]
