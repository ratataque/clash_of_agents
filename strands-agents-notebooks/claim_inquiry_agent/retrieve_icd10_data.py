"""
Amazon Bedrock Knowledge Base retrieval tool for ICD-10 diagnosis codes.
"""
import os
import boto3
import logging
from typing import Any, Dict, List
from strands.types.tools import ToolResult, ToolUse

logger = logging.getLogger(__name__)

TOOL_SPEC = {
    "name": "retrieve_icd10_data",
    "description": "Retrieves ICD-10 diagnosis code information from the knowledge base. Use this tool to look up diagnosis codes, validate codes, find code descriptions, check if codes are billable, and find related diagnosis codes. Contains ICD-10 classifications for: endocrine/metabolic diseases, musculoskeletal disorders, nervous system diseases, mental/behavioural disorders, congenital malformations, and other conditions.",
    "inputSchema": {
        "json": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The query to retrieve ICD-10 diagnosis information (e.g., 'E11.9 diabetes', 'rheumatoid arthritis codes', 'M54.5 back pain').",
                },
                "numberOfResults": {
                    "type": "integer",
                    "description": "The maximum number of results to return. Default is 10.",
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
        return "No ICD-10 results found above score threshold."

    formatted = []
    for result in results:
        doc_id = result.get("location", {}).get("customDocumentLocation", {}).get("id", "Unknown")
        score = result.get("score", 0.0)
        formatted.append(f"\nScore: {score:.4f}")
        formatted.append(f"Document: {doc_id}")

        content = result.get("content", {})
        if content and isinstance(content.get("text"), str):
            text = content["text"]
            formatted.append(f"Content: {text}\n")

    return "\n".join(formatted)


def retrieve_icd10_data(tool: ToolUse, **kwargs: Any) -> ToolResult:
    """Retrieve ICD-10 diagnosis code data from Amazon Bedrock Knowledge Base."""
    
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]
    logger.info(f"retrieve_icd10_data called with input: {tool_input}")

    kb_id = os.environ.get('KNOWLEDGE_BASE_1_ID')

    try:
        query = tool_input["text"]
        number_of_results = tool_input.get("numberOfResults", 10)
        region_name = os.environ.get('AWS_REGION', 'us-west-2')
        min_score = tool_input.get("score", 0.25)

        bedrock_agent_runtime_client = boto3.client("bedrock-agent-runtime", region_name=region_name)

        response = bedrock_agent_runtime_client.retrieve(
            retrievalQuery={"text": query},
            knowledgeBaseId=kb_id,
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": number_of_results},
            },
        )

        all_results = response.get("retrievalResults", [])
        filtered_results = filter_results_by_score(all_results, min_score)
        formatted_results = format_results_for_display(filtered_results)

        result = {
            "toolUseId": tool_use_id,
            "status": "success",
            "content": [
                {"text": f"Retrieved {len(filtered_results)} ICD-10 results with score >= {min_score}:\n{formatted_results}"}
            ],
        }
        logger.info(f"retrieve_icd10_data returning result: {result}")
        return result

    except Exception as e:
        logger.error(f"retrieve_icd10_data() error: {str(e)}")
        result = {
            "toolUseId": tool_use_id,
            "status": "error",
            "content": [{"text": f"Error retrieving ICD-10 data: {str(e)}"}],
        }
        return result
