import os
import logging
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, cast
from strands import Agent
from strands.models import BedrockModel


def _load_env_file():
    if os.environ.get("KNOWLEDGE_BASE_1_ID"):
        return

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")

            if key and not os.environ.get(key):
                os.environ[key] = value


_load_env_file()

try:
    from . import retrieve_product_info
    from . import retrieve_pet_care
    from .inventory_management import get_inventory
    from .user_management import get_user_by_id, get_user_by_email
    from .pricing import calculate_order_pricing
    from .response_formatter import format_order_response
except ImportError:
    import retrieve_product_info
    import retrieve_pet_care
    from inventory_management import get_inventory
    from user_management import get_user_by_id, get_user_by_email
    from pricing import calculate_order_pricing
    from response_formatter import format_order_response

logger = logging.getLogger(__name__)

logging.getLogger().setLevel(logging.INFO)

_agent = None

system_prompt = """
You are an online pet store assistant for staff. Analyze customer requests and respond using tools.

<requirements>
- Return ONLY the raw JSON object from format_order_response. No markdown, no code fences, no explanation text.
- NEVER do math yourself — always use calculate_order_pricing.
- NEVER construct final JSON manually — always use format_order_response.
- CRITICAL: message must NEVER be empty for any status.
- Message style must always be customer-facing and polite; do not reference internal process/tooling.
- Product identifiers are internal and must not appear in customer-facing message text.
- Status="Accept" when product is found and can be fulfilled.
- Status="Reject" with "We are sorry..." style wording when the request cannot be fulfilled (for example unavailable/sold-out, inappropriate, or vague request that cannot be fulfilled).
- Status="Error" with "We are sorry..." style wording ONLY when explicit product code/name lookup fails, required internal product details are missing, or tool/system execution fails.
- If customer gives a specific product code or exact product name and retrieval returns no match, use status="Error".
- If product data is missing required internal details (pet type, stock, or other required fulfillment data), use status="Error".
- If request is vague (e.g., "limited edition dog toy", "sold out item") and cannot be found/fulfilled, use status="Reject".
- Default quantity to 1 unless customer explicitly asks for another quantity (e.g., "two" => 2).
- Bundle discount is handled by calculate_order_pricing for quantity > 1.
- If replenish_inventory is true, include a customer-facing restock warning (e.g., "This item is popular and may take time to restock.") without exposing internal stock or reorder thresholds.
- If inventory details are incomplete/missing, do not fail solely for that reason; continue with available data and produce the best valid response.
- CRITICAL: petAdvice MUST be "" whenever status="Error".
- EXCEPTION: If customerType="Subscribed" and request includes BOTH (a) unavailable/sold-out product and (b) pet-care question, return status="Accept" (NOT Reject), items=[], all monetary fields=0, non-empty message explaining unavailability plus provided advice, and petAdvice filled with relevant advice.
- For Reject responses where pricing is not produced, use items_json="[]" and all monetary fields 0.
- For Error responses, use items_json="[]" and all monetary fields 0.
</requirements>

<customer_types>
- customerType is "Subscribed" ONLY when known user exists and subscription_status is "active".
- Otherwise customerType is "Guest" (expired/cancelled/no subscription/unknown user).
- If CustomerId is present and lookup succeeds, greet by first name ("Hi <name>, ...") regardless of subscription status.
- For unknown users (or no CustomerId), greet as "Dear Customer".
- Never expose internal account details in message text (no subscription_status, expiry date, user IDs, or account metadata).
- If customer asks about subscription but it is not active, treat as Guest silently.
- For Reject where customer is not Subscribed or did not ask advice, petAdvice must be "".
- SPECIAL CASE repeats: Subscribed + unavailable product + pet-care question => status="Accept", items=[], monetary fields=0, petAdvice populated.
- Greeting should remain natural in all statuses (Accept/Reject/Error) while still following non-empty message requirement.
</customer_types>

<pet_care_advice>
- If status is "Error", petAdvice MUST be "".
- For Guest customers, petAdvice MUST be "".
- Provide petAdvice only when BOTH are true: customerType="Subscribed" and customer asked a pet-care question.
</pet_care_advice>

<flow_a>
- Guest/unknown-customer path: resolve product + inventory context, determine quantity, call calculate_order_pricing when items exist, then call format_order_response.
- For non-fulfillable guest outcomes, return Reject/Error with items_json="[]" and monetary fields set to 0.
- If inventory indicates replenish_inventory=true, keep response fulfillable but include restock-delay wording in message.
- Return only JSON string from format_order_response.
</flow_a>

<flow_b>
- Known-customer path: determine customerType from user data, then resolve product fulfillability.
- If fulfillable: calculate pricing and format response. Include petAdvice only for Subscribed + pet-care question.
- If not fulfillable:
  - Apply EXCEPTION rule for Subscribed + unavailable + pet-care question => Accept with advice, no items, all monetary fields 0.
  - Otherwise Reject (or Error when explicit lookup/system failure rules require it) with no items and zero monetary fields.
- When Subscribed customer asks pet-care question in fulfillable order path, include concise relevant petAdvice from pet-care retrieval/context.
- Always return only JSON from format_order_response.
</flow_b>

<tools>
- Product/user/inventory/pet-care context may already be pre-fetched; use provided context when available.
- Do not re-issue prefetched lookups unless required data is clearly absent.

<calculate_order_pricing>
Call with items_json list entries like:
[{"product_id":"<id>","price":<price>,"quantity":<qty>,"current_stock":<stock>,"reorder_level":<reorder>}]
Use returned fields: items, shippingCost, subtotal, additionalDiscount, total.
Always trust this tool for shipping cost, subtotal, discounts, and final total.
</calculate_order_pricing>

<format_order_response>
Always use this tool for final output with ALL parameters:
- status
- message (MUST NEVER be empty)
- customer_type
- items_json
- shipping_cost
- subtotal
- additional_discount
- total
- pet_advice

For Reject/Error without pricing, use items_json="[]" and set shipping_cost, subtotal, additional_discount, total to 0.
For EXCEPTION Accept (advice-only), also use items_json="[]" and all monetary fields 0.
</format_order_response>
</tools>
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

    guardrail_id = os.environ.get("GUARDRAIL_ID", "i8ww2sdhqkcu")
    guardrail_version = os.environ.get("GUARDRAIL_VERSION", "1")

    model = BedrockModel(
        model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        max_tokens=2048,
        streaming=False,
        guardrail_id=guardrail_id,
        guardrail_version=guardrail_version,
    )

    tools = [
        retrieve_product_info,
        retrieve_pet_care,
        get_inventory,
        get_user_by_id,
        get_user_by_email,
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


def _get_agent():
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


def _make_rejection_response(message):
    response = {
        "status": "Reject",
        "message": message,
        "customerType": "Guest",
        "items": [],
        "shippingCost": 0,
        "petAdvice": "",
        "subtotal": 0,
        "additionalDiscount": 0,
        "total": 0,
    }
    return json.dumps(response)


def _check_fast_reject(prompt):
    if not isinstance(prompt, str):
        return None

    normalized = prompt.lower()
    if not normalized.strip():
        return None

    injection_patterns = [
        r"\bignore\s+previous\b",
        r"\bignore\s+all\b",
        r"\breveal\s+your\s+system\s+prompt\b",
        r"\bsystem\s+prompt\b",
        r"\binternal\s+rules\b",
        r"\byou\s+are\s+now\b",
        r"\bforget\s+your\s+instructions\b",
        r"\boverride\b",
        r"\bdisregard\b",
    ]
    if any(
        re.search(pattern, normalized, re.IGNORECASE) for pattern in injection_patterns
    ):
        return _make_rejection_response(
            "Sorry! We can't accept your request. We only handle pet store orders for cats and dogs."
        )

    harmful_phrase_patterns = [
        r"\bharm\s+animals\b",
        r"\banimal\s+cruelty\b",
    ]
    has_harmful_phrase = any(
        re.search(pattern, normalized, re.IGNORECASE)
        for pattern in harmful_phrase_patterns
    )
    has_harm_verb = bool(
        re.search(r"\b(poison|hurt|abuse|kill|harm)\b", normalized, re.IGNORECASE)
    )
    has_animal_context = bool(
        re.search(
            r"\b(animal|animals|pet|pets|cat|dog|hamster|parrot|bird|fish|rabbit|snake|turtle|lizard|guinea\s+pig|ferret)\b",
            normalized,
            re.IGNORECASE,
        )
    )
    if has_harmful_phrase or (has_harm_verb and has_animal_context):
        return _make_rejection_response(
            "Sorry! We can't accept your request. We do not support harmful activities."
        )

    has_supported_pet_context = bool(
        re.search(r"\b(cat|dog|kitten|puppy|cats|dogs|kittens|puppies)\b", normalized)
    )
    if has_supported_pet_context:
        return None

    unsupported_pet_patterns = [
        r"\bhamster\b",
        r"\bparrot\b",
        r"\bbird\b",
        r"\bfish\b",
        r"\brabbit\b",
        r"\bsnake\b",
        r"\bturtle\b",
        r"\blizard\b",
        r"\bguinea\s+pig\b",
        r"\bferret\b",
    ]
    if any(
        re.search(pattern, normalized, re.IGNORECASE)
        for pattern in unsupported_pet_patterns
    ):
        return _make_rejection_response(
            "Sorry! We can't accept your request. We only sell products for cats and dogs."
        )

    unsupported_product_patterns = [
        r"\bbird\s+seed\b",
        r"\bbird\s+food\b",
        r"\bfish\s+food\b",
        r"\bhamster\s+food\b",
        r"\bparrot\s+food\b",
        r"\brabbit\s+food\b",
        r"\bguinea\s+pig\s+food\b",
        r"\bferret\s+food\b",
        r"\bsnake\s+food\b",
        r"\bturtle\s+food\b",
        r"\blizard\s+food\b",
    ]
    if any(
        re.search(pattern, normalized, re.IGNORECASE)
        for pattern in unsupported_product_patterns
    ):
        return _make_rejection_response(
            "Sorry! We can't accept your request. We only sell products for cats and dogs."
        )

    return None


def _extract_text_content(tool_result):
    if not isinstance(tool_result, dict):
        return str(tool_result)

    content = tool_result.get("content")
    if not isinstance(content, list):
        return json.dumps(tool_result)

    parts = []
    for item in content:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])

    return "\n".join(parts) if parts else json.dumps(tool_result)


def _invoke_tool_function(tool_func, **kwargs):
    type_error = None
    for candidate in (
        tool_func,
        getattr(tool_func, "fn", None),
        getattr(tool_func, "__wrapped__", None),
    ):
        if candidate is None:
            continue
        try:
            return candidate(**kwargs)
        except TypeError as exc:
            type_error = exc

    if type_error is not None:
        raise type_error
    raise RuntimeError(f"Unable to invoke tool function: {tool_func}")


def _is_pet_care_question(text):
    return bool(
        re.search(
            r"\b(bath|groom|entertain|tips|advice|care|health|feeding|train|exercise)\b",
            text,
            re.IGNORECASE,
        )
    )


def _has_product_intent(text):
    if re.search(r"\b[A-Z]{2,}\d{3}\b", text):
        return True

    product_intent_keywords = [
        "price",
        "cost",
        "stock",
        "inventory",
        "order",
        "buy",
        "purchase",
        "product",
        "treat",
        "toy",
        "bottle",
        "pampering",
        "delights",
        "unit",
    ]
    normalized = text.lower()
    return any(keyword in normalized for keyword in product_intent_keywords)


def _extract_product_query(text):
    segments = [
        segment.strip() for segment in re.split(r"[\n.!?]+", text) if segment.strip()
    ]
    non_care_segments = [
        segment for segment in segments if not _is_pet_care_question(segment)
    ]
    if non_care_segments:
        return " ".join(non_care_segments)
    return text.strip()


def _extract_pet_care_query(text):
    segments = [
        segment.strip() for segment in re.split(r"[\n.!?]+", text) if segment.strip()
    ]
    care_segments = [segment for segment in segments if _is_pet_care_question(segment)]
    if care_segments:
        return " ".join(care_segments)
    return text.strip()


def _prefetch_data(prompt):
    try:
        if not isinstance(prompt, str) or not prompt.strip():
            return None

        customer_id_match = re.search(r"CustomerId:\s*(usr_\w+)", prompt, re.IGNORECASE)
        customer_id = customer_id_match.group(1) if customer_id_match else None

        customer_request_match = re.search(
            r"CustomerRequest:\s*(.*)", prompt, re.IGNORECASE | re.DOTALL
        )
        customer_request = (
            customer_request_match.group(1).strip()
            if customer_request_match
            else prompt.strip()
        )

        has_pet_care = _is_pet_care_question(customer_request)
        has_product = _has_product_intent(customer_request)

        product_query = (
            _extract_product_query(customer_request) if has_product else None
        )
        pet_care_query = (
            _extract_pet_care_query(customer_request) if has_pet_care else None
        )

        if not customer_id and not has_product and not has_pet_care:
            return None

        prefetched_results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            if customer_id:
                futures[
                    executor.submit(
                        _invoke_tool_function, get_user_by_id, user_id=customer_id
                    )
                ] = "user"

            if has_product and product_query:
                product_tool_use = {
                    "toolUseId": str(uuid.uuid4()),
                    "input": {"text": product_query},
                }
                futures[
                    executor.submit(
                        retrieve_product_info.retrieve_product_info,
                        cast(Any, product_tool_use),
                    )
                ] = "product"

            if has_pet_care and pet_care_query:
                pet_care_tool_use = {
                    "toolUseId": str(uuid.uuid4()),
                    "input": {"text": pet_care_query},
                }
                futures[
                    executor.submit(
                        retrieve_pet_care.retrieve_pet_care,
                        cast(Any, pet_care_tool_use),
                    )
                ] = "pet_care"

            for future in as_completed(futures):
                label = futures[future]
                try:
                    prefetched_results[label] = future.result()
                except Exception as exc:
                    logger.warning(f"Pre-fetch task failed for {label}: {exc}")

        product_text = _extract_text_content(prefetched_results.get("product", {}))
        product_code_match = re.search(r"\b([A-Z]{2,}\d{3})\b", product_text)
        if product_code_match:
            product_code = product_code_match.group(1)
            try:
                prefetched_results["inventory"] = _invoke_tool_function(
                    get_inventory, product_code=product_code
                )
            except Exception as exc:
                logger.warning(f"Pre-fetch task failed for inventory: {exc}")

        context_lines = [
            "[PRE-FETCHED CONTEXT — use this data instead of calling the tools again]",
            "The following data has already been retrieved. Do NOT call retrieve_product_info, retrieve_pet_care, get_user_by_id, or get_inventory again — use this data directly.",
        ]

        has_data = False
        if "user" in prefetched_results:
            context_lines.append(
                f"User Data: {_extract_text_content(prefetched_results['user'])}"
            )
            has_data = True
        if "product" in prefetched_results:
            context_lines.append(
                f"Product Info: {_extract_text_content(prefetched_results['product'])}"
            )
            has_data = True
        if "pet_care" in prefetched_results:
            context_lines.append(
                f"Pet Care Info: {_extract_text_content(prefetched_results['pet_care'])}"
            )
            has_data = True
        if "inventory" in prefetched_results:
            context_lines.append(
                f"Inventory: {_extract_text_content(prefetched_results['inventory'])}"
            )
            has_data = True

        if not has_data:
            return None

        context_lines.append("[END PRE-FETCHED CONTEXT]")
        context_lines.append("")
        context_lines.append(prompt)
        return "\n".join(context_lines)
    except Exception as exc:
        logger.warning(f"Pre-fetch orchestration failed: {exc}")
        return None


def process_request(prompt):
    fast_response = _check_fast_reject(prompt)
    if fast_response is not None:
        return fast_response

    try:
        prefetched_prompt = _prefetch_data(prompt)
        final_prompt = prefetched_prompt if prefetched_prompt is not None else prompt

        agent = _get_agent()
        if hasattr(agent, "messages"):
            agent.messages = []
        response = agent(final_prompt)
        result = str(response)
        if result.startswith("```"):
            lines = result.split("\n")
            if len(lines) >= 3:
                result = "\n".join(lines[1:-1]).strip()
            elif len(lines) == 2:
                result = lines[1].strip("` \n")
        return result
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing request: {error_message}")
        return {
            "status": "Error",
            "message": "We are sorry for the technical difficulties...",
        }
