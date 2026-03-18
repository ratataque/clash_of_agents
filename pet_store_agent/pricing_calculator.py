"""
Pricing Calculator Module

Deterministic pricing, discount, shipping, and inventory calculations
for the pet store agent. Extracted from LLM prompts for reliability,
testability, and cost reduction.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from decimal import Decimal, ROUND_HALF_UP
import json


@dataclass
class LineItem:
    """Single line item in an order"""

    productId: str
    price: float
    quantity: int
    bundleDiscount: float
    total: float
    replenishInventory: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "productId": self.productId,
            "price": self.price,
            "quantity": self.quantity,
            "bundleDiscount": self.bundleDiscount,
            "total": self.total,
            "replenishInventory": self.replenishInventory,
        }


@dataclass
class OrderCalculation:
    """Complete order calculation result"""

    customerType: str
    items: List[LineItem]
    subtotal: float
    shippingCost: float
    additionalDiscount: float
    total: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "customerType": self.customerType,
            "items": [item.to_dict() for item in self.items],
            "subtotal": self.subtotal,
            "shippingCost": self.shippingCost,
            "additionalDiscount": self.additionalDiscount,
            "total": self.total,
        }


class PricingCalculator:
    """
    Deterministic pricing calculator implementing all business rules.

    Business Rules:
    1. Line item total = price × quantity
    2. Bundle discount: 10% off if quantity > 1
    3. Subtotal = sum of all line item totals (after bundle discounts)
    4. Shipping: Free if subtotal >= $300, else $14.95 flat rate
    5. Subscriber discount (tiered):
        - subtotal < $100: 5%
        - $100 <= subtotal < $200: 10%
        - subtotal >= $200: 15%
    6. Total = subtotal - (subtotal × additionalDiscount) + shippingCost
    7. Inventory replenishment: flag if (stock - quantity) <= reorder_level
    """

    # Constants
    FREE_SHIPPING_THRESHOLD = 300.0
    FLAT_SHIPPING_RATE = 14.95
    BUNDLE_DISCOUNT_RATE = 0.10

    # Subscriber discount tiers: (threshold, discount_rate)
    SUBSCRIBER_DISCOUNT_TIERS = [
        (100.0, 0.05),  # < $100: 5%
        (200.0, 0.10),  # $100-$200: 10%
        (float("inf"), 0.15),  # >= $200: 15%
    ]

    @staticmethod
    def calculate_order(
        user_data: Optional[Dict[str, Any]],
        products: List[Dict[str, Any]],
    ) -> OrderCalculation:
        """
        Calculate complete order with all pricing rules.

        Args:
            user_data: User record with subscription_status field (or None)
            products: List of products, each with:
                - product_id: str
                - price: float
                - quantity: int
                - current_stock: int (optional)
                - reorder_level: int (optional)

        Returns:
            OrderCalculation with all pricing fields computed
        """
        # 1. Determine customer type
        customer_type = PricingCalculator._determine_customer_type(user_data)

        # 2. Calculate line items with bundle discounts
        items = []
        for product in products:
            line_item = PricingCalculator._calculate_line_item(product)
            items.append(line_item)

        # 3. Calculate subtotal (sum of line item totals after bundle discounts)
        subtotal = PricingCalculator._calculate_subtotal(items)

        # 4. Calculate shipping
        shipping_cost = PricingCalculator._calculate_shipping(subtotal)

        # 5. Calculate subscriber discount
        additional_discount = PricingCalculator._calculate_subscriber_discount(
            subtotal, customer_type
        )

        # 6. Calculate final total
        total = PricingCalculator._calculate_total(
            subtotal, additional_discount, shipping_cost
        )

        return OrderCalculation(
            customerType=customer_type,
            items=items,
            subtotal=subtotal,
            shippingCost=shipping_cost,
            additionalDiscount=additional_discount,
            total=total,
        )

    @staticmethod
    def _determine_customer_type(user_data: Optional[Dict[str, Any]]) -> str:
        """
        Determine customer type from user data.

        Rules:
        - Subscribed: user exists AND subscription_status="active"
        - Guest: no user, or expired/inactive subscription

        Args:
            user_data: User record or None

        Returns:
            "Subscribed" or "Guest"
        """
        if not user_data:
            return "Guest"

        subscription_status = user_data.get("subscription_status", "").lower()
        return "Subscribed" if subscription_status == "active" else "Guest"

    @staticmethod
    def _calculate_line_item(product: Dict[str, Any]) -> LineItem:
        """
        Calculate single line item with bundle discount and replenishment flag.

        Args:
            product: Dict with product_id, price, quantity, current_stock, reorder_level

        Returns:
            LineItem with all fields calculated
        """
        product_id = product["product_id"]
        price = float(product["price"])
        quantity = int(product["quantity"])
        current_stock = int(product.get("current_stock", 0))
        reorder_level = int(product.get("reorder_level", 0))

        # Use Decimal for precise money arithmetic
        price_dec = Decimal(str(price))
        quantity_dec = Decimal(str(quantity))

        # Bundle discount: 10% off if quantity > 1
        if quantity > 1:
            bundle_discount = PricingCalculator.BUNDLE_DISCOUNT_RATE
            line_total_dec = price_dec * quantity_dec * Decimal("0.90")
        else:
            bundle_discount = 0.0
            line_total_dec = price_dec * quantity_dec

        # Round to 2 decimal places for currency
        line_total = float(
            line_total_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

        # Inventory replenishment flag
        replenish_inventory = (current_stock - quantity) <= reorder_level

        return LineItem(
            productId=product_id,
            price=price,
            quantity=quantity,
            bundleDiscount=bundle_discount,
            total=line_total,
            replenishInventory=replenish_inventory,
        )

    @staticmethod
    def _calculate_subtotal(items: List[LineItem]) -> float:
        """
        Calculate subtotal (sum of all line item totals after bundle discounts).

        Args:
            items: List of LineItem objects

        Returns:
            Subtotal as float
        """
        subtotal_dec = sum(Decimal(str(item.total)) for item in items)
        return float(subtotal_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _calculate_shipping(subtotal: float) -> float:
        """
        Calculate shipping cost.

        Rules:
        - Free shipping if subtotal >= $300
        - Otherwise $14.95 flat rate

        Args:
            subtotal: Order subtotal

        Returns:
            Shipping cost as float
        """
        if subtotal >= PricingCalculator.FREE_SHIPPING_THRESHOLD:
            return 0.0
        else:
            return PricingCalculator.FLAT_SHIPPING_RATE

    @staticmethod
    def _calculate_subscriber_discount(subtotal: float, customer_type: str) -> float:
        """
        Calculate subscriber discount rate.

        Rules (only for Subscribed customers):
        - subtotal < $100: 5%
        - $100 <= subtotal < $200: 10%
        - subtotal >= $200: 15%
        - Guest customers: 0%

        Args:
            subtotal: Order subtotal
            customer_type: "Subscribed" or "Guest"

        Returns:
            Discount rate (0.0 to 0.15)
        """
        if customer_type != "Subscribed":
            return 0.0

        for threshold, discount_rate in PricingCalculator.SUBSCRIBER_DISCOUNT_TIERS:
            if subtotal < threshold:
                return discount_rate

        # Should never reach here due to inf threshold, but safety fallback
        return 0.15

    @staticmethod
    def _calculate_total(
        subtotal: float, additional_discount: float, shipping_cost: float
    ) -> float:
        """
        Calculate final total.

        Formula: total = subtotal - (subtotal × additionalDiscount) + shippingCost

        Args:
            subtotal: Order subtotal
            additional_discount: Discount rate (0.0 to 0.15)
            shipping_cost: Shipping cost

        Returns:
            Final total as float
        """
        subtotal_dec = Decimal(str(subtotal))
        discount_rate_dec = Decimal(str(additional_discount))
        shipping_dec = Decimal(str(shipping_cost))

        # Apply subscriber discount
        discount_amount_dec = subtotal_dec * discount_rate_dec
        subtotal_after_discount_dec = subtotal_dec - discount_amount_dec

        # Add shipping
        total_dec = subtotal_after_discount_dec + shipping_dec

        return float(total_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# Convenience functions for common operations


def calculate_order_from_retrieval(
    retrieval_data: Dict[str, Any],
) -> Optional[OrderCalculation]:
    """
    Helper to extract products and user from retrieval data and calculate order.

    Args:
        retrieval_data: Data from data_retriever agent with structure:
            {
                "user": {"found": bool, "data": {...}},
                "products": [...],
                "inventory": [...]
            }

    Returns:
        OrderCalculation or None if insufficient data
    """
    # Extract user data
    user_info = retrieval_data.get("user", {})
    user_data = user_info.get("data") if user_info.get("found") else None

    # Extract products (would need parsing logic specific to your retrieval format)
    # This is a placeholder - you'll need to implement actual parsing
    products = []  # TODO: Parse from retrieval_data

    if not products:
        return None

    return PricingCalculator.calculate_order(user_data, products)


def should_replenish_inventory(
    current_stock: int, quantity: int, reorder_level: int
) -> bool:
    """
    Standalone helper to check if inventory should be replenished.

    Args:
        current_stock: Current stock level
        quantity: Quantity being ordered
        reorder_level: Reorder threshold

    Returns:
        True if replenishment needed
    """
    return (current_stock - quantity) <= reorder_level
