import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import boto3
from strands import Agent
from strands.models import BedrockModel

from inventory_management import get_inventory
from pricing import calculate_order_pricing
from response_formatter import format_order_response
from user_management import get_user_by_email, get_user_by_id

logger = logging.getLogger(__name__)

SORRY_MESSAGE = "We are sorry, we cannot assist with that request."
TECHNICAL_MESSAGE = "We are sorry for the technical difficulties..."


INTENT_AGENT_PROMPT = """
You extract structured intent from pet-store user requests.
Return only strict JSON with this schema:
{
  "customerId": string|null,
  "customerEmail": string|null,
  "customerRequest": string,
  "productQuery": string,
  "explicitProductCode": string|null,
  "quantity": integer,
  "asksPetCare": boolean,
  "isPromptInjection": boolean,
  "isHarmful": boolean,
  "isNonPetStore": boolean,
  "isOutOfScopePet": boolean
}
Rules:
- quantity defaults to 1 if not explicit.
- explicitProductCode is only for code-like tokens such as PT003/XYZ999.
- isOutOfScopePet is true for requests not about cats/dogs or pet-store products (e.g., hamster/bird).
- Return JSON only.
"""

PRODUCTS_AGENT_PROMPT = """
You identify the best product candidate from retrieval results.
Input will include customer request and retrieval snippets.
Return only strict JSON:
{
  "found": boolean,
  "productId": string|null,
  "productCode": string|null,
  "price": number|null,
  "isUnavailableHint": boolean,
  "reason": string
}
Rules:
- If no reliable product match exists, found=false.
- productCode should be an internal code-like token when present (e.g. DD006, PT003).
- isUnavailableHint=true if request indicates sold out/unavailable.
- Return JSON only.
"""

CUSTOMER_AGENT_PROMPT = """
You generate a safe greeting prefix for customer messages.
Return only strict JSON:
{
  "greeting": string
}
Rules:
- If known first name exists, greeting should be like "Hi <FirstName>,"
- Else use "Dear Customer,"
- Do not reveal subscription status, IDs, emails, or internal details.
- Keep greeting concise.
"""

ORCHESTRATOR_AGENT_PROMPT = """
You write a customer-facing pet-store message based on structured inputs.
Return only strict JSON:
{
  "message": string
}
Rules:
- Max 250 chars.
- Never include internal product IDs/codes.
- For Reject/Error, start with "We are sorry".
- For unavailable but accepted advice-only flow, explain product is unavailable and provide advice value.
- If replenish inventory is true, mention: "This item is popular and may take time to restock."
- No internal implementation details.
"""


@dataclass
class CustomerContext:
    customer_type: str
    first_name: Optional[str]
    greeting: str


def _extract_json_blob(text: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _safe_agent_json(agent: Agent, prompt: str) -> Optional[Dict[str, Any]]:
    try:
        response = agent(prompt)
        return _extract_json_blob(str(response))
    except Exception as exc:
        logger.error("Agent call failed: %s", exc)
        return None


def _extract_tool_json(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(result, dict):
        return None
    try:
        payload = result["content"][0]["text"]
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _extract_first_name(name: str) -> Optional[str]:
    if not name:
        return None
    first = name.strip().split(" ")[0]
    return first if first else None


def _parse_quantity_fallback(text: str) -> int:
    numeric_match = re.search(r"\b(\d+)\b", text)
    if numeric_match:
        return max(1, int(numeric_match.group(1)))

    number_words = {
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
    lowered = text.lower()
    for word, value in number_words.items():
        if re.search(rf"\b{word}\b", lowered):
            return value
    return 1


def _intent_fallback(prompt: str) -> Dict[str, Any]:
    customer_id_match = re.search(r"CustomerId:\s*([A-Za-z0-9_\-]+)", prompt, re.IGNORECASE)
    email_match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", prompt)
    request_match = re.search(r"CustomerRequest:\s*(.*)", prompt, re.IGNORECASE | re.DOTALL)
    customer_request = request_match.group(1).strip() if request_match else prompt.strip()
    product_code_match = re.search(r"\b([A-Z]{2,}\d{3})\b", customer_request)

    lowered = customer_request.lower()
    asks_pet_care = any(
        token in lowered
        for token in ["tip", "advice", "suitable", "care", "healthy", "bathing", "diet", "in shape"]
    )
    is_prompt_injection = "ignore all previous instructions" in lowered or "system prompt" in lowered
    is_harmful = any(token in lowered for token in ["harm", "cruelty", "abuse", "hurt animals"])
    is_non_pet_store = any(token in lowered for token in ["stocks", "politics", "weather", "bitcoin"])
    is_out_of_scope = any(token in lowered for token in ["hamster", "bird", "parrot"])

    return {
        "customerId": customer_id_match.group(1) if customer_id_match else None,
        "customerEmail": email_match.group(1) if email_match else None,
        "customerRequest": customer_request,
        "productQuery": customer_request,
        "explicitProductCode": product_code_match.group(1) if product_code_match else None,
        "quantity": _parse_quantity_fallback(customer_request),
        "asksPetCare": asks_pet_care,
        "isPromptInjection": is_prompt_injection,
        "isHarmful": is_harmful,
        "isNonPetStore": is_non_pet_store,
        "isOutOfScopePet": is_out_of_scope,
    }


class PetStoreOrchestrator:
    def __init__(self, model: BedrockModel):
        self.intent_agent: Any = Agent(model=model, system_prompt=INTENT_AGENT_PROMPT)
        self.products_agent: Any = Agent(model=model, system_prompt=PRODUCTS_AGENT_PROMPT)
        self.customer_agent: Any = Agent(model=model, system_prompt=CUSTOMER_AGENT_PROMPT)
        self.orchestrator_agent: Any = Agent(model=model, system_prompt=ORCHESTRATOR_AGENT_PROMPT)

    def _retrieve_kb(self, kb_id: str, text: str, number_of_results: int = 10, score: float = 0.25) -> List[Dict[str, Any]]:
        region_name = os.environ.get("AWS_REGION", "us-west-2")
        client = boto3.client("bedrock-agent-runtime", region_name=region_name)
        response = client.retrieve(
            retrievalQuery={"text": text},
            knowledgeBaseId=kb_id,
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": number_of_results}},
        )
        results = response.get("retrievalResults", [])
        return [item for item in results if item.get("score", 0.0) >= score]

    def _format_retrieval_for_agent(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No results."
        lines: List[str] = []
        for idx, result in enumerate(results, 1):
            content_text = result.get("content", {}).get("text", "")
            lines.append(f"[{idx}] score={result.get('score', 0.0):.4f}\n{content_text}")
        return "\n\n".join(lines)

    def _resolve_customer(self, intent: Dict[str, Any]) -> CustomerContext:
        user_data: Optional[Dict[str, Any]] = None
        customer_id = intent.get("customerId")
        customer_email = intent.get("customerEmail")

        if customer_id:
            user_data = _extract_tool_json(get_user_by_id(customer_id))
        elif customer_email:
            user_data = _extract_tool_json(get_user_by_email(customer_email))

        subscription_status = (user_data or {}).get("subscription_status")
        customer_type = "Subscribed" if subscription_status == "active" else "Guest"
        first_name = _extract_first_name((user_data or {}).get("name", ""))

        customer_prompt = json.dumps(
            {"firstName": first_name, "knownUser": bool(user_data)},
            ensure_ascii=True,
        )
        customer_agent_output = _safe_agent_json(self.customer_agent, customer_prompt) or {}
        greeting = customer_agent_output.get("greeting") or (f"Hi {first_name}," if first_name else "Dear Customer,")

        return CustomerContext(customer_type=customer_type, first_name=first_name, greeting=greeting)

    def _resolve_product(self, intent: Dict[str, Any], product_kb_id: str) -> Dict[str, Any]:
        retrieval_results = self._retrieve_kb(product_kb_id, intent.get("productQuery") or intent.get("customerRequest") or "")
        formatted = self._format_retrieval_for_agent(retrieval_results)
        products_prompt = json.dumps(
            {
                "customerRequest": intent.get("customerRequest"),
                "explicitProductCode": intent.get("explicitProductCode"),
                "retrievalResults": formatted,
            },
            ensure_ascii=True,
        )
        product_data = _safe_agent_json(self.products_agent, products_prompt) or {}
        return {
            "found": bool(product_data.get("found")),
            "product_id": product_data.get("productId"),
            "product_code": product_data.get("productCode"),
            "price": product_data.get("price"),
            "is_unavailable_hint": bool(product_data.get("isUnavailableHint")),
            "reason": product_data.get("reason", ""),
        }

    def _build_message(
        self,
        status: str,
        greeting: str,
        customer_type: str,
        unavailable: bool,
        advice_only_accept: bool,
        replenish_inventory: bool,
    ) -> str:
        prompt = json.dumps(
            {
                "status": status,
                "greeting": greeting,
                "customerType": customer_type,
                "unavailable": unavailable,
                "adviceOnlyAccept": advice_only_accept,
                "replenishInventory": replenish_inventory,
            },
            ensure_ascii=True,
        )
        output = _safe_agent_json(self.orchestrator_agent, prompt) or {}
        message = output.get("message")
        if message:
            return message

        if status == "Reject":
            return f"{greeting} {SORRY_MESSAGE}"
        if status == "Error":
            return f"{greeting} {TECHNICAL_MESSAGE}"
        if advice_only_accept and unavailable:
            return f"{greeting} The requested item is currently unavailable, but we can still help with pet-care guidance."
        base = f"{greeting} Your request has been processed."
        if replenish_inventory:
            base += " This item is popular and may take time to restock."
        return base

    def _pet_advice(self, intent: Dict[str, Any], pet_kb_id: str) -> str:
        query = intent.get("customerRequest") or intent.get("productQuery") or ""
        results = self._retrieve_kb(pet_kb_id, query, number_of_results=5, score=0.25)
        if not results:
            return ""
        snippets: List[str] = []
        for result in results[:2]:
            text = result.get("content", {}).get("text", "").strip()
            if text:
                snippets.append(text)
        advice = " ".join(snippets).strip()
        return advice[:600]

    def _format_final(
        self,
        status: str,
        message: str,
        customer_type: str,
        items: List[Dict[str, Any]],
        shipping_cost: float,
        subtotal: float,
        additional_discount: float,
        total: float,
        pet_advice: str,
    ) -> Dict[str, Any]:
        formatted = format_order_response(
            status=status,
            message=message,
            customer_type=customer_type,
            items_json=json.dumps(items),
            shipping_cost=shipping_cost,
            subtotal=subtotal,
            additional_discount=additional_discount,
            total=total,
            pet_advice=pet_advice,
        )
        parsed = _extract_tool_json(formatted)
        if parsed:
            return parsed
        return {"status": "Error", "message": TECHNICAL_MESSAGE}

    def __call__(self, prompt: str) -> Dict[str, Any]:
        product_kb_id = os.environ.get("KNOWLEDGE_BASE_1_ID")
        pet_care_kb_id = os.environ.get("KNOWLEDGE_BASE_2_ID")
        if not product_kb_id or not pet_care_kb_id:
            raise ValueError("Required environment variables KNOWLEDGE_BASE_1_ID and KNOWLEDGE_BASE_2_ID must be set")

        intent_prompt = f"Input:\n{prompt}"
        intent = _safe_agent_json(self.intent_agent, intent_prompt) or _intent_fallback(prompt)
        if not intent:
            intent = _intent_fallback(prompt)

        customer_ctx = self._resolve_customer(intent)

        if intent.get("isPromptInjection") or intent.get("isHarmful") or intent.get("isNonPetStore") or intent.get("isOutOfScopePet"):
            message = self._build_message(
                status="Reject",
                greeting=customer_ctx.greeting,
                customer_type=customer_ctx.customer_type,
                unavailable=False,
                advice_only_accept=False,
                replenish_inventory=False,
            )
            return self._format_final(
                status="Reject",
                message=message,
                customer_type=customer_ctx.customer_type,
                items=[],
                shipping_cost=0,
                subtotal=0,
                additional_discount=0,
                total=0,
                pet_advice="",
            )

        try:
            product = self._resolve_product(intent, product_kb_id)
        except Exception as exc:
            logger.error("Product resolution failed: %s", exc)
            message = self._build_message(
                status="Error",
                greeting=customer_ctx.greeting,
                customer_type=customer_ctx.customer_type,
                unavailable=False,
                advice_only_accept=False,
                replenish_inventory=False,
            )
            return self._format_final(
                status="Error",
                message=message,
                customer_type=customer_ctx.customer_type,
                items=[],
                shipping_cost=0,
                subtotal=0,
                additional_discount=0,
                total=0,
                pet_advice="",
            )

        explicit_code = intent.get("explicitProductCode")
        quantity = max(1, int(intent.get("quantity", 1)))
        asks_pet_care = bool(intent.get("asksPetCare"))

        if not product.get("found"):
            if explicit_code:
                message = self._build_message(
                    status="Error",
                    greeting=customer_ctx.greeting,
                    customer_type=customer_ctx.customer_type,
                    unavailable=False,
                    advice_only_accept=False,
                    replenish_inventory=False,
                )
                return self._format_final(
                    status="Error",
                    message=message,
                    customer_type=customer_ctx.customer_type,
                    items=[],
                    shipping_cost=0,
                    subtotal=0,
                    additional_discount=0,
                    total=0,
                    pet_advice="",
                )

            advice_only_accept = customer_ctx.customer_type == "Subscribed" and asks_pet_care
            pet_advice = self._pet_advice(intent, pet_care_kb_id) if advice_only_accept else ""
            status = "Accept" if advice_only_accept else "Reject"
            message = self._build_message(
                status=status,
                greeting=customer_ctx.greeting,
                customer_type=customer_ctx.customer_type,
                unavailable=True,
                advice_only_accept=advice_only_accept,
                replenish_inventory=False,
            )
            return self._format_final(
                status=status,
                message=message,
                customer_type=customer_ctx.customer_type,
                items=[],
                shipping_cost=0,
                subtotal=0,
                additional_discount=0,
                total=0,
                pet_advice=pet_advice if status == "Accept" else "",
            )

        product_code = product.get("product_code")
        inventory_data = _extract_tool_json(get_inventory(product_code)) if product_code else None
        if not inventory_data:
            message = self._build_message(
                status="Error",
                greeting=customer_ctx.greeting,
                customer_type=customer_ctx.customer_type,
                unavailable=False,
                advice_only_accept=False,
                replenish_inventory=False,
            )
            return self._format_final(
                status="Error",
                message=message,
                customer_type=customer_ctx.customer_type,
                items=[],
                shipping_cost=0,
                subtotal=0,
                additional_discount=0,
                total=0,
                pet_advice="",
            )

        stock = int(inventory_data.get("quantity", 0))
        reorder_level = int(inventory_data.get("reorder_level", 0))
        unavailable = stock <= 0 or bool(product.get("is_unavailable_hint"))

        if unavailable:
            advice_only_accept = customer_ctx.customer_type == "Subscribed" and asks_pet_care
            pet_advice = self._pet_advice(intent, pet_care_kb_id) if advice_only_accept else ""
            status = "Accept" if advice_only_accept else "Reject"
            message = self._build_message(
                status=status,
                greeting=customer_ctx.greeting,
                customer_type=customer_ctx.customer_type,
                unavailable=True,
                advice_only_accept=advice_only_accept,
                replenish_inventory=False,
            )
            return self._format_final(
                status=status,
                message=message,
                customer_type=customer_ctx.customer_type,
                items=[],
                shipping_cost=0,
                subtotal=0,
                additional_discount=0,
                total=0,
                pet_advice=pet_advice if status == "Accept" else "",
            )

        price = float(product.get("price"))
        pricing_input = json.dumps(
            [
                {
                    "product_id": product.get("product_id"),
                    "price": price,
                    "quantity": quantity,
                    "current_stock": stock,
                    "reorder_level": reorder_level,
                }
            ]
        )
        pricing_result = _extract_tool_json(calculate_order_pricing(pricing_input))
        if not pricing_result:
            message = self._build_message(
                status="Error",
                greeting=customer_ctx.greeting,
                customer_type=customer_ctx.customer_type,
                unavailable=False,
                advice_only_accept=False,
                replenish_inventory=False,
            )
            return self._format_final(
                status="Error",
                message=message,
                customer_type=customer_ctx.customer_type,
                items=[],
                shipping_cost=0,
                subtotal=0,
                additional_discount=0,
                total=0,
                pet_advice="",
            )

        items = pricing_result.get("items", [])
        replenish_inventory = any(bool(item.get("replenishInventory")) for item in items)
        pet_advice = (
            self._pet_advice(intent, pet_care_kb_id)
            if customer_ctx.customer_type == "Subscribed" and asks_pet_care
            else ""
        )
        message = self._build_message(
            status="Accept",
            greeting=customer_ctx.greeting,
            customer_type=customer_ctx.customer_type,
            unavailable=False,
            advice_only_accept=False,
            replenish_inventory=replenish_inventory,
        )
        return self._format_final(
            status="Accept",
            message=message,
            customer_type=customer_ctx.customer_type,
            items=items,
            shipping_cost=float(pricing_result.get("shippingCost", 0)),
            subtotal=float(pricing_result.get("subtotal", 0)),
            additional_discount=float(pricing_result.get("additionalDiscount", 0)),
            total=float(pricing_result.get("total", 0)),
            pet_advice=pet_advice,
        )
