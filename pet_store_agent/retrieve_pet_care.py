"""
Amazon Bedrock Knowledge Base retrieval tool for pet care information.
"""
import os
import boto3
import logging
from typing import Any, Dict, List
from strands.types.tools import ToolResult, ToolUse

logger = logging.getLogger(__name__)

TOOL_SPEC = {
    "name": "retrieve_pet_care",
    "description": "Retrieves pet care advice knowledge base containing reference sources which should be the only authoritative references on pet caring information.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The query to retrieve relevant pet care knowledge.",
                },
                "numberOfResults": {
                    "type": "integer",
                    "description": "The maximum number of results to return. Default is 10.",
                },
                "region": {
                    "type": "string",
                    "description": "The AWS region name. Default is 'us-west-2'.",
                },
                "score": {
                    "type": "number",
                    "description": "Minimum relevance score threshold (0.0-1.0).",
                    "default": 0.25,
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": ["text"],
        }
    },
}


def filter_results_by_score(results: List[Dict[str, Any]], min_score: float) -> List[Dict[str, Any]]:
    """Filter results based on minimum score threshold."""
    return [result for result in results if result.get("score", 0.0) >= min_score]


def format_results_for_display(results: List[Dict[str, Any]]) -> str:
    """Format retrieval results for readable display."""
    if not results:
        return "No results found above score threshold."

    formatted = []
    for result in results:
        doc_id = result.get("location", {}).get("customDocumentLocation", {}).get("id", "Unknown")
        score = result.get("score", 0.0)
        formatted.append(f"\nScore: {score:.4f}")
        formatted.append(f"Document ID: {doc_id}")

        content = result.get("content", {})
        if content and isinstance(content.get("text"), str):
            text = content["text"]
            formatted.append(f"Content: {text}\n")

    return "\n".join(formatted)


def retrieve_pet_care(tool: ToolUse, **kwargs: Any) -> ToolResult:
    """Retrieve pet care information from Amazon Bedrock Knowledge Base."""
    
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]
    logger.info(f"retrieve_pet_care called with input: {tool_input}")
    
    kb_id = os.environ.get('KNOWLEDGE_BASE_2_ID')

    try:
        # Extract parameters
        query = tool_input["text"]
        number_of_results = tool_input.get("numberOfResults", 10)
        region_name = tool_input.get("region", os.environ.get('AWS_REGION', 'us-west-2'))
        min_score = tool_input.get("score", 0.25)

        # Create a new client for each invocation
        bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=region_name)

        # Perform retrieval
        response = bedrock_agent_runtime_client.retrieve(
            retrievalQuery={"text": query},
            knowledgeBaseId=kb_id,
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": number_of_results},
            },
        )

        # Get and filter results
        all_results = response.get("retrievalResults", [])
        filtered_results = filter_results_by_score(all_results, min_score)

        # Format results for display
        formatted_results = format_results_for_display(filtered_results)

        # Return results
        result = {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [
                {"text": f"Retrieved {len(filtered_results)} pet care results with score >= {min_score}:\n{formatted_results}"}
            ],
        }
        logger.info(f"retrieve_pet_care returning result: {result}")
        return result

    except Exception as e:
        logger.error(f"retrieve_pet_care() error: {str(e)}")
        result = {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": f"Error retrieving pet care information: {str(e)}"}],
        }
        logger.info(f"retrieve_pet_care returning result: {result}")
        return result