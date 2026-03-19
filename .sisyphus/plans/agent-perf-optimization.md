# Pet Store Agent — Response Latency Optimization

## TL;DR

> **Quick Summary**: Optimize the pet store AI agent from ~240s total benchmark time (10 tests × ~24s each) to sub-60s, by layering 6 complementary optimizations: singleton reuse, model downgrade, config tuning, deterministic routing, pre-fetch round-trip reduction, and benchmark parallelization.
> 
> **Deliverables**:
> - Modified `pet_store_agent.py` with singleton agent, Haiku 4.5 model, hybrid router, pre-fetch orchestration
> - Modified tool files with singleton boto3 clients and reduced KB results
> - Modified `run_tests.py` with parallel test execution and per-test timing
> - Successful redeployment via `./redeploy.sh`
> - All 10 tests passing with total benchmark time < 60s
> 
> **Estimated Effort**: Medium (6-8 tasks, ~3 hours implementation)
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 (baseline) → Task 2 (singletons) → Task 3 (model swap + config) → Task 5 (router) → Task 6 (pre-fetch) → Task 7 (deploy + validate) → F1-F4 (final verification)

---

## Context

### Original Request
User wants to reduce the 10-test benchmark (`run_tests.py`) from ~4 minutes to sub-1 minute. The agent is a pet store AI on AWS Bedrock AgentCore using Strands Agents SDK. User is open to any architecture change: model swaps, hybrid routing, programmatic tools, sub-agents, microservices.

### Interview Summary
**Key Discussions**:
- Agent uses Claude Sonnet 4 (~3-8s per LLM round-trip) — massively overkill for structured tool-use
- Agent is recreated every request — ~2-3s waste per call
- 4-7 LLM round-trips per request for tool decisions
- boto3 clients recreated per tool call — ~50-200ms waste each
- KB retrieval returns 10 results when 3-5 suffice
- Tests C, U, N, F are simple rejection cases that could bypass LLM entirely
- Test harness runs sequentially

**Research Findings**:
- Claude 3.5 Haiku TTFT: ~0.7-1.0s vs Sonnet 4: ~3-5s (5-10x faster per round-trip). Haiku 4.5 (Oct 2025) is even smarter while maintaining Haiku speed tier
- Amazon Nova Micro TTFT: 0.70s, 288.5 tokens/s — viable router model
- AWS Intelligent Prompt Routing: endorsed pattern for cost/latency (56% cost savings, 6.15% latency benefit)
- Bedrock prompt caching: up to 85% latency reduction for repeated prefixes
- Singleton agent/client reuse: safe in AgentCore warm runtime (module-level globals persist)
- Pre-fetch + parallel tool execution: can reduce 4-7 sequential round-trips to 1-2

### Metis Review
**Identified Gaps** (addressed):
- **Baseline capture**: Added Task 1 to record per-test timing before any changes
- **Behavior preservation**: Added golden output snapshot requirement
- **Rollback strategy**: Each optimization is a separate commit, individually revertable
- **Singleton safety**: Agent/client reuse validated as safe for stateless tools (no cross-request contamination)
- **Model accuracy risk**: Task 4 includes accuracy validation — if Haiku 4.5 fails tests, try Nova 2 Lite, then Haiku 3.5 as fallback. Other optimizations still provide significant speedup with any model
- **Parallel test throttling**: Task 8 includes bounded concurrency to avoid API throttling
- **max_tokens truncation risk**: Set to 2048 (not 1024) for safety margin

---

## Work Objectives

### Core Objective
Reduce total 10-test benchmark time from ~240s to <60s while maintaining 10/10 test pass rate.

### Concrete Deliverables
- `pet_store_agent/pet_store_agent.py` — singleton agent, model swap, hybrid router, pre-fetch orchestration, shorter prompt
- `pet_store_agent/retrieve_product_info.py` — singleton boto3 client, reduced KB result count (10→5)
- `pet_store_agent/retrieve_pet_care.py` — singleton boto3 client, reduced KB result count (10→5)
- `pet_store_agent/inventory_management.py` — singleton boto3 client
- `pet_store_agent/user_management.py` — singleton boto3 client
- `run_tests.py` — parallel execution with per-test timing output
- Successful deployment via `./redeploy.sh` with 10/10 pass rate and <60s total

### Definition of Done
- [ ] `python run_tests.py` → 10/10 tests pass
- [ ] `python run_tests.py` → total wall time < 60s
- [ ] Each test individually completes in < 15s (no single-test regression)
- [ ] `./redeploy.sh` exits 0

### Must Have
- All 10 tests (A, B, C, U, N, E, F, Y, K, P) pass after every change
- Total benchmark time < 60s
- Deployment via `./redeploy.sh` works
- Per-test timing output for measurement
- Each optimization layer individually revertable

### Must NOT Have (Guardrails)
- **No Lambda function changes** — inventory and user management Lambdas are out of scope
- **No Knowledge Base data changes** — KB content/schema untouched
- **No new external dependencies** — no Redis, no new AWS services, no new pip packages beyond what's in requirements.txt
- **No test semantics changes** — test pass/fail criteria in `run_tests.py` remain identical
- **No over-engineering** — no generic routing framework, no abstraction layers, no sub-agent microservice architecture
- **No caching of user/inventory data** — these are request-specific and must be fresh per call
- **No prompt semantic changes** — prompt can be shortened but must preserve all business rules and response format requirements
- **No changes to guardrail configuration** — guardrail ID `i8ww2sdhqkcu` v1 stays as-is

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES — `run_tests.py` is the benchmark harness, `test_pricing.py` has unit tests
- **Automated tests**: YES (tests-after) — existing benchmark IS the test suite; run after each optimization layer
- **Framework**: Python script (`run_tests.py`) invoking Bedrock AgentCore runtime

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Agent/Backend**: Use Bash (`python run_tests.py`) — Run full benchmark, assert pass count + timing
- **Deployment**: Use Bash (`./redeploy.sh`) — Assert exit code 0
- **Per-change validation**: Run benchmark after each optimization layer

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — baseline + independent infra):
├── Task 1: Capture baseline timing [quick]
├── Task 2: Singleton boto3 clients in all 4 tool files [quick]
└── Task 3: Parallel test execution in run_tests.py [quick]

Wave 2 (After Wave 1 — core agent optimizations):
├── Task 4: Singleton agent + model swap + config tuning [deep]
├── Task 5: Deterministic router for rejection cases [deep]
└── Task 6: Pre-fetch orchestration to reduce LLM round-trips [deep]

Wave 3 (After Wave 2 — deploy + validate):
├── Task 7: Deploy + full benchmark validation [quick]

Wave FINAL (After ALL tasks — parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real QA - full benchmark run (unspecified-high)
└── F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 (baseline) | — | 4, 5, 6 (need baseline for comparison) |
| 2 (boto3 singletons) | — | 7 (deploy) |
| 3 (parallel tests) | — | 7 (deploy) |
| 4 (agent singleton + model) | 1 | 5, 6, 7 |
| 5 (router) | 4 | 7 |
| 6 (pre-fetch) | 4 | 7 |
| 7 (deploy + validate) | 2, 3, 4, 5, 6 | F1-F4 |
| F1-F4 | 7 | — |

### Agent Dispatch Summary

- **Wave 1**: 3 tasks — T1 → `quick`, T2 → `quick`, T3 → `quick`
- **Wave 2**: 3 tasks — T4 → `deep`, T5 → `deep`, T6 → `deep`
- **Wave 3**: 1 task — T7 → `quick`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Capture Baseline Timing

  **What to do**:
  - Add per-test timing instrumentation to `run_tests.py`:
    - Wrap each test invocation with `time.time()` before and after
    - Print per-test timing after each test: `Test X: PASS/FAIL in {N:.1f}s`
    - Print total wall time at the end: `Total: {N:.1f}s`
  - Run the benchmark once to capture the baseline numbers
  - Save baseline output to `.sisyphus/evidence/task-1-baseline.txt`
  - **Important**: Do NOT change test logic, pass/fail criteria, or test order — only ADD timing instrumentation

  **Must NOT do**:
  - Change test pass/fail logic
  - Change test invocation method
  - Add parallelization (that's Task 3)
  - Change any test assertions or expected outputs

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple instrumentation addition — add timing wrappers around existing code
  - **Skills**: []
    - No specialized skills needed for basic Python timing code

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4, 5, 6 (they need baseline for comparison)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `run_tests.py:494-499` — Main test loop where timing should be added. Currently iterates `tests` list and calls each test function sequentially
  - `run_tests.py:17-44` — `invoke_agent()` function that makes the actual Bedrock AgentCore call — this is what takes ~24s per test

  **API/Type References**:
  - `run_tests.py:46-60` — `extract_json_from_response()` — JSON extraction from agent response, used by all tests

  **WHY Each Reference Matters**:
  - `run_tests.py:494-499`: This is the exact loop to instrument with timing. Each `test_*()` call here is one benchmark data point
  - `run_tests.py:17-44`: Understanding the invoke function helps verify that timing captures the full round-trip, not just post-processing

  **Acceptance Criteria**:
  - [ ] `python run_tests.py` still passes 10/10 tests (no behavioral change)
  - [ ] Each test prints timing: `Test X: PASS/FAIL in N.Ns`
  - [ ] Final line prints total: `Total: N.Ns`

  **QA Scenarios**:
  ```
  Scenario: Baseline benchmark capture
    Tool: Bash (python run_tests.py)
    Preconditions: Agent is deployed and accessible
    Steps:
      1. Run `python run_tests.py` and capture full output
      2. Verify output contains per-test timing lines matching pattern "Test [A-Z]: (PASS|FAIL) in [0-9]+\.[0-9]+s"
      3. Verify output contains final timing line matching "Total: [0-9]+\.[0-9]+s"
      4. Count PASS results — expect exactly 10
      5. Save full output to `.sisyphus/evidence/task-1-baseline.txt`
    Expected Result: 10/10 PASS, total time printed (likely ~200-300s), per-test times printed
    Failure Indicators: Any test FAILs that previously PASSed, timing not printed, total not shown
    Evidence: .sisyphus/evidence/task-1-baseline.txt
  ```

  **Commit**: YES
  - Message: `perf(bench): add per-test timing instrumentation to run_tests.py`
  - Files: `run_tests.py`
  - Pre-commit: `python run_tests.py` (10/10 pass)

- [x] 2. Singleton boto3 Clients in All Tool Files

  **What to do**:
  - In each of the 4 tool files, move boto3 client creation from inside the tool function to module-level:
    - `retrieve_product_info.py`: Move `boto3.client('bedrock-agent-runtime')` to module level
    - `retrieve_pet_care.py`: Move `boto3.client('bedrock-agent-runtime')` to module level
    - `inventory_management.py`: Move `boto3.client('lambda')` to module level
    - `user_management.py`: Move `boto3.client('lambda')` to module level (appears in multiple functions — `get_user_by_id` and `get_user_by_email`)
  - Use a simple pattern: `_client = None` at module level, lazy-init on first call
  - This is safe because boto3 clients are thread-safe for read operations and these tools don't modify AWS state

  **Must NOT do**:
  - Change tool function signatures or return types
  - Change any tool logic beyond client creation
  - Add connection pooling or caching of tool results
  - Change environment variable reading logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mechanical refactor — move client creation from function scope to module scope in 4 files
  - **Skills**: []
    - No specialized skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Task 7 (deploy)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `pet_store_agent/retrieve_product_info.py:86-96` — Current client creation inside function: `client = boto3.client('bedrock-agent-runtime', region_name=region)`. Move to module-level lazy-init
  - `pet_store_agent/retrieve_pet_care.py:86-96` — Identical pattern to product info — same refactor needed
  - `pet_store_agent/inventory_management.py:44-66` — Lambda client creation inside `get_inventory()`. Move to module level
  - `pet_store_agent/user_management.py:50-72` — Lambda client creation inside `get_user_by_id()`. Also check `get_user_by_email()` at `:123-146` for same pattern

  **WHY Each Reference Matters**:
  - Each file creates a new boto3 client per invocation (~50-200ms). With 2-4 tool calls per request, this wastes 100-800ms. Module-level singletons eliminate this entirely after first call

  **Acceptance Criteria**:
  - [ ] All 4 tool files use module-level client (lazy-init pattern)
  - [ ] No `boto3.client(...)` calls remain inside tool functions
  - [ ] `ast_grep_search` for `boto3.client` inside function bodies returns 0 matches in tool files

  **QA Scenarios**:
  ```
  Scenario: Verify boto3 singleton pattern applied
    Tool: Bash (ast_grep_search or grep)
    Preconditions: All 4 tool files modified
    Steps:
      1. Use grep to search for `boto3.client` in all 4 tool files
      2. Verify each file has exactly ONE boto3.client call at module level (or in a lazy-init helper)
      3. Verify no boto3.client calls exist inside the @tool decorated functions
      4. Read each file to confirm the function still passes the correct region_name and function_name
    Expected Result: Each file has 1 module-level client, 0 in-function clients
    Failure Indicators: boto3.client found inside @tool function body, client not using correct region
    Evidence: .sisyphus/evidence/task-2-singleton-audit.txt

  Scenario: Verify no import errors in tool files
    Tool: Bash (python -c "import pet_store_agent.retrieve_product_info" etc.)
    Preconditions: Files modified
    Steps:
      1. Run `python -c "import pet_store_agent.retrieve_product_info"` — should not error
      2. Run `python -c "import pet_store_agent.retrieve_pet_care"` — should not error
      3. Run `python -c "import pet_store_agent.inventory_management"` — should not error
      4. Run `python -c "import pet_store_agent.user_management"` — should not error
    Expected Result: All 4 imports succeed with exit code 0
    Failure Indicators: ImportError, SyntaxError, or any exception
    Evidence: .sisyphus/evidence/task-2-import-check.txt
  ```

  **Commit**: YES
  - Message: `perf(tools): singleton boto3 clients for all tool modules`
  - Files: `pet_store_agent/retrieve_product_info.py`, `pet_store_agent/retrieve_pet_care.py`, `pet_store_agent/inventory_management.py`, `pet_store_agent/user_management.py`

- [x] 3. Parallel Test Execution in run_tests.py

  **What to do**:
  - Modify `run_tests.py` to run all 10 tests concurrently using `concurrent.futures.ThreadPoolExecutor`
  - Use `max_workers=5` to avoid API throttling (not all 10 at once)
  - Each test function should still be called identically — only the orchestration changes
  - Preserve per-test timing output from Task 1
  - Print total wall time (which should now be ~max(individual times) × 2 due to concurrency limit)
  - **Critical**: Test functions must be thread-safe. Review `invoke_agent()` — it creates its own boto3 client per call, which is fine for thread safety

  **Must NOT do**:
  - Change individual test function logic
  - Change pass/fail criteria
  - Use more than 5 concurrent workers (risk of API throttling)
  - Change the test function signatures

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Replace sequential loop with ThreadPoolExecutor — straightforward Python concurrency pattern
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Task 7 (deploy validation uses this)
  - **Blocked By**: Task 1 (needs timing instrumentation first)

  **References**:

  **Pattern References**:
  - `run_tests.py:494-499` — Current sequential test loop to replace with ThreadPoolExecutor
  - `run_tests.py:17-44` — `invoke_agent()` creates its own boto3 client — this makes it thread-safe since each thread gets its own client

  **API/Type References**:
  - `run_tests.py:62-494` — All test functions (`test_a` through `test_p`). Each is a standalone function returning PASS/FAIL with no shared mutable state

  **WHY Each Reference Matters**:
  - `:494-499`: This is the exact code to refactor — replace `for test in tests: test()` with `executor.map()`
  - `:17-44`: Confirms thread safety — each invoke creates its own client, no shared state

  **Acceptance Criteria**:
  - [ ] Tests run with ThreadPoolExecutor (max_workers=5)
  - [ ] All 10 tests still pass
  - [ ] Per-test timing still printed
  - [ ] Total wall time significantly less than sequential (should be ~2-3x faster just from parallelization)

  **QA Scenarios**:
  ```
  Scenario: Parallel benchmark execution
    Tool: Bash (python run_tests.py)
    Preconditions: Tasks 1 and 3 both applied, agent deployed
    Steps:
      1. Run `python run_tests.py` and capture full output
      2. Count PASS results — expect exactly 10
      3. Read total wall time from final line
      4. Verify total wall time is < 150s (should be roughly 2-3x faster than baseline ~240s)
    Expected Result: 10/10 PASS, total time < 150s (parallelization alone, before agent optimizations)
    Failure Indicators: Any test FAIL, total time > 200s (parallelization not working), errors about throttling
    Evidence: .sisyphus/evidence/task-3-parallel-benchmark.txt

  Scenario: Thread safety — no result cross-contamination
    Tool: Bash (python run_tests.py)
    Preconditions: Parallel execution enabled
    Steps:
      1. Run benchmark 3 times in succession
      2. Compare pass/fail results across all 3 runs
      3. Verify identical 10/10 pass rate each time
    Expected Result: All 3 runs produce identical 10/10 PASS results
    Failure Indicators: Intermittent failures, different results between runs
    Evidence: .sisyphus/evidence/task-3-stability.txt
  ```

  **Commit**: YES
  - Message: `perf(bench): parallel test execution with ThreadPoolExecutor`
  - Files: `run_tests.py`
  - Pre-commit: `python run_tests.py` (10/10 pass)

- [x] 4. Singleton Agent + Model Swap to Haiku 4.5 + Config Tuning

  **What to do**:
  - **Singleton Agent**: Move agent creation from `process_request()` to module level in `pet_store_agent.py`:
    - Create `BedrockModel` and `Agent` once at module load time (or lazy-init on first call)
    - `process_request()` should reuse the singleton agent instead of calling `create_agent()` each time
    - The agent must be stateless between requests — verify that Strands Agent doesn't accumulate conversation history (if it does, reset messages between calls)
  - **Model Swap**: Change model from `us.anthropic.claude-sonnet-4-20250514-v1:0` to `anthropic.claude-haiku-4-5-20251001-v1:0` (Claude Haiku 4.5 — newest generation, fast + smart)
    - This is the single biggest latency win: ~3-8s → ~0.5-2s per LLM round-trip
    - Haiku 4.5 is newer than 3.5 (Oct 2025) — better tool-use accuracy while maintaining Haiku speed
    - If Haiku 4.5 fails tests, try `amazon.nova-2-lite-v1:0` (Nova 2nd gen), then `anthropic.claude-3-5-haiku-20241022-v1:0` as final fallback
  - **Config Tuning**:
    - Reduce `max_tokens` from 4096 to 2048 (responses are ~200-500 tokens, 2048 gives safety margin)
    - In KB retrieval tools (`retrieve_product_info.py`, `retrieve_pet_care.py`): reduce `numberOfResults` from 10 to 5
  - **System Prompt Compression**: Shorten the system prompt while preserving ALL business rules:
    - Remove verbose examples if present — keep only the rules
    - Remove redundant formatting instructions
    - Target: reduce token count by ~30-50% without losing any business logic
    - **Critical**: Every business rule in the current prompt must have a corresponding rule in the new prompt

  **Must NOT do**:
  - Remove any business rules from the system prompt (compress, don't delete)
  - Change tool function signatures or tool registration
  - Cache any per-request data (user info, inventory)
  - Change the guardrail configuration
  - Use a model not available in us-east-1 on Bedrock

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: This is the highest-impact task requiring careful model selection, prompt engineering, and understanding of Strands Agent lifecycle. Needs to verify Haiku maintains accuracy on all 10 tests
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (but should run first within wave — Tasks 5 and 6 build on this)
  - **Blocks**: Tasks 5, 6, 7
  - **Blocked By**: Task 1 (needs baseline)

  **References**:

  **Pattern References**:
  - `pet_store_agent/pet_store_agent.py:173-218` — `create_agent()` function: creates `BedrockModel` with model_id, then `Agent` with system_prompt, tools list, and model. This entire function should be called once at module level
  - `pet_store_agent/pet_store_agent.py:219-224` — `process_request()`: currently calls `create_agent()` every time. Should use the module-level singleton instead
  - `pet_store_agent/pet_store_agent.py:16-170` — `SYSTEM_PROMPT`: the full system prompt text (~4000 tokens). Compress this while keeping all rules

  **API/Type References**:
  - `pet_store_agent/pet_store_agent.py:175-184` — `BedrockModel` constructor parameters: `model_id`, `max_tokens`, `guardrail_config`. Change `model_id` and `max_tokens` here
  - `pet_store_agent/retrieve_product_info.py:88-96` — KB retrieval config with `numberOfResults` parameter to reduce
  - `pet_store_agent/retrieve_pet_care.py:88-96` — Same KB config to reduce

  **External References**:
  - Claude Haiku 4.5 model ID on Bedrock: `anthropic.claude-haiku-4-5-20251001-v1:0` (primary choice — newest Haiku, best quality/speed)
  - Amazon Nova 2 Lite model ID (fallback 1): `amazon.nova-2-lite-v1:0`
  - Claude 3.5 Haiku model ID (fallback 2): `anthropic.claude-3-5-haiku-20241022-v1:0`
  - Amazon Nova Micro model ID (reference only): `amazon.nova-micro-v1:0` — fastest model available, useful if a router model is needed later
  - Strands Agents SDK: Agent class likely accumulates `messages` — check if `.messages` needs clearing between requests

  **WHY Each Reference Matters**:
  - `:173-218`: This is THE function to make singleton. Understanding its parameters is essential for correct initialization
  - `:219-224`: This is the hot path — every request goes through here. Removing `create_agent()` call saves 2-3s
  - `:16-170`: System prompt compression must preserve every rule. Read carefully before shortening
  - `:175-184`: The BedrockModel constructor is where model_id and max_tokens are set — the two config changes
  - KB retrieval configs: Reducing from 10 to 5 results means fewer tokens in LLM context = faster processing

  **Acceptance Criteria**:
  - [ ] Agent is created once at module level (singleton pattern)
  - [ ] Model ID changed to Haiku 3.5 (or Nova Lite if Haiku fails tests)
  - [ ] `max_tokens` reduced to 2048
  - [ ] KB `numberOfResults` reduced to 5 in both retrieval files
  - [ ] System prompt shorter but preserving all business rules
  - [ ] Cannot test remotely until deploy — but verify code is syntactically valid: `python -c "import pet_store_agent.pet_store_agent"`

  **QA Scenarios**:
  ```
  Scenario: Verify singleton agent pattern
    Tool: Bash (grep/read)
    Preconditions: pet_store_agent.py modified
    Steps:
      1. Read `pet_store_agent.py` and verify `create_agent()` is called at module level (outside any function)
      2. Verify `process_request()` does NOT call `create_agent()`
      3. Verify the agent variable is reused across calls
      4. Check if Agent has a `.messages` attribute that needs clearing between requests
    Expected Result: One agent creation at module level, process_request uses it directly
    Failure Indicators: create_agent() still called inside process_request()
    Evidence: .sisyphus/evidence/task-4-singleton-verify.txt

  Scenario: Verify model ID and config changes
    Tool: Bash (grep)
    Preconditions: pet_store_agent.py modified
    Steps:
      1. Grep for model_id in pet_store_agent.py — expect "claude-haiku-4-5" or "nova-2-lite"
      2. Grep for max_tokens — expect 2048
      3. Grep for numberOfResults in retrieve_product_info.py — expect 5
      4. Grep for numberOfResults in retrieve_pet_care.py — expect 5
    Expected Result: All config values match expected
    Failure Indicators: Old model ID still present, max_tokens still 4096, numberOfResults still 10
    Evidence: .sisyphus/evidence/task-4-config-verify.txt

  Scenario: Verify system prompt preservation
    Tool: Bash (python)
    Preconditions: pet_store_agent.py modified
    Steps:
      1. Extract the new system prompt text
      2. Verify it still mentions: cat, dog, subscription types, pricing rules, order format, rejection criteria
      3. Count approximate token length — should be 30-50% shorter than original
    Expected Result: All business rules preserved, prompt shorter
    Failure Indicators: Missing business rules, prompt same length or longer
    Evidence: .sisyphus/evidence/task-4-prompt-verify.txt

  Scenario: Verify code imports cleanly
    Tool: Bash (python -c)
    Preconditions: All Task 4 changes applied
    Steps:
      1. Run `python -c "import pet_store_agent.pet_store_agent"` from the pet_store_agent directory
      2. Expect exit code 0 (may fail if env vars not set — that's okay, check for SyntaxError only)
    Expected Result: No SyntaxError or ImportError
    Failure Indicators: SyntaxError, ImportError, IndentationError
    Evidence: .sisyphus/evidence/task-4-import-check.txt
  ```

  **Commit**: YES
  - Message: `perf(agent): singleton agent + Haiku 4.5 model + config tuning`
  - Files: `pet_store_agent/pet_store_agent.py`, `pet_store_agent/retrieve_product_info.py`, `pet_store_agent/retrieve_pet_care.py`

- [x] 5. Deterministic Router for Rejection Cases

  **What to do**:
  - Add a fast pre-classifier in `process_request()` that runs BEFORE the LLM agent:
    - **Keyword/regex-based classification** — no LLM call needed
    - For requests matching rejection patterns, return a pre-formatted rejection response immediately
  - **Rejection patterns to detect** (based on test analysis):
    - **Test C (prompt injection)**: Detect system prompt override attempts — patterns like "ignore previous", "you are now", "forget your instructions", "system:", "override"
    - **Test U (unethical)**: Detect requests for harmful advice — patterns like "poison", "harm", "kill", "hurt", "abuse" in pet context
    - **Test N (hamster/non-cat-dog)**: Detect non-cat/non-dog animal requests — check if request mentions animal names NOT in {"cat", "dog", "kitten", "puppy"} and doesn't mention cat/dog
    - **Test F (bird seed)**: Detect non-cat/non-dog product requests — check if product name doesn't match any known cat/dog products
  - **Response format**: Return the same JSON structure the agent would return for rejections, with appropriate error messages
  - **Safety**: If the classifier is unsure (no clear match), always fall through to the full LLM pipeline. False negatives are fine; false positives are NOT
  - **Implementation approach**: Simple Python function, ~30-50 lines. No ML model, no LLM call

  **Must NOT do**:
  - Use an LLM for classification (that defeats the purpose)
  - Block requests that should succeed (false positives are unacceptable)
  - Change the response format for rejections
  - Be too aggressive with pattern matching — when in doubt, let the LLM handle it
  - Remove or bypass the Bedrock guardrail (it still applies on the LLM path)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires careful analysis of test cases to determine correct rejection patterns without false positives. Must understand the exact boundary between what should be rejected vs processed
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 6, after Task 4)
  - **Parallel Group**: Wave 2 (with Task 6)
  - **Blocks**: Task 7
  - **Blocked By**: Task 4 (builds on singleton agent in pet_store_agent.py)

  **References**:

  **Pattern References**:
  - `pet_store_agent/pet_store_agent.py:219-224` — `process_request()`: the router should be added at the START of this function, before agent invocation
  - `pet_store_agent/pet_store_agent.py:16-170` — System prompt contains business rules for what to reject: non-cat/dog animals, unethical requests, prompt injection attempts

  **Test References** (CRITICAL — these define what the router must handle):
  - `run_tests.py` Test C — Prompt injection test. Look at the exact prompt sent and the expected response pattern
  - `run_tests.py` Test U — Unethical request test. Look at exact prompt and expected rejection
  - `run_tests.py` Test N — Hamster (non-cat/dog) test. Look at exact prompt and expected rejection
  - `run_tests.py` Test F — Bird seed (non-pet product) test. Look at exact prompt and expected rejection

  **WHY Each Reference Matters**:
  - `process_request()`: This is where the router goes — before the agent.process() call
  - System prompt: Defines the rejection rules the router must replicate
  - Test files: The router's output must match what these tests expect. Read each test to understand the EXACT expected response format

  **Acceptance Criteria**:
  - [ ] Router function exists in `pet_store_agent.py`
  - [ ] Router handles tests C, U, N, F without LLM call
  - [ ] Router returns properly formatted JSON responses matching test expectations
  - [ ] Router falls through to LLM for tests A, B, E, K, Y, P
  - [ ] No false positives — legitimate requests never blocked by router

  **QA Scenarios**:
  ```
  Scenario: Router correctly rejects prompt injection (Test C pattern)
    Tool: Bash (python)
    Preconditions: Router added to process_request()
    Steps:
      1. Create a test script that calls process_request() with Test C's exact prompt
      2. Measure response time — should be < 100ms (no LLM call)
      3. Verify response contains rejection message
    Expected Result: Instant rejection (<100ms), correctly formatted response
    Failure Indicators: Response takes >1s (LLM was called), wrong format
    Evidence: .sisyphus/evidence/task-5-router-injection.txt

  Scenario: Router does NOT block legitimate orders (Test A pattern)
    Tool: Bash (python)
    Preconditions: Router added to process_request()
    Steps:
      1. Create a test script that calls process_request() with Test A's exact prompt
      2. Verify the router does NOT intercept this — it should fall through to LLM
      3. The response should be a valid order, not a rejection
    Expected Result: Router passes through, LLM processes normally
    Failure Indicators: Router incorrectly rejects a legitimate order
    Evidence: .sisyphus/evidence/task-5-router-passthrough.txt
  ```

  **Commit**: YES
  - Message: `perf(agent): deterministic router for fast rejection cases`
  - Files: `pet_store_agent/pet_store_agent.py`

- [x] 6. Pre-Fetch Orchestration to Reduce LLM Round-Trips

  **What to do**:
  - **Goal**: Reduce from 4-7 LLM round-trips per request to 1-2 by pre-fetching data before the LLM decides
  - **Approach**: For requests that pass the router (legitimate orders), parse the request programmatically to extract:
    - Customer identifier (ID or email) — regex for email pattern, or look for numeric IDs
    - Product name mentions — match against known product keywords (cat food, dog food, etc.)
    - Action type — order, subscription, inquiry, pet care advice
  - **Pre-fetch pipeline**: Based on extracted info, call relevant tools IN PARALLEL before the LLM:
    - If customer ID found → call `get_user_by_id` or `get_user_by_email`
    - If product mentioned → call `retrieve_product_info` with product keywords
    - If pet care topic detected → call `retrieve_pet_care`
    - If product mentioned → call `get_inventory` for that product
  - **Inject pre-fetched data**: Add the pre-fetched results to the user message or as a context prefix, so the LLM has all data in its FIRST call and can generate the final response without additional tool calls
  - **Fallback**: If pre-fetch parsing fails or extracts nothing, fall through to normal agent behavior (LLM decides tools). This ensures correctness is never sacrificed for speed
  - **Use `concurrent.futures.ThreadPoolExecutor`** for parallel tool calls

  **Must NOT do**:
  - Cache results between different requests
  - Skip the LLM entirely for order processing (LLM still needed for pricing logic, response formatting, and business rule application)
  - Remove tools from the agent (they're still needed as fallback)
  - Change tool function signatures
  - Pre-fetch data that isn't needed (wasteful API calls)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex orchestration logic — needs to parse natural language requests, determine which tools to call, run them in parallel, and inject results into the LLM context. Must handle edge cases gracefully
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 5, after Task 4)
  - **Parallel Group**: Wave 2 (with Task 5)
  - **Blocks**: Task 7
  - **Blocked By**: Task 4 (needs singleton agent and model swap)

  **References**:

  **Pattern References**:
  - `pet_store_agent/pet_store_agent.py:219-224` — `process_request()`: pre-fetch pipeline goes between router check and agent invocation
  - `pet_store_agent/pet_store_agent.py:173-218` — `create_agent()` shows which tools are registered — these are the functions to call in pre-fetch

  **API/Type References**:
  - `pet_store_agent/retrieve_product_info.py` — KB retrieval function signature: takes a query string, returns retrieval results
  - `pet_store_agent/retrieve_pet_care.py` — KB retrieval function signature: takes a query string, returns pet care info
  - `pet_store_agent/inventory_management.py` — `get_inventory()` function: takes product_id or product_name
  - `pet_store_agent/user_management.py` — `get_user_by_id(user_id)` and `get_user_by_email(email)` functions
  - `pet_store_agent/pricing.py` — `calculate_order_pricing()`: local function, very fast, can be called after data is fetched

  **Test References**:
  - `run_tests.py` Test A — Basic order: mentions customer ID, product. Good pre-fetch candidate
  - `run_tests.py` Test B — Subscription + advice: mentions customer, product, AND pet care. Multiple pre-fetches needed
  - `run_tests.py` Test E — Multi-item order: mentions customer, multiple products
  - `run_tests.py` Test K — Order with specific constraints
  - `run_tests.py` Test Y — Another order variant
  - `run_tests.py` Test P — Complex order with pet care

  **WHY Each Reference Matters**:
  - `process_request()`: The pre-fetch pipeline is inserted here, transforming the request before the agent sees it
  - Tool function signatures: Need to know exact parameters to call tools programmatically in pre-fetch
  - Test cases: Each test represents a different pre-fetch pattern — studying them reveals which tools are typically needed together

  **Acceptance Criteria**:
  - [ ] Pre-fetch function exists that parses requests and calls tools in parallel
  - [ ] Pre-fetched data injected into LLM context
  - [ ] LLM round-trips reduced (observable via fewer tool calls in agent logs)
  - [ ] Fallback to normal agent behavior if parsing fails
  - [ ] Code imports cleanly: `python -c "import pet_store_agent.pet_store_agent"`

  **QA Scenarios**:
  ```
  Scenario: Pre-fetch reduces tool calls for standard order
    Tool: Bash (python)
    Preconditions: Pre-fetch pipeline added, agent deployed
    Steps:
      1. Add temporary logging to count LLM round-trips
      2. Process a standard order request (Test A pattern)
      3. Count LLM round-trips — should be 1-2 instead of 4-7
      4. Verify response is still correct
    Expected Result: 1-2 LLM round-trips, correct order response
    Failure Indicators: Still 4+ round-trips, incorrect response, pre-fetch error
    Evidence: .sisyphus/evidence/task-6-prefetch-roundtrips.txt

  Scenario: Fallback works when parsing fails
    Tool: Bash (python)
    Preconditions: Pre-fetch pipeline added
    Steps:
      1. Send an ambiguous request that the parser can't classify
      2. Verify the agent still processes it correctly via normal tool-calling path
    Expected Result: Agent falls back to normal behavior, correct response
    Failure Indicators: Error thrown, no response, wrong response
    Evidence: .sisyphus/evidence/task-6-prefetch-fallback.txt
  ```

  **Commit**: YES
  - Message: `perf(agent): pre-fetch tool data to reduce LLM round-trips`
  - Files: `pet_store_agent/pet_store_agent.py`

- [x] 7. Deploy Optimized Agent + Full Benchmark Validation

  **What to do**:
  - Deploy the optimized agent using `./redeploy.sh`
  - Wait for deployment to complete (script handles this)
  - Run the full benchmark: `python run_tests.py`
  - Validate:
    - All 10 tests pass
    - Total wall time < 60s
    - No single test > 15s
  - If any test fails:
    - Identify which optimization caused the failure (check git log for recent changes)
    - If model swap caused it: try Nova Lite as alternative, or revert to Sonnet with other optimizations (still significant speedup)
    - If router caused it: check for false positives, adjust patterns
    - If pre-fetch caused it: check if data injection format is wrong
  - Save full benchmark output as evidence
  - If benchmark passes but is >60s, identify the slowest tests and investigate further

  **Must NOT do**:
  - Skip the benchmark — this is the entire success metric
  - Accept failures without investigation
  - Deploy without all prior tasks completed
  - Modify tests to make them pass (that defeats the purpose)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Deployment and validation — run scripts, check output, no complex coding
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (solo)
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: Tasks 2, 3, 4, 5, 6 (all optimizations must be in place)

  **References**:

  **Pattern References**:
  - `redeploy.sh` — Deployment script. Understand what it does: sets env vars, runs agentcore CLI deploy
  - `run_tests.py` — Benchmark harness (now with parallel execution from Task 3)

  **WHY Each Reference Matters**:
  - `redeploy.sh`: Must be run from correct directory, may need env vars set. Understanding the script prevents deployment issues
  - `run_tests.py`: This is the final validation tool — must know how to interpret its output

  **Acceptance Criteria**:
  - [ ] `./redeploy.sh` exits with code 0
  - [ ] `python run_tests.py` → 10/10 tests pass
  - [ ] `python run_tests.py` → total wall time < 60s
  - [ ] No single test > 15s
  - [ ] Benchmark output saved as evidence

  **QA Scenarios**:
  ```
  Scenario: Full deployment and benchmark validation
    Tool: Bash
    Preconditions: All Tasks 1-6 completed and committed
    Steps:
      1. Run `./redeploy.sh` — expect exit code 0
      2. Wait 30s for deployment to propagate
      3. Run `python run_tests.py` — capture full output
      4. Parse output: count PASS results (expect 10)
      5. Parse total time (expect < 60s)
      6. Parse per-test times (expect all < 15s)
      7. Save full output to evidence
    Expected Result: Deploy succeeds, 10/10 PASS, total < 60s
    Failure Indicators: Deploy fails, any test FAIL, total > 60s, any single test > 15s
    Evidence: .sisyphus/evidence/task-7-final-benchmark.txt

  Scenario: Identify regression source if tests fail
    Tool: Bash
    Preconditions: Benchmark shows failures
    Steps:
      1. If test fails, check which test
      2. If rejection test (C/U/N/F) fails → router issue (Task 5)
      3. If order test (A/B/E/K/Y/P) fails → model swap (Task 4) or pre-fetch (Task 6) issue
      4. Try reverting the suspected change and re-deploying
      5. Re-run benchmark to confirm fix
    Expected Result: Identify root cause of any failure
    Failure Indicators: Cannot isolate the failing change
    Evidence: .sisyphus/evidence/task-7-regression-analysis.txt
  ```

  **Commit**: YES (if any fixes needed)
  - Message: `perf(deploy): deploy optimized agent and validate benchmark`
  - Files: varies (depends on what needs fixing)
  - Pre-commit: `./redeploy.sh && python run_tests.py` (10/10 pass, <60s)

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run `python run_tests.py`). For each "Must NOT Have": search codebase for forbidden patterns (Lambda changes, KB data changes, new dependencies, test criteria changes). Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Review all changed files for: `as any`/`@ts-ignore` equivalents, empty except blocks, print statements left in prod code, commented-out code, unused imports. Check for AI slop: excessive comments, over-abstraction, generic variable names. Run `python test_pricing.py` to verify unit tests still pass.
  Output: `Pricing Tests [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Run `./redeploy.sh` then `python run_tests.py`. Verify: (a) all 10 tests pass, (b) total time < 60s, (c) no single test > 15s. Capture full output. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Tests [10/10 pass] | Total Time [Xs] | Max Single [Xs] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (`git diff`). Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Flag any Lambda changes, KB changes, new pip packages, or test criteria changes.
  Output: `Tasks [N/N compliant] | Scope Violations [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

| Commit | Message | Files | Pre-commit Check |
|--------|---------|-------|-----------------|
| 1 | `perf(agent): capture baseline timing in benchmark` | `run_tests.py` | `python run_tests.py` (10/10 pass) |
| 2 | `perf(tools): singleton boto3 clients for all tool modules` | `retrieve_product_info.py`, `retrieve_pet_care.py`, `inventory_management.py`, `user_management.py` | N/A (deployed code) |
| 3 | `perf(bench): parallel test execution with timing output` | `run_tests.py` | `python run_tests.py` (10/10 pass) |
| 4 | `perf(agent): singleton agent + Haiku 4.5 model + config tuning` | `pet_store_agent.py` | N/A (deployed code) |
| 5 | `perf(agent): deterministic router for rejection cases` | `pet_store_agent.py` | N/A (deployed code) |
| 6 | `perf(agent): pre-fetch tool data to reduce LLM round-trips` | `pet_store_agent.py` | N/A (deployed code) |
| 7 | `perf(deploy): deploy optimized agent and validate benchmark` | — | `./redeploy.sh && python run_tests.py` (10/10 pass, <60s) |

---

## Success Criteria

### Verification Commands
```bash
python run_tests.py          # Expected: 10/10 tests pass, total time < 60s
python test_pricing.py        # Expected: all unit tests pass
./redeploy.sh                # Expected: exit code 0
```

### Final Checklist
- [ ] All 10 tests pass (A, B, C, U, N, E, F, Y, K, P)
- [ ] Total benchmark time < 60s
- [ ] No single test > 15s
- [ ] No Lambda function changes
- [ ] No KB data changes
- [ ] No new pip dependencies
- [ ] No test criteria changes
- [ ] Per-test timing output available
- [ ] Each optimization layer has its own commit
