#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./deploy_with_env.sh [agent_dir] [env_file] [additional agentcore args...]
# Example:
#   ./deploy_with_env.sh pet_store_agent
#   ./deploy_with_env.sh claim_inquiry_agent claim_inquiry_agent/.env --local

agent_dir="${1:-pet_store_agent}"
env_file="${2:-$agent_dir/.env}"

if [[ ! -d "$agent_dir" ]]; then
  echo "Error: agent directory not found: $agent_dir" >&2
  exit 1
fi

if [[ ! -f "$env_file" ]]; then
  echo "Error: .env file not found: $env_file" >&2
  exit 1
fi

if ! command -v agentcore >/dev/null 2>&1; then
  echo "Error: 'agentcore' CLI not found in PATH." >&2
  exit 1
fi

# Prefer project venv tools when available
if [[ -d ".venv/bin" ]]; then
  export PATH="$(pwd)/.venv/bin:$PATH"
fi

extra_args=()
if [[ $# -ge 3 ]]; then
  extra_args=("${@:3}")
fi
env_args=()

show_help_only=false
for arg in "${extra_args[@]}"; do
  if [[ "$arg" == "--help" ]]; then
    show_help_only=true
    break
  fi
done

if [[ "$show_help_only" == "false" ]] && ! command -v uv >/dev/null 2>&1; then
  if [[ -x ".venv/bin/python" ]]; then
    echo "uv not found in PATH. Installing uv into project .venv ..."
    .venv/bin/python -m pip install uv >/dev/null
  fi
fi

if [[ "$show_help_only" == "false" ]] && ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is required for direct_code_deploy deployment but was not found." >&2
  echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
  echo "Or use container deployment instead: agentcore configure --help" >&2
  exit 1
fi

# Export env vars from .env file
while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line%$'\r'}"
  [[ -z "$line" ]] && continue
  [[ "$line" =~ ^[[:space:]]*# ]] && continue

  if [[ "$line" != *=* ]]; then
    echo "Error: invalid .env line (expected KEY=VALUE): $line" >&2
    exit 1
  fi

  key="${line%%=*}"
  value="${line#*=}"

  # trim surrounding spaces on key only
  key="${key#"${key%%[![:space:]]*}"}"
  key="${key%"${key##*[![:space:]]}"}"

  if [[ -z "$key" ]]; then
    echo "Error: empty key in .env line: $line" >&2
    exit 1
  fi

  export "${key}=${value}"
  env_args+=(--env "${key}=${value}")
  echo "  Exported: $key"
done < "$env_file"

if [[ "$show_help_only" == "false" ]] && command -v aws >/dev/null 2>&1; then
  config_file="$agent_dir/.bedrock_agentcore.yaml"
  expected_account=""
  if [[ -f "$config_file" ]]; then
    expected_account="$(grep -E "^[[:space:]]*account:[[:space:]]*'?[0-9]{12}'?[[:space:]]*$" "$config_file" | head -n 1 | grep -oE "[0-9]{12}" | head -n 1)"
  fi

  if [[ -n "$expected_account" ]]; then
    active_account="$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true)"
    if [[ -n "$active_account" && "$active_account" != "$expected_account" ]]; then
      echo "Error: AWS account mismatch for deployment." >&2
      echo "  Active credentials account:   $active_account" >&2
      echo "  Agent config expected account: $expected_account" >&2
      echo "Switch to credentials for account $expected_account and retry." >&2
      exit 1
    fi
  fi
fi

echo "Deploying from $agent_dir using $env_file ..."
(
  cd "$agent_dir"
  agentcore deploy "${env_args[@]}" "${extra_args[@]}"
)
