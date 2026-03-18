import json
import logging
from strands import tool

logger = logging.getLogger(__name__)


@tool
def calculate_order_pricing(items: str) -> dict:
    """
    Calculate order pricing with bundle discounts, shipping, and additional discounts.

    Args:
        items: JSON string of items array. Each item has product_id, price, quantity, current_stock, reorder_level.

    Returns:
        Dictionary with pricing breakdown including items array, shipping cost, subtotal, and total.
    """
    logger.info(f"calculate_order_pricing called with items: {items}")

    try:
        items_list = json.loads(items)

        items_result = []
        total_item_sum = 0
        total_item_count = 0

        for item in items_list:
            product_id = item["product_id"]
            price = item["price"]
            quantity = item["quantity"]
            current_stock = item["current_stock"]
            reorder_level = item["reorder_level"]

            bundle_discount = 0.10 if quantity > 1 else 0

            if quantity == 1:
                item_total = round(price, 2)
            else:
                item_total = round(price + (price * 0.90 * (quantity - 1)), 2)

            remaining_stock = current_stock - quantity
            replenish_inventory = remaining_stock <= reorder_level

            items_result.append(
                {
                    "productId": product_id,
                    "price": price,
                    "quantity": quantity,
                    "bundleDiscount": bundle_discount,
                    "total": item_total,
                    "replenishInventory": replenish_inventory,
                }
            )

            total_item_sum += item_total
            total_item_count += quantity

        if total_item_sum >= 75:
            shipping_cost = 0
        elif total_item_count <= 2:
            shipping_cost = 14.95
        else:
            shipping_cost = 19.95

        additional_discount = 0.15 if total_item_sum > 300 else 0

        subtotal = round(total_item_sum + shipping_cost, 2)
        discount_amount = round(total_item_sum * additional_discount, 2)
        total = round(subtotal - discount_amount, 2)

        result_data = {
            "items": items_result,
            "shippingCost": shipping_cost,
            "subtotal": subtotal,
            "additionalDiscount": additional_discount,
            "total": total,
        }

        result = {"status": "success", "content": [{"text": json.dumps(result_data)}]}
        logger.info(f"calculate_order_pricing returning result: {result}")
        return result

    except Exception as e:
        logger.error(f"calculate_order_pricing() error: {str(e)}")
        result = {
            "status": "error",
            "content": [{"text": f"Failed to calculate pricing: {str(e)}"}],
        }
        logger.info(f"calculate_order_pricing returning result: {result}")
        return result
