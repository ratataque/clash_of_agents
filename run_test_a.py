#!/usr/bin/env python3
"""Regression tests: Test A (Basic Pricing DD006, guest) and Test B (Bundle Deal with pet advice)"""

import boto3
import json
import uuid
import sys
import os
from datetime import datetime

AGENT_RUNTIME_ARN = os.environ.get(
    "AGENT_RUNTIME_ARN",
    "arn:aws:bedrock-agentcore:us-east-1:799631972281:runtime/PetStoreAgentRuntime-dQAchb62bb",
)

PROMPT = "A new user is asking about the price of Doggy Delights?"

EXPECTED = {
    "status": "Accept",
    "customerType": "Guest",
    "has_items": True,
    "shippingCost": 14.95,
}


def invoke_agent(prompt):
    client = boto3.client("bedrock-agentcore")
    try:
        invoke_response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            qualifier="DEFAULT",
            traceId=str(uuid.uuid4()),
            contentType="application/json",
            payload=json.dumps({"prompt": prompt}),
        )

        if "text/event-stream" in invoke_response.get("contentType", ""):
            content = []
            for line in invoke_response["response"].iter_lines(chunk_size=1):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                    content.append(line)
            response_text = "\n".join(content)
        else:
            events = []
            for event in invoke_response.get("response", []):
                events.append(event)
            combined_content = ""
            for event in events:
                combined_content += event.decode("utf-8")
            response_text = combined_content

        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            return parsed
        except json.JSONDecodeError:
            import re

            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return {"raw_response": response_text, "parse_error": True}

    except Exception as e:
        return {"error": str(e), "status": "Error"}


def main():
    # Test A
    print(f"=== Test A: Basic Pricing (DD006, guest) ===")
    print(f"Prompt: {PROMPT}")
    print(f"Started: {datetime.now().isoformat()}\n")

    response_a = invoke_agent(PROMPT)

    print(f"Raw response:\n{json.dumps(response_a, indent=2)}\n")

    checks_a = []
    checks_a.append(("status=Accept", response_a.get("status") == "Accept"))
    checks_a.append(("customerType=Guest", response_a.get("customerType") == "Guest"))
    checks_a.append(("has items", bool(response_a.get("items"))))
    checks_a.append(("shippingCost=14.95", response_a.get("shippingCost") == 14.95))

    items_a = response_a.get("items", [])
    if items_a:
        item = items_a[0]
        checks_a.append(("productId=DD006", item.get("productId") == "DD006"))
        checks_a.append(("price=54.99", item.get("price") == 54.99))

    print("Checks:")
    all_pass_a = True
    for name, passed in checks_a:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_pass_a = False

    result_a = "PASS" if all_pass_a else "FAIL"
    print(f"\nTest A: {result_a}\n")

    # Test B
    prompt_b = "CustomerId: usr_001\nCustomerRequest: I'm interested in purchasing two water bottles under your bundle deal. Would these bottles also be suitable for bathing my Chihuahua?"
    print(f"=== Test B: Bundle Deal with Pet Advice ===")
    print(f"Prompt: {prompt_b}")
    print(f"Started: {datetime.now().isoformat()}\n")

    response_b = invoke_agent(prompt_b)

    print(f"Raw response:\n{json.dumps(response_b, indent=2)}\n")

    checks_b = []
    checks_b.append(("status=Accept", response_b.get("status") == "Accept"))
    checks_b.append(
        ("customerType=Subscribed", response_b.get("customerType") == "Subscribed")
    )
    checks_b.append(("has items", bool(response_b.get("items"))))
    checks_b.append(("has petAdvice", len(response_b.get("petAdvice", "")) > 10))

    items_b = response_b.get("items", [])
    if items_b:
        item = items_b[0]
        checks_b.append(("bundleDiscount=0.10", item.get("bundleDiscount") == 0.10))
        checks_b.append(("productId=BP010", item.get("productId") == "BP010"))

    print("Checks:")
    all_pass_b = True
    for name, passed in checks_b:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_pass_b = False

    result_b = "PASS" if all_pass_b else "FAIL"
    print(f"\nTest B: {result_b}\n")

    # Summary
    print("=" * 50)
    print(f"Test A: {result_a}")
    print(f"Test B: {result_b}")
    overall = "PASS" if (all_pass_a and all_pass_b) else "FAIL"
    print(f"Overall: {overall}")
    print("=" * 50)

    return 0 if (all_pass_a and all_pass_b) else 1


if __name__ == "__main__":
    sys.exit(main())
