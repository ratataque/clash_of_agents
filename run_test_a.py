#!/usr/bin/env python3
"""Quick test: runs only Test A (Basic Pricing DD006, guest)"""

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
    print(f"=== Test A: Basic Pricing (DD006, guest) ===")
    print(f"Prompt: {PROMPT}")
    print(f"Started: {datetime.now().isoformat()}\n")

    response = invoke_agent(PROMPT)

    print(f"Raw response:\n{json.dumps(response, indent=2)}\n")

    checks = []
    checks.append(("status=Accept", response.get("status") == "Accept"))
    checks.append(("customerType=Guest", response.get("customerType") == "Guest"))
    checks.append(("has items", bool(response.get("items"))))
    checks.append(("shippingCost=14.95", response.get("shippingCost") == 14.95))

    items = response.get("items", [])
    if items:
        item = items[0]
        checks.append(("productId=DD006", item.get("productId") == "DD006"))
        checks.append(("price=54.99", item.get("price") == 54.99))

    print("Checks:")
    all_pass = True
    for name, passed in checks:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")
        if not passed:
            all_pass = False

    print(f"\n{'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
