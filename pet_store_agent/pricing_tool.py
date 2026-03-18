import json
from typing import Dict, List

from strands import tool


def _round_money(value: float) -> float:
    return round(value + 1e-9, 2)


def _item_total(price: float, quantity: int) -> float:
    if quantity <= 1:
        return _round_money(price)
    discounted_units = max(quantity - 1, 0)
    total = price + (discounted_units * price * 0.9)
    return _round_money(total)


def _shipping_cost(subtotal: float, total_quantity: int) -> float:
    if subtotal >= 300:
        return 0.0
    return 14.95


def calculate_pricing_data(items: List[Dict]) -> Dict:
    if not items:
        raise ValueError("At least one item is required for pricing")

    normalized_items: List[Dict] = []
    subtotal = 0.0
    total_quantity = 0

    for item in items:
        product_id = item["productId"]
        price = float(item["price"])
        quantity = int(item["quantity"])
        if quantity <= 0:
            raise ValueError(f"Invalid quantity for {product_id}: {quantity}")

        line_total = _item_total(price, quantity)
        subtotal += line_total
        total_quantity += quantity

        normalized_items.append(
            {
                "productId": product_id,
                "price": _round_money(price),
                "quantity": quantity,
                "bundleDiscount": 0.10 if quantity > 1 else 0.0,
                "total": line_total,
                "replenishInventory": bool(item.get("replenishInventory", False)),
            }
        )

    subtotal = _round_money(subtotal)
    additional_discount = 0.15 if subtotal > 300 else 0.0
    discounted_subtotal = _round_money(subtotal * (1 - additional_discount))
    shipping_cost = _shipping_cost(subtotal, total_quantity)
    total = _round_money(discounted_subtotal + shipping_cost)

    return {
        "items": normalized_items,
        "subtotal": subtotal,
        "additionalDiscount": additional_discount,
        "shippingCost": shipping_cost,
        "total": total,
    }


@tool
def calculate_pricing(items_json: str) -> Dict:
    items = json.loads(items_json)
    pricing = calculate_pricing_data(items)
    return {"status": "success", "content": [{"text": json.dumps(pricing)}]}
