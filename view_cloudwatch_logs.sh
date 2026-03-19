#!/usr/bin/env bash
set -euo pipefail

# Query CloudWatch Logs Insights for all events related to a session/request/log identifier.
#
# Usage:
#   ./view_cloudwatch_logs.sh <id> --log-group <group-name> [options]
#
# Examples:
#   ./view_cloudwatch_logs.sh 9a28d3b0-bfbe-4df8-8281-2ee1a362aa65 --log-group /aws/lambda/my-runtime
#   ./view_cloudwatch_logs.sh d5f28d87-079e-43ed-8d76-6e5e24d3e4b7 --log-group /aws/lambda/my-runtime --hours 2
#   ./view_cloudwatch_logs.sh runtime-logs-9a28d3b0-bfbe-4df8-8281-2ee1a362aa65 --log-group /aws/lambda/my-runtime --json

usage() {
  cat <<'USAGE'
Usage:
  ./view_cloudwatch_logs.sh <id> --log-group <group-name> [options]

Required:
  <id>                     Identifier to trace (sessionId, requestId, runtime-logs-* token, etc.)
  --log-group <name>       CloudWatch log group name (or set CLOUDWATCH_LOG_GROUP)

Options:
  --region <aws-region>    AWS region (default: AWS_REGION/AWS_DEFAULT_REGION/us-east-1)
  --hours <n>              Time window backwards from now in hours (default: 24)
  --start <iso|epoch>      Start time override (ISO8601 like 2026-03-18T23:50:00Z or epoch seconds)
  --end <iso|epoch>        End time override (ISO8601 or epoch seconds; default: now)
  --limit <n>              Max rows returned (default: 500)
  --json                   Print raw query result JSON
  -h, --help               Show this help

Notes:
  - The script searches both @message and @logStream for the provided id.
  - For best results, narrow the time window with --hours or --start/--end.
USAGE
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Error: required command not found: $cmd" >&2
    exit 1
  fi
}

to_epoch_seconds() {
  local value="$1"
  python3 - "$value" <<'PY'
import datetime
import sys

raw = sys.argv[1].strip()
if raw.isdigit():
    print(raw)
    raise SystemExit(0)

candidate = raw.replace("Z", "+00:00")
try:
    dt = datetime.datetime.fromisoformat(candidate)
except ValueError as exc:
    raise SystemExit(f"Error: invalid time format: {raw}\nUse ISO8601 (e.g. 2026-03-18T23:50:00Z) or epoch seconds.") from exc

if dt.tzinfo is None:
    dt = dt.replace(tzinfo=datetime.timezone.utc)

print(int(dt.timestamp()))
PY
}

escape_regex() {
  local value="$1"
  python3 - "$value" <<'PY'
import re
import sys
print(re.escape(sys.argv[1]))
PY
}

id="${1:-}"
if [[ -z "$id" ]] || [[ "$id" == "-h" ]] || [[ "$id" == "--help" ]]; then
  usage
  exit 0
fi
shift || true

log_group="${CLOUDWATCH_LOG_GROUP:-}"
region="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
hours="24"
limit="500"
raw_json="false"
start_override=""
end_override=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log-group)
      log_group="${2:-}"
      shift 2
      ;;
    --region)
      region="${2:-}"
      shift 2
      ;;
    --hours)
      hours="${2:-}"
      shift 2
      ;;
    --start)
      start_override="${2:-}"
      shift 2
      ;;
    --end)
      end_override="${2:-}"
      shift 2
      ;;
    --limit)
      limit="${2:-}"
      shift 2
      ;;
    --json)
      raw_json="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$log_group" ]]; then
  echo "Error: missing --log-group (or CLOUDWATCH_LOG_GROUP env var)." >&2
  exit 1
fi

if ! [[ "$hours" =~ ^[0-9]+$ ]]; then
  echo "Error: --hours must be an integer." >&2
  exit 1
fi

if ! [[ "$limit" =~ ^[0-9]+$ ]]; then
  echo "Error: --limit must be an integer." >&2
  exit 1
fi

require_cmd aws
require_cmd python3

now_epoch="$(date -u +%s)"
if [[ -n "$start_override" ]]; then
  start_epoch="$(to_epoch_seconds "$start_override")"
else
  start_epoch="$((now_epoch - hours * 3600))"
fi

if [[ -n "$end_override" ]]; then
  end_epoch="$(to_epoch_seconds "$end_override")"
else
  end_epoch="$now_epoch"
fi

if (( start_epoch >= end_epoch )); then
  echo "Error: start time must be earlier than end time." >&2
  exit 1
fi

escaped_id="$(escape_regex "$id")"
query_string="$(cat <<EOFQ
fields @timestamp, @logStream, @message
| filter @message like /$escaped_id/ or @logStream like /$escaped_id/
| parse @message '"sessionId": "*"' as sessionId
| parse @message '"requestId": "*"' as requestId
| parse @message '"level": "*"' as level
| sort @timestamp asc
| limit $limit
EOFQ
)"

echo "Running Logs Insights query..."
echo "  region:    $region"
echo "  log group: $log_group"
echo "  id:        $id"
echo "  window:    $(date -u -r "$start_epoch" '+%Y-%m-%dT%H:%M:%SZ') -> $(date -u -r "$end_epoch" '+%Y-%m-%dT%H:%M:%SZ')"

start_json="$(aws logs start-query \
  --region "$region" \
  --log-group-name "$log_group" \
  --start-time "$start_epoch" \
  --end-time "$end_epoch" \
  --query-string "$query_string" \
  --output json)"

query_id="$(python3 - "$start_json" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
qid = payload.get("queryId", "")
if not qid:
    raise SystemExit("Error: failed to obtain CloudWatch queryId.")
print(qid)
PY
)"

status="Scheduled"
results_json=""
for _ in {1..30}; do
  results_json="$(aws logs get-query-results --region "$region" --query-id "$query_id" --output json)"
  status="$(python3 - "$results_json" <<'PY'
import json
import sys
print(json.loads(sys.argv[1]).get("status", "Unknown"))
PY
)"
  case "$status" in
    Complete)
      break
      ;;
    Failed|Cancelled|Timeout|Unknown)
      echo "Error: query ended with status: $status" >&2
      echo "$results_json"
      exit 1
      ;;
    *)
      sleep 1
      ;;
  esac
done

if [[ "$status" != "Complete" ]]; then
  echo "Error: query did not complete in time. Query ID: $query_id" >&2
  exit 1
fi

if [[ "$raw_json" == "true" ]]; then
  echo "$results_json"
  exit 0
fi

python3 - "$results_json" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
rows = payload.get("results", [])

if not rows:
    print("No matching events found in the selected window.")
    raise SystemExit(0)

def row_to_map(row):
    out = {}
    for item in row:
        out[item.get("field", "")] = item.get("value", "")
    return out

print(f"Found {len(rows)} event(s):")
for i, row in enumerate(rows, start=1):
    data = row_to_map(row)
    ts = data.get("@timestamp", "")
    stream = data.get("@logStream", "")
    level = data.get("level", "")
    sid = data.get("sessionId", "")
    rid = data.get("requestId", "")
    msg = data.get("@message", "")

    print(f"\n[{i}] {ts}  level={level or '-'}")
    print(f"    stream:    {stream}")
    if sid:
        print(f"    sessionId: {sid}")
    if rid:
        print(f"    requestId: {rid}")
    print(f"    message:   {msg}")
PY
