import json
import logging
from typing import Dict, Any, List


def _uninitialized(*args, **kwargs):
    raise RuntimeError("Orchestrator dependencies are not initialized")


parse_intent = _uninitialized
determine_customer_context = _uninitialized
match_product = _uninitialized
get_user_by_id = _uninitialized
get_user_by_email = _uninitialized
get_inventory = _uninitialized
retrieve_product_info = _uninitialized
retrieve_pet_care = _uninitialized
format_order_response = _uninitialized
generate_greeting = _uninitialized
build_accept_message = _uninitialized
build_reject_message = _uninitialized
build_error_message = _uninitialized
calculate_order_pricing = _uninitialized


def _ensure_imports() -> None:
    global parse_intent
    global determine_customer_context
    global match_product
    global get_user_by_id
    global get_user_by_email
    global get_inventory
    global retrieve_product_info
    global retrieve_pet_care
    global format_order_response
    global generate_greeting
    global build_accept_message
    global build_reject_message
    global build_error_message
    global calculate_order_pricing

    if parse_intent is not _uninitialized:
        return

    try:
        from .agents.intent_agent import parse_intent as _parse_intent
        from .agents.customer_agent import (
            determine_customer_context as _determine_customer_context,
        )
        from .agents.product_agent import match_product as _match_product
        from .lib.lambda_utils import (
            get_user_by_id as _get_user_by_id,
            get_user_by_email as _get_user_by_email,
            get_inventory as _get_inventory,
        )
        from .lib.bedrock_utils import (
            retrieve_product_info as _retrieve_product_info,
            retrieve_pet_care as _retrieve_pet_care,
        )
        from .services.formatting import (
            format_order_response as _format_order_response,
            generate_greeting as _generate_greeting,
            build_accept_message as _build_accept_message,
            build_reject_message as _build_reject_message,
            build_error_message as _build_error_message,
        )
        from .pricing import calculate_order_pricing as _calculate_order_pricing
    except ImportError:
        from agents.intent_agent import parse_intent as _parse_intent
        from agents.customer_agent import (
            determine_customer_context as _determine_customer_context,
        )
        from agents.product_agent import match_product as _match_product
        from lib.lambda_utils import (
            get_user_by_id as _get_user_by_id,
            get_user_by_email as _get_user_by_email,
            get_inventory as _get_inventory,
        )
        from lib.bedrock_utils import (
            retrieve_product_info as _retrieve_product_info,
            retrieve_pet_care as _retrieve_pet_care,
        )
        from services.formatting import (
            format_order_response as _format_order_response,
            generate_greeting as _generate_greeting,
            build_accept_message as _build_accept_message,
            build_reject_message as _build_reject_message,
            build_error_message as _build_error_message,
        )
        from pricing import calculate_order_pricing as _calculate_order_pricing

    parse_intent = _parse_intent
    determine_customer_context = _determine_customer_context
    match_product = _match_product
    get_user_by_id = _get_user_by_id
    get_user_by_email = _get_user_by_email
    get_inventory = _get_inventory
    retrieve_product_info = _retrieve_product_info
    retrieve_pet_care = _retrieve_pet_care
    format_order_response = _format_order_response
    generate_greeting = _generate_greeting
    build_accept_message = _build_accept_message
    build_reject_message = _build_reject_message
    build_error_message = _build_error_message
    calculate_order_pricing = _calculate_order_pricing


logger = logging.getLogger(__name__)


def process_request(user_request: str) -> str:
    """
    Main orchestration function - coordinates all specialized agents and services.

    This replaces the monolithic LLM agent with programmatic flow control.

    Flow:
    1. Parse Intent (Intent Agent) → extract entities
    2. Handle security threats/out-of-scope immediately
    3. Lookup Customer (Customer Agent + lambda_utils) → determine type
    4. Retrieve Product (bedrock_utils + Product Agent) → match catalog
    5. Check Inventory (lambda_utils) → verify stock
    6. Calculate Pricing (pricing service) → compute totals
    7. Retrieve Pet Care Advice if applicable (bedrock_utils)
    8. Format Response (formatting service) → build final JSON

    Args:
        user_request: Raw customer request text

    Returns:
        JSON string with complete order response
    """
    try:
        _ensure_imports()
        logger.info("Orchestrator: starting request processing")

        # ===== STEP 1: Parse Intent =====
        intent = parse_intent(user_request)
        logger.info(f"Orchestrator: intent parsed - type={intent.get('request_type')}")

        # ===== STEP 2: Handle Security Threats & Out-of-Scope =====
        if intent.get("request_type") == "security_threat":
            return json.dumps(
                format_order_response(
                    status="Reject",
                    message="Dear Customer, We are sorry, we cannot assist with that request.",
                    customer_type="Guest",
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        if intent.get("request_type") == "out_of_scope":
            return json.dumps(
                format_order_response(
                    status="Reject",
                    message="Dear Customer, We are sorry, that request is outside our pet store scope.",
                    customer_type="Guest",
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        # ===== STEP 3: Lookup Customer =====
        customer_context = {
            "customer_type": "Guest",
            "first_name": None,
            "subscription_active": False,
        }

        if intent.get("customer_id"):
            user_result = get_user_by_id(intent["customer_id"])
            customer_context = determine_customer_context(user_result)
        elif intent.get("customer_email"):
            user_result = get_user_by_email(intent["customer_email"])
            customer_context = determine_customer_context(user_result)

        customer_type = customer_context.get("customer_type", "Guest")
        first_name = customer_context.get("first_name")
        subscription_active = customer_context.get("subscription_active", False)

        logger.info(
            f"Orchestrator: customer_type={customer_type}, subscription_active={subscription_active}"
        )

        # Generate greeting
        greeting = generate_greeting(first_name, status="Accept")

        # ===== STEP 4: Handle Pet-Care-Only Requests =====
        if intent.get("request_type") == "pet_care_only":
            if customer_type == "Subscribed" and intent.get("pet_care_question"):
                pet_care_result = retrieve_pet_care(intent["pet_care_question"])
                pet_advice = extract_pet_advice(pet_care_result)

                return json.dumps(
                    format_order_response(
                        status="Accept",
                        message=f"{greeting} Here is some advice for your question.",
                        customer_type=customer_type,
                        items=[],
                        shipping_cost=0,
                        subtotal=0,
                        additional_discount=0,
                        total=0,
                        pet_advice=pet_advice,
                    )
                )
            else:
                return json.dumps(
                    format_order_response(
                        status="Reject",
                        message=f"{greeting} We are sorry, pet care advice is only available to subscribed customers.",
                        customer_type=customer_type,
                        items=[],
                        shipping_cost=0,
                        subtotal=0,
                        additional_discount=0,
                        total=0,
                        pet_advice="",
                    )
                )

        # ===== STEP 5: Product Purchase Flow =====
        product_query = intent.get("product_query")
        quantity = intent.get("quantity", 1)

        if not product_query:
            return json.dumps(
                format_order_response(
                    status="Error",
                    message=build_error_message(
                        greeting, "no product was specified in your request"
                    ),
                    customer_type=customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        # Retrieve product from KB
        kb_result = retrieve_product_info(product_query)

        if kb_result.get("status") != "success" or not kb_result.get("results"):
            logger.warning(f"Orchestrator: KB retrieval failed or empty results")

            # SPECIAL CASE: Subscribed customer with pet care question
            if customer_type == "Subscribed" and intent.get("pet_care_question"):
                pet_care_result = retrieve_pet_care(intent["pet_care_question"])
                pet_advice = extract_pet_advice(pet_care_result)

                return json.dumps(
                    format_order_response(
                        status="Accept",
                        message=f"{greeting} Unfortunately, the product you requested is currently unavailable. However, here is some advice for your pet care question.",
                        customer_type=customer_type,
                        items=[],
                        shipping_cost=0,
                        subtotal=0,
                        additional_discount=0,
                        total=0,
                        pet_advice=pet_advice,
                    )
                )

            return json.dumps(
                format_order_response(
                    status="Error",
                    message=build_error_message(
                        greeting, "the product you requested was not found"
                    ),
                    customer_type=customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        # Match product using Product Agent
        product_match = match_product(product_query, kb_result["results"])

        if not product_match.get("match_found"):
            # SPECIAL CASE: Subscribed customer with pet care question
            if customer_type == "Subscribed" and intent.get("pet_care_question"):
                pet_care_result = retrieve_pet_care(intent["pet_care_question"])
                pet_advice = extract_pet_advice(pet_care_result)

                return json.dumps(
                    format_order_response(
                        status="Accept",
                        message=f"{greeting} {product_match.get('reason', 'Product unavailable')}. However, here is some advice for your pet care question.",
                        customer_type=customer_type,
                        items=[],
                        shipping_cost=0,
                        subtotal=0,
                        additional_discount=0,
                        total=0,
                        pet_advice=pet_advice,
                    )
                )

            return json.dumps(
                format_order_response(
                    status="Reject",
                    message=build_reject_message(
                        greeting,
                        product_match.get("reason", "the product is not available"),
                    ),
                    customer_type=customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        if not product_match.get("in_scope"):
            return json.dumps(
                format_order_response(
                    status="Reject",
                    message=build_reject_message(
                        greeting,
                        product_match.get("reason", "that product is out of scope"),
                    ),
                    customer_type=customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        # ===== STEP 6: Check Inventory =====
        product_id = product_match.get("product_id")
        price = product_match.get("price")

        if not product_id or price is None:
            return json.dumps(
                format_order_response(
                    status="Error",
                    message=build_error_message(
                        greeting, "product details are incomplete"
                    ),
                    customer_type=customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        inventory_result = get_inventory(product_id)

        if inventory_result.get("status") != "success":
            logger.warning(
                f"Orchestrator: inventory lookup failed, proceeding with defaults"
            )
            current_stock = 100  # Default for missing inventory
            reorder_level = 50
        else:
            inv_data = inventory_result.get("data", {})
            current_stock = inv_data.get("quantity", 100)
            reorder_level = inv_data.get("reorder_level", 50)

        # Check if in stock
        if current_stock < quantity:
            return json.dumps(
                format_order_response(
                    status="Reject",
                    message=build_reject_message(
                        greeting, "the product is currently out of stock"
                    ),
                    customer_type=customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        # ===== STEP 7: Calculate Pricing =====
        items_for_pricing = json.dumps(
            [
                {
                    "product_id": product_id,
                    "price": price,
                    "quantity": quantity,
                    "current_stock": current_stock,
                    "reorder_level": reorder_level,
                }
            ]
        )

        pricing_result = calculate_order_pricing(items_for_pricing)

        if pricing_result.get("status") != "success":
            return json.dumps(
                format_order_response(
                    status="Error",
                    message=build_error_message(
                        greeting, "we encountered a pricing error"
                    ),
                    customer_type=customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )
            )

        pricing_data = json.loads(pricing_result["content"][0]["text"])
        items = pricing_data.get("items", [])
        shipping_cost = pricing_data.get("shippingCost", 0)
        subtotal = pricing_data.get("subtotal", 0)
        additional_discount = pricing_data.get("additionalDiscount", 0)
        total = pricing_data.get("total", 0)

        # Check if replenishment needed
        replenish_needed = any(item.get("replenishInventory", False) for item in items)

        # ===== STEP 8: Retrieve Pet Care Advice (if applicable) =====
        pet_advice = ""
        if customer_type == "Subscribed" and intent.get("pet_care_question"):
            pet_care_result = retrieve_pet_care(intent["pet_care_question"])
            pet_advice = extract_pet_advice(pet_care_result)

        # ===== STEP 9: Format Final Response =====
        message = build_accept_message(
            greeting,
            items,
            shipping_cost,
            subtotal,
            total,
            replenish_needed,
        )

        response = format_order_response(
            status="Accept",
            message=message,
            customer_type=customer_type,
            items=items,
            shipping_cost=shipping_cost,
            subtotal=subtotal,
            additional_discount=additional_discount,
            total=total,
            pet_advice=pet_advice,
        )

        logger.info("Orchestrator: request processing completed successfully")
        return json.dumps(response)

    except Exception as e:
        logger.error(f"Orchestrator: unexpected error: {str(e)}")
        return json.dumps(
            format_order_response(
                status="Error",
                message="Dear Customer, We are sorry for the technical difficulties.",
                customer_type="Guest",
                items=[],
                shipping_cost=0,
                subtotal=0,
                additional_discount=0,
                total=0,
                pet_advice="",
            )
        )


def extract_pet_advice(pet_care_result: Dict[str, Any]) -> str:
    """
    Extract concise pet advice from KB retrieval results.

    Args:
        pet_care_result: Result from retrieve_pet_care

    Returns:
        Formatted pet advice string (or empty string if no results)
    """
    if pet_care_result.get("status") != "success":
        return ""

    results = pet_care_result.get("results", [])
    if not results:
        return ""

    # Take top result's content
    top_result = results[0]
    advice = top_result.get("content", "")

    # Truncate to reasonable length (max 500 chars)
    if len(advice) > 500:
        advice = advice[:497] + "..."

    return advice
