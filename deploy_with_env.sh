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

extra_args=()
if [[ $# -ge 3 ]]; then
  extra_args=("${@:3}")
fi

env_args=()
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

  env_args+=(--env "${key}=${value}")
done < "$env_file"

echo "Deploying from $agent_dir using $env_file ..."
(
  cd "$agent_dir"
  agentcore deploy --auto-update-on-conflict --force-rebuild-deps "${env_args[@]}" "${extra_args[@]}"
)

