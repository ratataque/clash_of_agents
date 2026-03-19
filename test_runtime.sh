#!/usr/bin/env bash
set -euo pipefail

# Run regression tests against deployed AgentCore runtime
# Usage:
#   ./test_runtime.sh [agent_dir] [env_file] [--tests A|A,B,...] [additional run_test.py args...]
# Examples:
#   ./test_runtime.sh pet_store_agent
#   ./test_runtime.sh pet_store_agent pet_store_agent/.env
#   ./test_runtime.sh pet_store_agent pet_store_agent/.env --tests B
#   ./test_runtime.sh pet_store_agent pet_store_agent/.env --tests A,C,U

selected_tests=""
positional_args=()
runner_args=()
all_args=("$@")
i=0
while [[ $i -lt ${#all_args[@]} ]]; do
  arg="${all_args[$i]}"
  case "$arg" in
    -h|--help)
      echo "Usage: ./test_runtime.sh [agent_dir] [env_file] [--tests A|A,B,...] [additional run_test.py args...]"
      exit 0
      ;;
    --tests|-t)
      i=$((i + 1))
      if [[ $i -ge ${#all_args[@]} ]]; then
        echo "Error: --tests requires a value (for example: --tests A,B)" >&2
        exit 1
      fi
      selected_tests="${all_args[$i]}"
      ;;
    --tests=*|-t=*)
      selected_tests="${arg#*=}"
      ;;
    --)
      i=$((i + 1))
      while [[ $i -lt ${#all_args[@]} ]]; do
        runner_args+=("${all_args[$i]}")
        i=$((i + 1))
      done
      break
      ;;
    -*)
      runner_args+=("$arg")
      ;;
    *)
      positional_args+=("$arg")
      ;;
  esac
  i=$((i + 1))
done

agent_dir="${positional_args[0]:-pet_store_agent}"
env_file="${positional_args[1]:-$agent_dir/.env}"
if [[ ${#positional_args[@]} -gt 2 ]]; then
  runner_args+=("${positional_args[@]:2}")
fi

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

if [[ ! -f "$env_file" ]]; then
  echo "Error: .env file not found: $env_file" >&2
  exit 1
fi

runner_file=""
if [[ -f "run_test.py" ]]; then
  runner_file="run_test.py"
elif [[ -f "run_tests.py" ]]; then
  runner_file="run_tests.py"
else
  echo "Error: neither run_test.py nor run_tests.py found in repository root." >&2
  exit 1
fi

python_bin="python"
if [[ -x ".venv/bin/python" ]]; then
  python_bin=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  python_bin="python3"
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
  key="${key#"${key%%[![:space:]]*}"}"
  key="${key%"${key##*[![:space:]]}"}"

  if [[ -z "$key" ]]; then
    echo "Error: empty key in .env line: $line" >&2
    exit 1
  fi

  export "${key}=${value}"
  echo "  Exported: $key"
done < "$env_file"

# Default AGENT_RUNTIME_ARN from deployed runtime metadata unless already set
if [[ -z "${AGENT_RUNTIME_ARN:-}" ]]; then
  runtime_arn="$("$python_bin" - "$yaml_file" <<'PY'
import sys
from pathlib import Path
import yaml

yaml_file = Path(sys.argv[1])
data = yaml.safe_load(yaml_file.read_text())
default_agent = data.get("default_agent")
if not default_agent or default_agent not in data.get("agents", {}):
    raise SystemExit(f"Error: default agent missing/invalid in {yaml_file}")
agent_cfg = data["agents"][default_agent]
agent_arn = agent_cfg.get("bedrock_agentcore", {}).get("agent_arn")
if not agent_arn:
    raise SystemExit("Error: agent_arn not found in .bedrock_agentcore.yaml (deploy may not have completed)")
print(agent_arn)
PY
)"
  export AGENT_RUNTIME_ARN="$runtime_arn"
  echo "  Exported: AGENT_RUNTIME_ARN"
fi

if [[ -n "$selected_tests" ]]; then
  IFS=',' read -r -a selected_array <<< "$selected_tests"
  tests=()
  for test_id in "${selected_array[@]}"; do
    test_id="${test_id// /}"
    test_id="${test_id^^}"
    [[ -z "$test_id" ]] && continue
    tests+=("$test_id")
  done

  if [[ ${#tests[@]} -eq 0 ]]; then
    echo "Error: --tests value is empty. Use values like A or A,B" >&2
    exit 1
  fi

  echo "Running tests with $env_file (runner: $runner_file, tests: $selected_tests) ..."
  "$python_bin" "$runner_file" "${tests[@]}" "${runner_args[@]}"
else
  echo "Running tests with $env_file (runner: $runner_file) ..."
  "$python_bin" "$runner_file" "${runner_args[@]}"
fi
