#!/usr/bin/env bash
set -euo pipefail

# Notebook-style AgentCore runtime test
# Usage:
#   ./test_runtime.sh [agent_dir] [prompt]
# Examples:
#   ./test_runtime.sh pet_store_agent
#   ./test_runtime.sh claim_inquiry_agent "Patient asks about Adalimumab coverage"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: ./test_runtime.sh [agent_dir] [prompt]"
  exit 0
fi

agent_dir="${1:-pet_store_agent}"
prompt="${2:-A new user is asking about the price of Doggy Delights}"

if [[ ! -d "$agent_dir" ]]; then
  echo "Error: agent directory not found: $agent_dir" >&2
  exit 1
fi

yaml_file="$agent_dir/.bedrock_agentcore.yaml"
if [[ ! -f "$yaml_file" ]]; then
  echo "Error: runtime metadata file not found: $yaml_file" >&2
  echo "Run deploy first (for example: ./deploy_with_env.sh $agent_dir)." >&2
  exit 1
fi

python_bin="python"
if [[ -x ".venv/bin/python" ]]; then
  python_bin=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  python_bin="python3"
fi

"$python_bin" - "$yaml_file" "$prompt" <<'PY'
import json
import sys
import uuid
from pathlib import Path

import boto3
import yaml
from botocore.exceptions import UnknownServiceError

yaml_file = Path(sys.argv[1])
prompt = sys.argv[2]

data = yaml.safe_load(yaml_file.read_text())
default_agent = data.get("default_agent")
if not default_agent or default_agent not in data.get("agents", {}):
    raise SystemExit(f"Error: default agent missing/invalid in {yaml_file}")

agent_cfg = data["agents"][default_agent]
bedrock_cfg = agent_cfg.get("bedrock_agentcore", {})
agent_id = bedrock_cfg.get("agent_id")
agent_arn = bedrock_cfg.get("agent_arn")
region = agent_cfg.get("aws", {}).get("region", "us-east-1")

if not agent_id or not agent_arn:
    raise SystemExit("Error: agent_id/agent_arn not found in .bedrock_agentcore.yaml (deploy may not have completed)")

print(f"Agent ID: {agent_id}")
print(f"Agent ARN: {agent_arn}")
print(f"Region: {region}")

try:
    control_client = boto3.client("bedrock-agentcore-control", region_name=region)
    status = control_client.get_agent_runtime(agentRuntimeId=agent_id).get("status")
    print(f"Runtime status: {status}")
    if status != "READY":
        raise SystemExit(f"Error: runtime is not READY (status={status})")
except UnknownServiceError:
    print("Runtime status check skipped: local boto3/botocore lacks 'bedrock-agentcore-control'.")
    print("Tip: use repo venv (`source .venv/bin/activate`) or upgrade boto3/botocore.")

try:
    data_client = boto3.client("bedrock-agentcore", region_name=region)
except UnknownServiceError:
    raise SystemExit(
        "Error: local boto3/botocore lacks 'bedrock-agentcore'. "
        "Activate the repo venv (`source .venv/bin/activate`) or upgrade boto3/botocore."
    )
invoke_response = data_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    qualifier="DEFAULT",
    traceId=str(uuid.uuid4()),
    contentType="application/json",
    payload=json.dumps({"prompt": prompt}),
)

content_type = invoke_response.get("contentType", "")
print(f"Content-Type: {content_type}")
print("Response:")

if "text/event-stream" in content_type:
    output = []
    for line in invoke_response["response"].iter_lines(chunk_size=1):
        if not line:
            continue
        raw = line.decode("utf-8")
        if raw.startswith("data: "):
            raw = raw[6:]
            output.append(raw)
    print("\n".join(output))
else:
    body = invoke_response.get("response")
    if hasattr(body, "read"):
        print(body.read().decode("utf-8"))
    else:
        print(body)
PY
