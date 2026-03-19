"""
Shared utilities for Amazon Bedrock Knowledge Base retrievals.
Centralizes boto3 bedrock-agent-runtime usage and result parsing.
"""

import os
import boto3
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def retrieve_from_kb(
    kb_id: str,
    query: str,
    number_of_results: int = 10,
    min_score: float = 0.25,
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve information from Amazon Bedrock Knowledge Base.

    Args:
        kb_id: Knowledge Base ID
        query: Search query text
        number_of_results: Maximum number of results to return
        min_score: Minimum relevance score threshold (0.0-1.0)
        region_name: AWS region (defaults to AWS_REGION env var or us-west-2)

    Returns:
        Dict with:
            - status: "success" or "error"
            - results: List of result dicts with score, content, document_id (if success)
            - error: Error message (if error)

    Example:
        result = retrieve_from_kb(
            kb_id="JZIDPRZPJJ",
            query="Doggy Delights",
            min_score=0.3
        )
        if result["status"] == "success":
            for item in result["results"]:
                print(f"Score: {item['score']}, Content: {item['content']}")
    """
    if not region_name:
        region_name = os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
        )

    try:
        logger.info(f"Retrieving from KB {kb_id} with query: {query[:50]}...")

        bedrock_client = boto3.client("bedrock-agent-runtime", region_name=region_name)

        response = bedrock_client.retrieve(
            retrievalQuery={"text": query},
            knowledgeBaseId=kb_id,
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": number_of_results}
            },
        )

        all_results = response.get("retrievalResults", [])

        # Filter and structure results
        filtered_results = []
        for result in all_results:
            score = result.get("score", 0.0)
            if score >= min_score:
                content_obj = result.get("content", {})
                content_text = (
                    content_obj.get("text", "") if isinstance(content_obj, dict) else ""
                )

                doc_location = result.get("location", {}).get(
                    "customDocumentLocation", {}
                )
                document_id = (
                    doc_location.get("id", "Unknown")
                    if isinstance(doc_location, dict)
                    else "Unknown"
                )

                filtered_results.append(
                    {
                        "score": score,
                        "content": content_text,
                        "document_id": document_id,
                    }
                )

        logger.info(
            f"KB retrieval succeeded: {len(filtered_results)} results above score {min_score}"
        )
        return {"status": "success", "results": filtered_results}

    except Exception as e:
        logger.error(f"KB retrieval from {kb_id} failed: {str(e)}")
        return {
            "status": "error",
            "error": f"Knowledge Base retrieval failed: {str(e)}",
            "results": [],
        }


def retrieve_product_info(
    query: str, number_of_results: int = 10, min_score: float = 0.25
) -> Dict[str, Any]:
    """
    Retrieve product information from the product catalog Knowledge Base.

    Args:
        query: Product search query
        number_of_results: Maximum results
        min_score: Minimum relevance score

    Returns:
        Dict with status and results list
    """
    kb_id = os.environ.get("KNOWLEDGE_BASE_1_ID")
    if not kb_id:
        return {
            "status": "error",
            "error": "KNOWLEDGE_BASE_1_ID environment variable not set",
            "results": [],
        }

    return retrieve_from_kb(
        kb_id=kb_id,
        query=query,
        number_of_results=number_of_results,
        min_score=min_score,
    )


def retrieve_pet_care(
    query: str, number_of_results: int = 10, min_score: float = 0.25
) -> Dict[str, Any]:
    """
    Retrieve pet care advice from the pet care Knowledge Base.

    Args:
        query: Pet care question
        number_of_results: Maximum results
        min_score: Minimum relevance score

    Returns:
        Dict with status and results list
    """
    kb_id = os.environ.get("KNOWLEDGE_BASE_2_ID")
    if not kb_id:
        return {
            "status": "error",
            "error": "KNOWLEDGE_BASE_2_ID environment variable not set",
            "results": [],
        }

    return retrieve_from_kb(
        kb_id=kb_id,
        query=query,
        number_of_results=number_of_results,
        min_score=min_score,
    )
