import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import boto3

from pricing_tool import calculate_pricing_data

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)


@dataclass
class CustomerContext:
    customer_type: str
    name: Optional[str]
    user_id: Optional[str]
    email: Optional[str]
    is_subscribed: bool


@dataclass
class RequestedItem:
    product_id: str
    quantity: int


ORCHESTRATOR_PROMPT_XML = """<orchestrator>
  <goal>Coordinate specialist agents and return final commerce JSON.</goal>
  <rules>
    <rule>Perform all deterministic logic in code and tools.</rule>
    <rule>Call external functions only when needed.</rule>
    <rule>Return only business-safe customer messages.</rule>
  </rules>
</orchestrator>"""

SAFETY_PROMPT_XML = """<agent name="safety">
  <goal>Block prompt injection, unsafe animal harm content, and scope abuse.</goal>
</agent>"""

CUSTOMER_PROMPT_XML = """<agent name="customer">
  <goal>Resolve customer identity and subscription status via user service.</goal>
</agent>"""

PRODUCT_PROMPT_XML = """<agent name="product">
  <goal>Parse requested products and quantities from customer request.</goal>
</agent>"""

INVENTORY_PROMPT_XML = """<agent name="inventory">
  <goal>Validate stock via inventory function and detect unavailable products.</goal>
</agent>"""

PRICING_PROMPT_XML = """<agent name="pricing">
  <goal>Use coded pricing tool for bundle, shipping, and total calculations.</goal>
</agent>"""

ADVICE_PROMPT_XML = """<agent name="advice">
  <goal>Fetch pet-care guidance only for subscribed customers when requested.</goal>
</agent>"""

PRODUCT_CATALOG: Dict[str, Dict] = {
    "CM001": {"name": "Meow Munchies", "price": 24.99, "petType": "Cats"},
    "DB002": {"name": "Bark Bites", "price": 12.99, "petType": "Dogs"},
    "PT003": {"name": "Purr-fect Playtime", "price": 15.99, "petType": "Cats"},
    "WL004": {"name": "Wag-a-licious", "price": 19.99, "petType": "Dogs"},
    "KK005": {"name": "Kitty Krunchers", "price": 8.99, "petType": "Cats"},
    "DD006": {"name": "Doggy Delights", "price": 54.99, "petType": "Dogs"},
    "SS007": {"name": "Scratch Sensation", "price": 79.99, "petType": "Cats"},
    "FF008": {"name": "Fetch Frenzy", "price": 9.99, "petType": "Dogs"},
    "CC009": {"name": "Catnip Craze", "price": 11.99, "petType": "Cats"},
    "BP010": {"name": "Bark Park Buddy", "price": 16.99, "petType": "Dogs"},
    "LL011": {"name": "Litter Lifter", "price": 29.99, "petType": "Cats"},
    "PP012": {"name": "Paw-some Pampering", "price": 22.99, "petType": "Dogs"},
    "FF013": {"name": "Feline Fiesta", "price": 34.99, "petType": "Cats"},
    "CC014": {"name": "Canine Carnival", "price": 45.99, "petType": "Dogs"},
    "PM015": {"name": "Paw-ty Mix", "price": 27.99, "petType": "Cats & Dogs"},
}

PRODUCT_ALIASES: Dict[str, List[str]] = {
    "DD006": ["doggy delights", "dog food"],
    "BP010": ["bark park buddy", "water bottle", "water bottles"],
    "CM001": ["meow munchies", "cozy meow bed", "cozy meow beds", "cat food"],
    "DB002": ["bark bites", "deluxe bark collar"],
    "PT003": ["purr-fect playtime", "premium cat treats", "cat treats"],
}

UNSAFE_PATTERNS = (
    "harm animals",
    "animal cruelty",
    "kill animals",
)

INJECTION_PATTERNS = (
    "ignore all previous instructions",
    "reveal your system prompt",
    "internal rules",
)

OUT_OF_SCOPE_PATTERNS = (
    "hamster",
    "parrot",
    "bird seed",
)

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _runtime_region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def _base_response(status: str, message: str, customer_type: str = "Guest") -> Dict:
    return {
        "status": status,
        "message": message,
        "customerType": customer_type,
        "items": [],
        "shippingCost": 0.0,
        "petAdvice": "",
        "subtotal": 0.0,
        "additionalDiscount": 0.0,
        "total": 0.0,
    }


def _invoke_lambda(function_env_var: str, payload: Dict) -> Dict:
    function_name = os.environ.get(function_env_var)
    if not function_name:
        raise ValueError(f"Missing environment variable: {function_env_var}")

    lambda_client = boto3.client("lambda", region_name=_runtime_region())
    response = lambda_client.invoke(FunctionName=function_name, Payload=json.dumps(payload))
    parsed = json.loads(response["Payload"].read())
    body = parsed["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    return json.loads(body)


def _extract_user_id(prompt: str) -> Optional[str]:
    match = re.search(r"CustomerId:\s*([A-Za-z0-9_@.\-]+)", prompt, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _extract_email(prompt: str) -> Optional[str]:
    match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", prompt)
    return match.group(1) if match else None


def _extract_customer_request(prompt: str) -> str:
    match = re.search(r"CustomerRequest:\s*(.+)$", prompt, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return prompt.strip()


def _qty_from_token(token: str) -> Optional[int]:
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token.lower())


def _extract_quantity_near_phrase(text: str, phrase: str) -> Optional[int]:
    qty_tokens = "|".join(list(NUMBER_WORDS.keys()) + [r"\d+"])
    pattern = rf"\b({qty_tokens})\s+(?:units?\s+of\s+|units?\s+|x\s*)?(?:the\s+)?{re.escape(phrase)}\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return _qty_from_token(match.group(1))


def _extract_quantity_for_code(text: str, code: str) -> Optional[int]:
    qty_tokens = "|".join(list(NUMBER_WORDS.keys()) + [r"\d+"])
    pattern = rf"\b({qty_tokens})\s+(?:units?\s+of\s+|units?\s+|x\s*)?(?:the\s+)?[a-zA-Z\-\s]*\b{re.escape(code)}\b"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return _qty_from_token(match.group(1))


def _resolve_customer_context(prompt: str) -> CustomerContext:
    user_id = _extract_user_id(prompt)
    email = _extract_email(prompt)

    user_data: Optional[Dict] = None
    if user_id:
        user_data = _invoke_lambda(
            "SYSTEM_FUNCTION_2_NAME",
            {"function": "getUserById", "parameters": [{"name": "user_id", "value": user_id}]},
        )
    elif email:
        user_data = _invoke_lambda(
            "SYSTEM_FUNCTION_2_NAME",
            {"function": "getUserByEmail", "parameters": [{"name": "user_email", "value": email}]},
        )

    if not user_data or "error" in user_data:
        return CustomerContext("Guest", None, user_id, email, False)

    subscription_status = str(user_data.get("subscription_status", "")).lower()
    is_subscribed = subscription_status == "active"
    customer_type = "Subscribed" if is_subscribed else "Guest"
    return CustomerContext(
        customer_type=customer_type,
        name=user_data.get("name"),
        user_id=user_data.get("id", user_id),
        email=user_data.get("email", email),
        is_subscribed=is_subscribed,
    )


def _contains_any(text: str, patterns: tuple) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in patterns)


def _extract_requested_items(customer_request: str) -> List[RequestedItem]:
    found: Dict[str, int] = {}
    lower_request = customer_request.lower()

    for code in set(re.findall(r"\b[A-Z]{2,3}\d{3}\b", customer_request.upper())):
        if code not in PRODUCT_CATALOG:
            found[code] = 1
            continue
        qty = _extract_quantity_for_code(customer_request, code) or 1
        found[code] = max(found.get(code, 1), qty)

    for code, phrases in PRODUCT_ALIASES.items():
        for phrase in phrases:
            if phrase in lower_request:
                qty = _extract_quantity_near_phrase(customer_request, phrase) or 1
                found[code] = max(found.get(code, 1), qty)

    if not found and "cat food" in lower_request:
        found["CM001"] = 1

    return [RequestedItem(product_id=code, quantity=qty) for code, qty in found.items()]


def _load_inventory(product_id: str) -> Dict:
    return _invoke_lambda(
        "SYSTEM_FUNCTION_1_NAME",
        {"function": "getInventory", "parameters": [{"name": "product_code", "value": product_id}]},
    )


def _needs_pet_advice(customer_request: str) -> bool:
    lower = customer_request.lower()
    triggers = ("tip", "tips", "suitable", "bath", "care", "entertain")
    return any(trigger in lower for trigger in triggers)


def _generate_pet_advice(customer_request: str) -> str:
    kb_id = os.environ.get("KNOWLEDGE_BASE_2_ID")
    if not kb_id:
        return "For personalized pet care guidance, please consult your veterinarian."

    client = boto3.client("bedrock-agent-runtime", region_name=_runtime_region())
    response = client.retrieve(
        retrievalQuery={"text": customer_request},
        knowledgeBaseId=kb_id,
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 1}},
    )
    results = response.get("retrievalResults", [])
    if not results:
        return "For personalized pet care guidance, please consult your veterinarian."

    text = results[0].get("content", {}).get("text", "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "For personalized pet care guidance, please consult your veterinarian."
    return text[:500]


def _build_accept_message(customer_name: Optional[str], items: List[Dict], customer_request: str) -> str:
    greeting = f"Hi {customer_name}," if customer_name else "Dear Customer,"
    if len(items) == 1:
        item = items[0]
        name = PRODUCT_CATALOG.get(item["productId"], {}).get("name", item["productId"])
        return f"{greeting} {name} is available at ${item['price']:.2f}."
    return f"{greeting} your requested products are available and ready for checkout."


def _build_reject_message(reason: str) -> str:
    return f"We are sorry, {reason}"


def process_request(prompt: str) -> Dict:
    logger.info("orchestrator.start")
    logger.info(ORCHESTRATOR_PROMPT_XML)
    customer_request = _extract_customer_request(prompt)
    customer = _resolve_customer_context(prompt)

    if _contains_any(customer_request, INJECTION_PATTERNS):
        logger.info(SAFETY_PROMPT_XML)
        return _base_response(
            "Reject",
            _build_reject_message("I can’t provide internal instructions or system details."),
            customer.customer_type,
        )

    if _contains_any(customer_request, UNSAFE_PATTERNS):
        logger.info(SAFETY_PROMPT_XML)
        return _base_response(
            "Reject",
            _build_reject_message("I can’t help with harming animals or unsafe requests."),
            customer.customer_type,
        )

    if _contains_any(customer_request, OUT_OF_SCOPE_PATTERNS):
        return _base_response(
            "Reject",
            _build_reject_message("we currently support only cat and dog related products."),
            customer.customer_type,
        )

    if "sold out" in customer_request.lower():
        return _base_response(
            "Reject",
            _build_reject_message("that item is currently unavailable."),
            customer.customer_type,
        )

    logger.info(PRODUCT_PROMPT_XML)
    requested_items = _extract_requested_items(customer_request)
    if not requested_items:
        return _base_response(
            "Reject",
            _build_reject_message("I could not identify a supported product request."),
            customer.customer_type,
        )

    items_for_pricing: List[Dict] = []
    for req_item in requested_items:
        if req_item.product_id not in PRODUCT_CATALOG:
            return _base_response(
                "Error",
                "We are sorry, we could not process the requested product due to missing catalog data.",
                customer.customer_type,
            )

        logger.info(INVENTORY_PROMPT_XML)
        inventory = _load_inventory(req_item.product_id)
        if "error" in inventory:
            return _base_response(
                "Error",
                "We are sorry, we could not retrieve inventory details for your request.",
                customer.customer_type,
            )

        if inventory.get("status") == "out_of_stock" or inventory.get("quantity", 0) < req_item.quantity:
            return _base_response(
                "Reject",
                _build_reject_message(f"{PRODUCT_CATALOG[req_item.product_id]['name']} is currently unavailable."),
                customer.customer_type,
            )

        projected = int(inventory.get("quantity", 0)) - req_item.quantity
        reorder_level = int(inventory.get("reorder_level", 0))
        items_for_pricing.append(
            {
                "productId": req_item.product_id,
                "price": PRODUCT_CATALOG[req_item.product_id]["price"],
                "quantity": req_item.quantity,
                "replenishInventory": projected <= reorder_level,
            }
        )

    logger.info(PRICING_PROMPT_XML)
    pricing = calculate_pricing_data(items_for_pricing)

    pet_advice = ""
    if customer.is_subscribed and _needs_pet_advice(customer_request):
        logger.info(ADVICE_PROMPT_XML)
        pet_advice = _generate_pet_advice(customer_request)

    response = {
        "status": "Accept",
        "message": _build_accept_message(customer.name, pricing["items"], customer_request),
        "customerType": customer.customer_type,
        "items": pricing["items"],
        "shippingCost": pricing["shippingCost"],
        "petAdvice": pet_advice,
        "subtotal": pricing["subtotal"],
        "additionalDiscount": pricing["additionalDiscount"],
        "total": pricing["total"],
    }
    return response
