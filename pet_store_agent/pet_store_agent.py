import os
import logging
from strands.models import BedrockModel

from orchestrator import PetStoreOrchestrator

logger = logging.getLogger(__name__)

logging.getLogger().setLevel(logging.INFO)

def create_agent():
    product_info_kb_id = os.environ.get("KNOWLEDGE_BASE_1_ID")
    pet_care_kb_id = os.environ.get("KNOWLEDGE_BASE_2_ID")
    inventory_management_function = os.environ.get("SYSTEM_FUNCTION_1_NAME")
    user_management_function = os.environ.get("SYSTEM_FUNCTION_2_NAME")

    if not product_info_kb_id or not pet_care_kb_id:
        raise ValueError(
            "Required environment variables KNOWLEDGE_BASE_1_ID and KNOWLEDGE_BASE_2_ID must be set"
        )

    if not inventory_management_function or not user_management_function:
        raise ValueError(
            "Required environment variables SYSTEM_FUNCTION_1_NAME and SYSTEM_FUNCTION_2_NAME must be set"
        )

    guardrail_id = os.environ.get("GUARDRAIL_ID", "i8ww2sdhqkcu")
    guardrail_version = os.environ.get("GUARDRAIL_VERSION", "1")
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        max_tokens=4096,
        streaming=False,
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version,
    )
    return PetStoreOrchestrator(model)


def process_request(prompt):
    try:
        agent = create_agent()
        response = agent(prompt)
        return response
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing request: {error_message}")
        return {
            "status": "Error",
            "message": "We are sorry for the technical difficulties...",
        }
