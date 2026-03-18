"""
Pricing calculation tool for the output formatter agent.
Provides deterministic pricing calculations as a callable tool.
"""

from decimal import Decimal, ROUND_HALF_UP
from strands import tool


@tool
def calculate_order_pricing(
    customer_type: str,
    items: list[dict],
) -> dict:
    """
    Calculate complete order pricing with all business rules.

    Args:
        customer_type: "Subscribed" or "Guest"
        items: List of items, each with:
            - productId: str
            - price: float
            - quantity: int
            - current_stock: int (optional, for replenishment flag)
            - reorder_level: int (optional, for replenishment flag)

    Returns:
        Dictionary with all pricing fields:
        {
            "items": [{"productId", "price", "quantity", "bundleDiscount", "total", "replenishInventory"}, ...],
            "subtotal": float,
            "shippingCost": float,
            "additionalDiscount": float,
            "total": float
        }
    """
    FREE_SHIPPING_THRESHOLD = 300.0
    FLAT_SHIPPING_RATE = 14.95
    BUNDLE_DISCOUNT_RATE = 0.10

    calculated_items = []

    for item in items:
        product_id = item["productId"]
        price = float(item["price"])
        quantity = int(item["quantity"])
        current_stock = int(item.get("current_stock", 0))
        reorder_level = int(item.get("reorder_level", 0))

        price_dec = Decimal(str(price))
        quantity_dec = Decimal(str(quantity))

        if quantity > 1:
            bundle_discount = BUNDLE_DISCOUNT_RATE
            line_total_dec = price_dec * quantity_dec * Decimal("0.90")
        else:
            bundle_discount = 0.0
            line_total_dec = price_dec * quantity_dec

        line_total = float(
            line_total_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

        replenish_inventory = (current_stock - quantity) <= reorder_level

        calculated_items.append(
            {
                "productId": product_id,
                "price": price,
                "quantity": quantity,
                "bundleDiscount": bundle_discount,
                "total": line_total,
                "replenishInventory": replenish_inventory,
            }
        )

    subtotal_dec = sum(Decimal(str(item["total"])) for item in calculated_items)
    subtotal = float(subtotal_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    if subtotal >= FREE_SHIPPING_THRESHOLD:
        shipping_cost = 0.0
    else:
        shipping_cost = FLAT_SHIPPING_RATE

    if customer_type == "Subscribed":
        if subtotal < 100.0:
            additional_discount = 0.05
        elif subtotal < 200.0:
            additional_discount = 0.10
        else:
            additional_discount = 0.15
    else:
        additional_discount = 0.0

    subtotal_dec = Decimal(str(subtotal))
    discount_rate_dec = Decimal(str(additional_discount))
    shipping_dec = Decimal(str(shipping_cost))

    discount_amount_dec = subtotal_dec * discount_rate_dec
    subtotal_after_discount_dec = subtotal_dec - discount_amount_dec
    total_dec = subtotal_after_discount_dec + shipping_dec

    total = float(total_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return {
        "status": "success",
        "content": [
            {
                "text": f"""{{
    "items": {calculated_items},
    "subtotal": {subtotal},
    "shippingCost": {shipping_cost},
    "additionalDiscount": {additional_discount},
    "total": {total}
}}"""
            }
        ],
    }
