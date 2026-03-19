#!/usr/bin/env python3
"""
Probe all products via inventory Lambda and product KB to find items with missing data.
Usage: python probe_products.py
"""

import boto3
import json
import os
import sys

# Load .env manually
env_path = os.path.join(os.path.dirname(__file__), "pet_store_agent", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

INVENTORY_LAMBDA = os.environ.get("SYSTEM_FUNCTION_1_NAME")
KB_ID = os.environ.get("KNOWLEDGE_BASE_1_ID")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# All known product codes
KNOWN_CODES = [
    "CM001",
    "DB002",
    "PT003",
    "DD006",
    "FF008",
    "CC009",
    "BP010",
    "LL011",
    "PP012",
    "PM015",
]

lambda_client = boto3.client("lambda", region_name=REGION)
kb_client = boto3.client("bedrock-agent-runtime", region_name=REGION)


def call_inventory(product_code=None):
    """Call inventory Lambda"""
    payload = {"function": "getInventory", "parameters": []}
    if product_code:
        payload["parameters"].append({"name": "product_code", "value": product_code})

    try:
        response = lambda_client.invoke(
            FunctionName=INVENTORY_LAMBDA,
            Payload=json.dumps(payload),
        )
        lambda_response = json.loads(response["Payload"].read())
        actual_data = json.loads(
            lambda_response["response"]["functionResponse"]["responseBody"]["TEXT"][
                "body"
            ]
        )
        return actual_data
    except Exception as e:
        return {"error": str(e)}


def query_kb(query_text):
    """Query product knowledge base"""
    try:
        response = kb_client.retrieve(
            retrievalQuery={"text": query_text},
            knowledgeBaseId=KB_ID,
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": 5},
            },
        )
        results = response.get("retrievalResults", [])
        return [
            {
                "score": r.get("score", 0),
                "text": r.get("content", {}).get("text", "")[:300],
            }
            for r in results
        ]
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 70)
    print("PRODUCT DATA PROBE")
    print("=" * 70)

    # Step 1: Get ALL inventory (no filter)
    print("\n--- Step 1: Full inventory listing ---")
    all_inventory = call_inventory()
    print(json.dumps(all_inventory, indent=2, default=str))

    # Step 2: Query each known product code individually
    print("\n--- Step 2: Individual product inventory lookups ---")
    for code in KNOWN_CODES:
        print(f"\n  [{code}]")
        data = call_inventory(code)
        print(f"    {json.dumps(data, indent=2, default=str)}")

        # Check for missing fields
        if isinstance(data, dict) and "error" not in data:
            expected_fields = [
                "product_code",
                "name",
                "quantity",
                "reorder_level",
                "status",
            ]
            missing = [f for f in expected_fields if f not in data or data[f] is None]
            if missing:
                print(f"    ⚠️  MISSING FIELDS: {missing}")
            else:
                print(f"    ✅ All expected inventory fields present")
        elif isinstance(data, list):
            # Sometimes returns a list
            for item in data:
                expected_fields = [
                    "product_code",
                    "name",
                    "quantity",
                    "reorder_level",
                    "status",
                ]
                missing = [
                    f for f in expected_fields if f not in item or item[f] is None
                ]
                if missing:
                    print(
                        f"    ⚠️  MISSING FIELDS in {item.get('product_code', '?')}: {missing}"
                    )

    # Step 3: Query KB for each product code
    print("\n\n--- Step 3: Knowledge Base lookups ---")
    for code in KNOWN_CODES:
        print(f"\n  [{code}] KB query:")
        results = query_kb(code)
        if isinstance(results, dict) and "error" in results:
            print(f"    ❌ Error: {results['error']}")
        elif not results:
            print(f"    ⚠️  NO KB RESULTS for {code}")
        else:
            for r in results[:2]:  # Show top 2
                print(f"    Score: {r['score']:.4f}")
                print(f"    Text: {r['text'][:200]}...")

            # Check if price is mentioned
            all_text = " ".join(r["text"] for r in results)
            has_price = "$" in all_text or "price" in all_text.lower()
            has_pet_type = any(
                w in all_text.lower() for w in ["cat", "dog", "both", "pet type"]
            )
            print(f"    Price mentioned: {'✅' if has_price else '⚠️ NO'}")
            print(f"    Pet type mentioned: {'✅' if has_pet_type else '⚠️ NO'}")

    # Step 4: Try some non-existent / edge case codes
    print("\n\n--- Step 4: Edge case product codes ---")
    edge_codes = ["XYZ999", "PP012", "LL011", "TEST001", "DD007"]
    for code in edge_codes:
        print(f"\n  [{code}] Inventory:")
        data = call_inventory(code)
        print(f"    {json.dumps(data, indent=2, default=str)}")


if __name__ == "__main__":
    main()
