# Architectural Decisions - Bedrock Agents Assessment

Session started: 2026-03-18T16:42:35.258Z

## 2026-03-18 Decision: Prompt-level JSON enforcement for reject/error paths

- Chosen fix: strengthen `system_prompt` only (no code-path/tool/schema changes) by adding an explicit universal JSON requirement and three Reject JSON exemplars.
- Rationale: evaluation failures were format-compliance failures in rejection classes, and this model is instruction/example sensitive; prompt reinforcement is the lowest-risk, highest-leverage intervention.

## 2026-03-18 Decision: Adopt 3-agent orchestration with early-reject gate

- Chosen design: split `process_request` into Intent Classifier (nova-lite) → Data Retriever (nova-pro + tools) → Output Formatter (nova-pro).
- Rationale: reduce unnecessary tool calls and latency while preserving strict JSON output; enforce immediate Reject/Error response when classifier identifies unsafe or out-of-scope requests.
