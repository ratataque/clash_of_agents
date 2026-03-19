#!/usr/bin/env python3
"""
Pricing unit tests — verifies calculate_order_pricing against business rules:

Bundle: 10% off each additional unit (first at regular price)
Shipping:
  - items_total >= $75 → free
  - items_total < $75, total_qty <= 2 → $14.95
  - items_total < $75, total_qty >= 3 → $19.95
Discount: 15% off items_total when items_total > $300
Subtotal: items_total + shipping
Total: subtotal - (items_total * 0.15) if discount applies, else subtotal
"""

import json
import sys

sys.path.insert(0, "pet_store_agent")
from pricing import calculate_order_pricing


def make_item(product_id, price, quantity, current_stock=100, reorder_level=10):
    return {
        "product_id": product_id,
        "price": price,
        "quantity": quantity,
        "current_stock": current_stock,
        "reorder_level": reorder_level,
    }


def call_pricing(items_list):
    result = calculate_order_pricing(json.dumps(items_list))
    data = json.loads(result["content"][0]["text"])
    return data


def assert_close(actual, expected, label, tol=0.01):
    ok = abs(actual - expected) < tol
    icon = "✅" if ok else "❌"
    print(f"  {icon} {label}: expected={expected}, got={actual}")
    return ok


def run_test(name, items_list, expected):
    print(f"\n--- {name} ---")
    data = call_pricing(items_list)
    all_pass = True

    for i, exp_item in enumerate(expected.get("items", [])):
        actual_item = data["items"][i]
        for key in exp_item:
            ok = (
                abs(actual_item[key] - exp_item[key]) < 0.01
                if isinstance(exp_item[key], float)
                else actual_item[key] == exp_item[key]
            )
            icon = "✅" if ok else "❌"
            print(
                f"  {icon} items[{i}].{key}: expected={exp_item[key]}, got={actual_item[key]}"
            )
            if not ok:
                all_pass = False

    for key in ["shippingCost", "subtotal", "additionalDiscount", "total"]:
        if key in expected:
            if not assert_close(data[key], expected[key], key):
                all_pass = False

    status = "PASS" if all_pass else "FAIL"
    print(f"  → {status}")
    return all_pass


# ─── Test cases ──────────────────────────────────────────────────────────────

TESTS = {}


def test_single_item_qty1():
    """DD006 $54.99 × 1 — no bundle, shipping $14.95"""
    return run_test(
        "Single item qty=1 (DD006)",
        [make_item("DD006", 54.99, 1)],
        {
            "items": [{"bundleDiscount": 0, "total": 54.99}],
            "shippingCost": 14.95,
            "subtotal": 69.94,
            "additionalDiscount": 0,
            "total": 69.94,
        },
    )


TESTS["single_qty1"] = test_single_item_qty1


def test_single_item_qty2():
    """BP010 $16.99 × 2 — bundle 10%, shipping $14.95 (qty=2, total=32.28 < 75)"""
    # first at full: 16.99, second at 90%: 16.99 * 0.90 = 15.291
    # item_total = 16.99 + 15.291 = 32.281 → round = 32.28
    return run_test(
        "Single item qty=2 (BP010)",
        [make_item("BP010", 16.99, 2)],
        {
            "items": [{"bundleDiscount": 0.10, "total": 32.28}],
            "shippingCost": 14.95,
            "subtotal": 47.23,
            "additionalDiscount": 0,
            "total": 47.23,
        },
    )


TESTS["single_qty2"] = test_single_item_qty2


def test_single_item_qty3_under75():
    """PM015 $27.99 × 3 — bundle 10%, qty=3, total < 75 → shipping $19.95"""
    # first: 27.99, additional 2 at 90%: 27.99 * 0.90 * 2 = 50.382
    # item_total = 27.99 + 50.382 = 78.372 → round = 78.37
    # 78.37 >= 75 → FREE shipping actually!
    # Let's use a cheaper item: FF008 $9.99 × 3
    # first: 9.99, additional 2 at 90%: 9.99 * 0.90 * 2 = 17.982
    # item_total = 9.99 + 17.982 = 27.972 → round = 27.97
    # 27.97 < 75, qty=3 >= 3 → shipping = 19.95
    return run_test(
        "Single item qty=3 under $75 (FF008 $9.99)",
        [make_item("FF008", 9.99, 3)],
        {
            "items": [{"bundleDiscount": 0.10, "total": 27.97}],
            "shippingCost": 19.95,
            "subtotal": 47.92,
            "additionalDiscount": 0,
            "total": 47.92,
        },
    )


TESTS["single_qty3_under75"] = test_single_item_qty3_under75


def test_free_shipping_boundary_at_75():
    """Item total exactly $75.00 → free shipping (>= 75)"""
    # Use price=$75.00, qty=1
    return run_test(
        "Free shipping boundary: items_total = $75.00",
        [make_item("TEST", 75.00, 1)],
        {
            "items": [{"bundleDiscount": 0, "total": 75.00}],
            "shippingCost": 0,
            "subtotal": 75.00,
            "additionalDiscount": 0,
            "total": 75.00,
        },
    )


TESTS["shipping_boundary_75"] = test_free_shipping_boundary_at_75


def test_shipping_just_below_75():
    """Item total $74.99 → NOT free, qty=1 → $14.95"""
    return run_test(
        "Shipping just below $75: items_total = $74.99",
        [make_item("TEST", 74.99, 1)],
        {
            "items": [{"bundleDiscount": 0, "total": 74.99}],
            "shippingCost": 14.95,
            "subtotal": 89.94,
            "additionalDiscount": 0,
            "total": 89.94,
        },
    )


TESTS["shipping_below_75"] = test_shipping_just_below_75


def test_shipping_qty2_under75():
    """2 different items, total qty=2, items_total < 75 → $14.95"""
    # FF008 $9.99 × 1 + CC009 $11.99 × 1 = 21.98
    return run_test(
        "2 items qty=1 each, under $75 → $14.95",
        [make_item("FF008", 9.99, 1), make_item("CC009", 11.99, 1)],
        {
            "items": [
                {"bundleDiscount": 0, "total": 9.99},
                {"bundleDiscount": 0, "total": 11.99},
            ],
            "shippingCost": 14.95,
            "subtotal": 36.93,
            "additionalDiscount": 0,
            "total": 36.93,
        },
    )


TESTS["shipping_2items_under75"] = test_shipping_qty2_under75


def test_shipping_qty3_mixed_under75():
    """Mixed items, total qty=3, items_total < 75 → $19.95"""
    # FF008 $9.99 × 2 + CC009 $11.99 × 1
    # FF008: 9.99 + 9.99*0.90 = 9.99 + 8.991 = 18.981 → 18.98
    # CC009: 11.99
    # total_items = 18.98 + 11.99 = 30.97, qty = 3
    return run_test(
        "Mixed items, total qty=3, under $75 → $19.95",
        [make_item("FF008", 9.99, 2), make_item("CC009", 11.99, 1)],
        {
            "items": [
                {"bundleDiscount": 0.10, "total": 18.98},
                {"bundleDiscount": 0, "total": 11.99},
            ],
            "shippingCost": 19.95,
            "subtotal": 50.92,
            "additionalDiscount": 0,
            "total": 50.92,
        },
    )


TESTS["shipping_3items_mixed"] = test_shipping_qty3_mixed_under75


def test_discount_boundary_at_300():
    """Items total exactly $300.00 → NO discount (spec says OVER $300, code uses > 300)"""
    return run_test(
        "Discount boundary: items_total = $300.00 → NO 15% discount",
        [make_item("TEST", 300.00, 1)],
        {
            "items": [{"bundleDiscount": 0, "total": 300.00}],
            "shippingCost": 0,
            "subtotal": 300.00,
            "additionalDiscount": 0,
            "total": 300.00,
        },
    )


TESTS["discount_boundary_300"] = test_discount_boundary_at_300


def test_discount_just_above_300():
    """Items total $300.01 → 15% discount kicks in"""
    # discount = 300.01 * 0.15 = 45.0015 → round = 45.00
    # subtotal = 300.01, total = 300.01 - 45.00 = 255.01
    return run_test(
        "Discount just above $300: items_total = $300.01",
        [make_item("TEST", 300.01, 1)],
        {
            "items": [{"bundleDiscount": 0, "total": 300.01}],
            "shippingCost": 0,
            "subtotal": 300.01,
            "additionalDiscount": 0.15,
            "total": 255.01,
        },
    )


TESTS["discount_above_300"] = test_discount_just_above_300


def test_bulk_order_over_300():
    """DD006 $54.99 × 10 — bundle + free shipping + 15% discount"""
    # first: 54.99, additional 9 at 90%: 54.99 * 0.90 * 9 = 445.419
    # item_total = 54.99 + 445.419 = 500.409 → round = 500.41
    # 500.41 >= 75 → free shipping
    # 500.41 > 300 → 15% discount
    # subtotal = 500.41
    # discount = 500.41 * 0.15 = 75.0615 → round = 75.06
    # total = 500.41 - 75.06 = 425.35
    return run_test(
        "Bulk order over $300 (DD006 × 10)",
        [make_item("DD006", 54.99, 10)],
        {
            "items": [{"bundleDiscount": 0.10, "total": 500.41}],
            "shippingCost": 0,
            "subtotal": 500.41,
            "additionalDiscount": 0.15,
            "total": 425.35,
        },
    )


TESTS["bulk_over_300"] = test_bulk_order_over_300


def test_bulk_pt003_qty10():
    """PT003 $15.99 × 10 — matches test K"""
    # first: 15.99, additional 9 at 90%: 15.99 * 0.90 * 9 = 129.519
    # item_total = 15.99 + 129.519 = 145.509 → round = 145.51
    # 145.51 >= 75 → free shipping
    # 145.51 < 300 → no discount
    return run_test(
        "PT003 × 10 (test K scenario)",
        [make_item("PT003", 15.99, 10)],
        {
            "items": [{"bundleDiscount": 0.10, "total": 145.51}],
            "shippingCost": 0,
            "subtotal": 145.51,
            "additionalDiscount": 0,
            "total": 145.51,
        },
    )


TESTS["pt003_qty10"] = test_bulk_pt003_qty10


def test_pm015_qty1():
    """PM015 $27.99 × 1 — matches test E scenario"""
    return run_test(
        "PM015 × 1 (test E scenario)",
        [make_item("PM015", 27.99, 1)],
        {
            "items": [{"bundleDiscount": 0, "total": 27.99}],
            "shippingCost": 14.95,
            "subtotal": 42.94,
            "additionalDiscount": 0,
            "total": 42.94,
        },
    )


TESTS["pm015_qty1"] = test_pm015_qty1


def test_multi_item_order():
    """CM001 × 2 + DB002 × 1 — matches test T scenario"""
    # CM001 $24.99 × 2: 24.99 + 24.99*0.90 = 24.99 + 22.491 = 47.481 → 47.48
    # DB002 $12.99 × 1: 12.99
    # items_total = 47.48 + 12.99 = 60.47, qty = 3
    # 60.47 < 75, qty=3 → shipping = 19.95
    # subtotal = 60.47 + 19.95 = 80.42
    # 60.47 < 300 → no discount
    # total = 80.42
    return run_test(
        "CM001 × 2 + DB002 × 1 (test T scenario)",
        [make_item("CM001", 24.99, 2), make_item("DB002", 12.99, 1)],
        {
            "items": [
                {"bundleDiscount": 0.10, "total": 47.48},
                {"bundleDiscount": 0, "total": 12.99},
            ],
            "shippingCost": 19.95,
            "subtotal": 80.42,
            "additionalDiscount": 0,
            "total": 80.42,
        },
    )


TESTS["multi_item_t"] = test_multi_item_order


def test_bp010_qty2():
    """BP010 $16.99 × 2 — matches test B scenario"""
    # first: 16.99, second at 90%: 15.291
    # item_total = 32.281 → round = 32.28
    # 32.28 < 75, qty=2 → shipping = 14.95
    # subtotal = 32.28 + 14.95 = 47.23
    return run_test(
        "BP010 × 2 (test B scenario)",
        [make_item("BP010", 16.99, 2)],
        {
            "items": [{"bundleDiscount": 0.10, "total": 32.28}],
            "shippingCost": 14.95,
            "subtotal": 47.23,
            "additionalDiscount": 0,
            "total": 47.23,
        },
    )


TESTS["bp010_qty2"] = test_bp010_qty2


def test_replenish_inventory():
    """Verify replenishInventory flag: remaining_stock <= reorder_level"""
    data = call_pricing([make_item("X", 10.00, 1, current_stock=50, reorder_level=10)])
    ok1 = data["items"][0]["replenishInventory"] == False  # 50-1=49 > 10

    data2 = call_pricing([make_item("Y", 10.00, 5, current_stock=15, reorder_level=10)])
    ok2 = data2["items"][0]["replenishInventory"] == True  # 15-5=10 <= 10

    data3 = call_pricing([make_item("Z", 10.00, 1, current_stock=11, reorder_level=10)])
    ok3 = data3["items"][0]["replenishInventory"] == True  # 11-1=10 <= 10

    print("\n--- Replenish inventory flag ---")
    icon1 = "✅" if ok1 else "❌"
    icon2 = "✅" if ok2 else "❌"
    icon3 = "✅" if ok3 else "❌"
    print(f"  {icon1} stock=50, qty=1, reorder=10 → replenish=False (49 > 10)")
    print(f"  {icon2} stock=15, qty=5, reorder=10 → replenish=True (10 <= 10)")
    print(f"  {icon3} stock=11, qty=1, reorder=10 → replenish=True (10 <= 10)")
    all_pass = ok1 and ok2 and ok3
    print(f"  → {'PASS' if all_pass else 'FAIL'}")
    return all_pass


TESTS["replenish"] = test_replenish_inventory


def main():
    args = sys.argv[1:]

    if args:
        tests_to_run = {k: v for k, v in TESTS.items() if k in args}
        if not tests_to_run:
            print(f"Unknown test(s): {args}")
            print(f"Available: {', '.join(TESTS.keys())}")
            sys.exit(1)
    else:
        tests_to_run = TESTS

    results = {}
    for name, fn in tests_to_run.items():
        results[name] = fn()

    print("\n" + "=" * 50)
    all_pass = True
    for name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_pass = False
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    print("=" * 50)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
