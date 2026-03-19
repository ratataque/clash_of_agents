"""
Customer Agent - Handle user lookup and subscription status determination.
Specialized agent focused on customer context and entitlements.
"""

import logging
import json
from typing import Dict, Any, Optional
from strands import Agent
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

CUSTOMER_PROMPT = """You are a customer context specialist for a pet store. Your job is to analyze user data and determine customer type.

You will be given user data from our system (or an error if lookup failed).

Your task:
1. Determine if user exists and has an active subscription
2. Extract customer name for personalization
3. Classify customerType as "Subscribed" or "Guest"

**Customer Type Rules:**
- "Subscribed": User exists AND subscription_status == "active"
- "Guest": ANY other case (expired, cancelled, no subscription, user not found, lookup error)

**Output Format (JSON only, no markdown):**
{
  "user_found": true|false,
  "first_name": "Sarah" or null,
  "customer_type": "Subscribed"|"Guest",
  "subscription_active": true|false,
  "reason": "brief explanation"
}

**CRITICAL:**
- Never expose internal subscription details (status, expiry dates, IDs) in reason
- Reason should be generic: "Active subscriber", "Guest customer", "User lookup failed"
- If subscription_status is "expired" or "cancelled", treat as Guest silently

Examples:

Input:
User lookup successful:
{
  "id": "usr_001",
  "name": "Sarah Johnson",
  "email": "sarah@example.com",
  "subscription_status": "active",
  "subscription_end_date": "2026-12-31"
}

Output:
{
  "user_found": true,
  "first_name": "Sarah",
  "customer_type": "Subscribed",
  "subscription_active": true,
  "reason": "Active subscriber"
}

Input:
User lookup successful:
{
  "id": "usr_002",
  "name": "John Doe",
  "subscription_status": "expired"
}

Output:
{
  "user_found": true,
  "first_name": "John",
  "customer_type": "Guest",
  "subscription_active": false,
  "reason": "Guest customer"
}

Input:
User lookup failed: User not found

Output:
{
  "user_found": false,
  "first_name": null,
  "customer_type": "Guest",
  "subscription_active": false,
  "reason": "Guest customer"
}

Now analyze:"""


def create_customer_agent() -> Agent:
    """
    Create the Customer Agent with customer classification model.

    Returns:
        Configured Customer Agent
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        max_tokens=512,
        streaming=False,
    )

    agent = Agent(
        model=model,
        system_prompt=CUSTOMER_PROMPT,
        tools=[],  # No tools - receives pre-fetched user data
    )

    return agent


def determine_customer_context(user_lookup_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine customer type and context from user lookup result.

    Args:
        user_lookup_result: Result from lambda_utils.get_user_by_id/email
            Expected: {"status": "success", "data": {...}} or {"status": "error", "error": "..."}

    Returns:
        Dict with:
            - user_found: bool
            - first_name: str | None
            - customer_type: "Subscribed" | "Guest"
            - subscription_active: bool
            - reason: str

    Example:
        user_result = get_user_by_id("usr_001")
        context = determine_customer_context(user_result)
        # Returns: {"customer_type": "Subscribed", "first_name": "Sarah", ...}
    """
    try:
        logger.info("Customer Agent: analyzing user lookup result")

        # Format user data for agent
        if user_lookup_result.get("status") == "success":
            user_data = user_lookup_result.get("data", {})
            prompt = f"User lookup successful:\n{user_data}"
        else:
            error_msg = user_lookup_result.get("error", "Unknown error")
            prompt = f"User lookup failed: {error_msg}"

        agent = create_customer_agent()
        response = agent(prompt)

        context_data = json.loads(str(response))

        logger.info(
            f"Customer Agent: customer_type={context_data.get('customer_type')}, user_found={context_data.get('user_found')}"
        )
        return context_data

    except json.JSONDecodeError as e:
        logger.error(f"Customer Agent: failed to parse JSON response: {str(e)}")
        # Safe fallback
        return {
            "user_found": False,
            "first_name": None,
            "customer_type": "Guest",
            "subscription_active": False,
            "reason": f"Failed to parse customer context: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Customer Agent: unexpected error: {str(e)}")
        return {
            "user_found": False,
            "first_name": None,
            "customer_type": "Guest",
            "subscription_active": False,
            "reason": f"Customer context error: {str(e)}",
        }
