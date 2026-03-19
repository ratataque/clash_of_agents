"""
Response formatting service - programmatic JSON schema enforcement.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


_PRODUCT_CODE_PATTERN = re.compile(r"\b[A-Z]{2,5}\d{3,6}\b")
_USER_ID_PATTERN = re.compile(r"\busr_\d+\b", re.IGNORECASE)


def _redact_sensitive_message(message: str) -> str:
    redacted = _PRODUCT_CODE_PATTERN.sub("the selected product", message)
    redacted = _USER_ID_PATTERN.sub("customer", redacted)
    return redacted


def _mask_product_id(value: Any, index: int) -> Any:
    if isinstance(value, str) and _PRODUCT_CODE_PATTERN.fullmatch(value):
        return f"ITEM-{index + 1:03d}"
    return value


def _sanitize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for index, item in enumerate(items):
        copied = dict(item)
        if "productId" in copied:
            copied["productId"] = _mask_product_id(copied.get("productId"), index)
        sanitized.append(copied)
    return sanitized


def format_order_response(
    status: str,
    message: str,
    customer_type: str,
    items: List[Dict[str, Any]],
    shipping_cost: float,
    subtotal: float,
    additional_discount: float,
    total: float,
    pet_advice: str = "",
) -> Dict[str, Any]:
    """
    Format order response into the exact JSON schema expected by evaluation.

    This is a programmatic function that enforces schema compliance and validation.

    Args:
        status: "Accept", "Reject", or "Error"
        message: Customer-facing message (MUST NOT be empty)
        customer_type: "Guest" or "Subscribed"
        items: List of item dicts (can be empty list for Reject/Error)
        shipping_cost: Shipping cost amount
        subtotal: Order subtotal
        additional_discount: Discount rate (0 or 0.15)
        total: Final total
        pet_advice: Pet care advice (empty string for non-Subscribed or Error)

    Returns:
        Dict with the complete formatted response

    Validation Rules:
        - message MUST NOT be empty
        - petAdvice MUST be "" (empty string) when status is "Error"
        - For Reject/Error: items=[], monetary fields=0
        - customerType must be "Guest" or "Subscribed"
    """
    # Enforce validation rules
    if not message or message.strip() == "":
        logger.error(
            "format_order_response: message field is empty - this violates schema"
        )
        message = "Dear Customer, We are sorry for the inconvenience."

    message = _redact_sensitive_message(message).strip()
    if message == "":
        message = "Dear Customer, We are sorry for the inconvenience."

    if status == "Error" and pet_advice != "":
        logger.warning(
            "format_order_response: forcing petAdvice to empty string for Error status"
        )
        pet_advice = ""

    if customer_type not in ["Guest", "Subscribed"]:
        logger.warning(
            f"format_order_response: invalid customerType '{customer_type}', defaulting to 'Guest'"
        )
        customer_type = "Guest"

    response_dict = {
        "status": status,
        "message": message,
        "customerType": customer_type,
        "items": _sanitize_items(items),
        "shippingCost": shipping_cost,
        "petAdvice": pet_advice,
        "subtotal": subtotal,
        "additionalDiscount": additional_discount,
        "total": total,
    }

    logger.info(
        f"Formatted response: status={status}, customerType={customer_type}, items_count={len(items)}"
    )
    return response_dict


def generate_greeting(first_name: Optional[str], status: str) -> str:
    """
    Generate customer greeting based on name and status.

    Args:
        first_name: Customer's first name (None for unknown users)
        status: Response status (Accept, Reject, Error)

    Returns:
        Greeting string (e.g., "Hi Sarah," or "Dear Customer,")
    """
    if first_name:
        return f"Hi {first_name},"
    return "Dear Customer,"


def build_accept_message(
    greeting: str,
    items: List[Dict[str, Any]],
    shipping_cost: float,
    subtotal: float,
    total: float,
    replenish_needed: bool = False,
) -> str:
    """
    Build an Accept status message.

    Args:
        greeting: Greeting string
        items: List of item dicts
        replenish_needed: Whether any item needs replenishment

    Returns:
        Complete message string
    """
    item_count = sum(int(item.get("quantity", 0)) for item in items)
    if item_count <= 0:
        item_count = len(items)
    item_phrase = "item" if item_count == 1 else "items"

    base_message = (
        f"{greeting} Thank you for your order! "
        f"We've processed {item_count} {item_phrase}. "
        f"Subtotal: ${subtotal:.2f}, shipping: ${shipping_cost:.2f}, total: ${total:.2f}."
    )

    if replenish_needed:
        base_message += " This item is popular and may take time to restock."

    return base_message


def build_reject_message(
    greeting: str, reason: str = "we cannot assist with that request"
) -> str:
    """
    Build a Reject status message.

    Args:
        greeting: Greeting string
        reason: Specific rejection reason

    Returns:
        Complete message string
    """
    return f"{greeting} We are sorry, {reason}."


def build_error_message(
    greeting: str, reason: str = "we encountered technical difficulties"
) -> str:
    """
    Build an Error status message.

    Args:
        greeting: Greeting string
        reason: Specific error reason

    Returns:
        Complete message string
    """
    return f"{greeting} We are sorry, {reason}."
