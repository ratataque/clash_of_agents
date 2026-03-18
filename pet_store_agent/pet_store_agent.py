import os
import logging
from typing import Any
from strands import Agent
from strands.models import BedrockModel

import retrieve_product_info
from inventory_management import get_inventory
from pricing import calculate_order_pricing
from response_formatter import format_order_response

logger = logging.getLogger(__name__)

logging.getLogger().setLevel(logging.INFO)

system_prompt = """
You are an online pet store assistant for staff. Analyze customer requests and respond using your tools in this exact order:

## Execution Flow
1. Use retrieve_product_info to look up products matching the customer's request
2. For each product found, use get_inventory to check stock levels
3. Use calculate_order_pricing with the product data to get deterministic pricing
4. Use format_order_response to build the final JSON response
5. Return ONLY the JSON output from format_order_response — nothing else

## Business Rules
- Status "Accept" when product found and in stock
- Status "Reject" with "We are sorry..." when product unavailable
- Status "Error" with "We are sorry..." on system issues
- customerType is always "Guest" when no user ID or email is provided in the request
- petAdvice is always "" (empty string) for Guest customers
- NEVER do math yourself — always use calculate_order_pricing
- NEVER construct JSON manually — always use format_order_response
- Product identifiers are for internal tool use and must not appear in the customer-facing message
- Default quantity to 1 unless the customer explicitly asks for a different quantity
- If tool output is missing, inconsistent, or errors, return status "Error" via format_order_response

## Tool Usage Details

### Step 1: retrieve_product_info
Call with the product name from the customer query.
Extract from results: product_id (like DD006), price, product name/description.

### Step 2: get_inventory
Call with the product_code (e.g. "DD006") from step 1.
Extract: quantity (current stock), reorder_level.

### Step 3: calculate_order_pricing
Call with items as a JSON string: [{"product_id": "<id>", "price": <price>, "quantity": <qty>, "current_stock": <stock>, "reorder_level": <reorder>}]
- Default quantity to 1 unless customer specifies otherwise
- Use price from product info, stock data from inventory
Extract ALL output: items array, shippingCost, subtotal, additionalDiscount, total

### Step 4: format_order_response
Call with:
- status: "Accept" (when product is available) or "Reject" / "Error" as required by the business rules
- message: A warm, friendly message about the product (max 250 chars, don't reveal product IDs)
- customer_type: "Guest" (no user ID/email in request)
- items_json: The items array from calculate_order_pricing as JSON string
- shipping_cost: From calculate_order_pricing
- subtotal: From calculate_order_pricing
- additional_discount: From calculate_order_pricing
- total: From calculate_order_pricing
- pet_advice: "" (empty, guest user)

For Reject responses, set items_json to [] and monetary fields to 0 when pricing was not produced.
For Error responses, set items_json to [] and monetary fields to 0.

### Step 5: Return
Output ONLY the text content from format_order_response. No additional text, no markdown, no explanation.

## Example
Input: "A new user is asking about the price of Doggy Delights?"
Expected Flow:
1. retrieve_product_info("Doggy Delights") → finds DD006 at $54.99
2. get_inventory("DD006") → stock: 150, reorder_level: 50
3. calculate_order_pricing('[{"product_id":"DD006","price":54.99,"quantity":1,"current_stock":150,"reorder_level":50}]')
4. format_order_response(status="Accept", message="Dear Customer!...", customer_type="Guest", items_json=..., shipping_cost=14.95, subtotal=69.94, additional_discount=0, total=69.94)
5. Return the JSON from step 4

Remember: return JSON only. Always use retrieve_product_info, get_inventory, calculate_order_pricing, and format_order_response in that order for product pricing inquiries.
"""


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

    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        max_tokens=4096,
        streaming=False,
    )

    tools = [
        retrieve_product_info,
        get_inventory,
        calculate_order_pricing,
        format_order_response,
    ]

    agent: Any = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=tools,
    )
    setattr(agent, "tools", tools)
    return agent


def process_request(prompt):
    try:
        agent = create_agent()
        response = agent(prompt)
        return str(response)
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing request: {error_message}")
        return {
            "status": "Error",
            "message": "We are sorry for the technical difficulties...",
        }
