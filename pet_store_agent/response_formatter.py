import json
import logging
from strands import tool

logger = logging.getLogger(__name__)


@tool
def format_order_response(
    status: str,
    message: str,
    customer_type: str,
    items_json: str,
    shipping_cost: float,
    subtotal: float,
    additional_discount: float,
    total: float,
    pet_advice: str = "",
) -> dict:
    """
    Format order response into the exact JSON schema expected by evaluation.

    Args:
    - status: "Accept", "Reject", or "Error"
    - message: Customer-facing message (max 250 chars)
    - customer_type: "Guest" or "Subscribed"
    - items_json: JSON string of the items array
    - shipping_cost: Shipping cost amount
    - subtotal: Order subtotal
    - additional_discount: Discount amount (0 or 0.15)
    - total: Final total
    - pet_advice: Pet care advice (optional, default="")

    Returns:
        Dict with status and formatted JSON response
    """
    logger.info(
        f"format_order_response called with status={status}, customer_type={customer_type}"
    )

    try:
        items = json.loads(items_json)

        response_dict = {
            "status": status,
            "message": message,
            "customerType": customer_type,
            "items": items,
            "shippingCost": shipping_cost,
            "petAdvice": pet_advice,
            "subtotal": subtotal,
            "additionalDiscount": additional_discount,
            "total": total,
        }

        result = {"status": "success", "content": [{"text": json.dumps(response_dict)}]}
        logger.info(f"format_order_response returning result: {result}")
        return result
    except Exception as e:
        logger.error(f"format_order_response() error: {str(e)}")
        result = {
            "status": "error",
            "content": [{"text": f"Failed to format response: {str(e)}"}],
        }
        logger.info(f"format_order_response returning result: {result}")
        return result
