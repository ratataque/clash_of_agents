# Wave 1: Pass Prompt A — Multi-Agent Pet Store Orchestrator

## TL;DR

> **Quick Summary**: Replace the monolithic pet store agent with a multi-agent orchestrator pattern. Wave 1 focuses exclusively on passing Prompt A (basic product pricing inquiry for Doggy Delights DD006) at 50/50 points. The orchestrator delegates to specialized tools for intent classification, pricing calculation, and response formatting — keeping the LLM's job simple and the math deterministic.
> 
> **Deliverables**:
> - Orchestrator agent (`pet_store_agent.py` rewritten) that coordinates the flow
> - Deterministic pricing calculator tool (`pricing.py`)
> - Deterministic response formatter tool (`response_formatter.py`)
> - Updated entrypoints (`agentcore_entrypoint.py`, `lambda_function.py`)
> - Deployed and passing `run_test_a.py` at 50/50
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 2 waves
 > **Critical Path**: Task 1 | Task 2 (parallel) → Task 3 (orchestrator) → Task 4 (entrypoints + deploy) → Task 5 (test & fix)

---

## Context

### Original Request
Build a multi-agent pet store customer service system using the Strands Agents SDK deployed on AWS Bedrock AgentCore. The architecture should be an orchestrator pattern with specialized sub-agents and deterministic tools. Wave 1 targets passing Prompt A only.

### Interview Summary
**Key Discussions**:
- Architecture: Orchestrator agent delegates to sub-agents/tools, aggregates results, responds
- "Each agent should have one simple task and tools appropriated"
- "If the task can be done programmatically we can make a tool instead of an agent"
- "Create the first wave to pass the first prompt"
- "We do not care about other tests than test A for now, keep it simple"

**Research Findings**:
- Current monolithic agent scores only 10/50 on Prompt A — returns `status: "Error"` instead of `Accept`
- Root cause: the LLM is doing ALL the work (math, formatting, business rules) and failing
- Strands SDK supports `@tool` decorator pattern (used by inventory_management.py, user_management.py) and `TOOL_SPEC` module pattern (used by retrieve_product_info.py, retrieve_pet_care.py)
- Existing tools (KB retrieval, inventory, user management) work fine and should be reused as-is
- The system prompt's Sample 1 is literally Prompt A — the expected output is in the codebase

### Metis Review
**Identified Gaps** (addressed):
- For Wave 1, intent classification can be skipped — the orchestrator's system prompt can handle Prompt A directly without a separate intent tool
- Pricing calculator must be deterministic Python — no LLM involvement in math
- Response formatter ensures JSON schema compliance — prevents the "Error" status that plagues the current agent
- Simplicity is key: don't over-engineer for Wave 1, just pass Prompt A

---

## Work Objectives

### Core Objective
Replace the monolithic `pet_store_agent.py` with an orchestrator pattern that uses deterministic tools for pricing and response formatting, passing Prompt A at 50/50 points.

### Concrete Deliverables
- `pet_store_agent/pricing.py` — Deterministic pricing calculator tool
- `pet_store_agent/response_formatter.py` — Deterministic response JSON builder tool
- `pet_store_agent/pet_store_agent.py` — Rewritten as orchestrator agent
- `pet_store_agent/agentcore_entrypoint.py` — Updated (minimal change)
- `pet_store_agent/lambda_function.py` — Updated (minimal change)

### Definition of Done
- [ ] `python run_test_a.py` passes all 6 checks (status=Accept, customerType=Guest, has items, shippingCost=14.95, productId=DD006, price=54.99)
- [ ] No regression: `python run_evaluation.py` shows Prompt A score = 50/50

### Must Have
- Deterministic pricing calculation (no LLM math)
- Deterministic response JSON building (no LLM JSON formatting)
- Orchestrator uses existing `retrieve_product_info` tool for product lookup
- Orchestrator uses existing `get_inventory` tool for inventory check
- Response matches expected schema exactly
- `shippingCost` = 14.95 (order under $75, single item)
- `bundleDiscount` = 0 (single item, no bundle)
- `additionalDiscount` = 0 (order under $300)
- `subtotal` = item total + shipping = 69.94
- `total` = 69.94

### Must NOT Have (Guardrails)
- NO intent classification agent/tool in Wave 1 — keep it simple
- NO user management calls in Wave 1 — Prompt A is a guest, no user lookup needed
- NO pet care KB calls in Wave 1 — no advice needed for guests
- NO changes to existing tools (retrieve_product_info.py, retrieve_pet_care.py, inventory_management.py, user_management.py) — they work fine
- NO over-engineering for future prompts — Wave 1 is ONLY about Prompt A
- NO complex multi-agent delegation framework — the orchestrator is just a Strands Agent with better tools
- NO hardcoded Prompt A responses — the agent must actually use tools to look up product info and calculate pricing (it needs to generalize later)

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (no unit test framework)
- **Automated tests**: None (we use `run_test_a.py` as the acceptance test)
- **Framework**: None
- **QA Method**: Deploy to AgentCore → run `run_test_a.py` → verify all checks pass

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Tool code**: Use Bash (python REPL) — Import, call functions with test data, compare output
- **Deployed agent**: Use Bash (python run_test_a.py) — End-to-end test against deployed agent

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — independent tools):
├── Task 1: Pricing calculator tool [quick]
├── Task 2: Response formatter tool [quick]

Wave 2 (After Wave 1 — orchestrator + integration):
├── Task 3: Rewrite orchestrator agent (depends: 1, 2) [unspecified-high]
├── Task 4: Update entrypoints + deploy (depends: 3) [quick]
├── Task 5: Test against Prompt A + fix loop (depends: 4) [deep]

Wave FINAL (After ALL tasks — verification):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real QA — run_test_a.py (unspecified-high)
├── Task F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 3 |
| 2 | — | 3 |
| 3 | 1, 2 | 4 |
| 4 | 3 | 5 |
| 5 | 4 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: **2 tasks** — T1 → `quick`, T2 → `quick`
- **Wave 2**: **3 tasks** — T3 → `unspecified-high`, T4 → `quick`, T5 → `deep`
- **FINAL**: **4 tasks** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Create deterministic pricing calculator tool (`pricing.py`)

  **What to do**:
  - Create `pet_store_agent/pricing.py` with a `@tool`-decorated function `calculate_order_pricing`
  - The tool takes structured item data and returns a complete pricing breakdown
  - All math must use Python floats with explicit rounding to 2 decimal places (use `round(x, 2)`)
  - Implement these business rules:
    - **Bundle discount**: When `quantity > 1` for a single item, apply 10% discount. Calculation: first unit at full price, each additional unit gets 10% off. So for qty=2 at $16.99: total = 16.99 + (16.99 * 0.90) = 16.99 + 15.291 = 32.281 → round to 32.28. The `bundleDiscount` field in the response is always `0.10` (the rate) when qty > 1, else `0`
    - **Shipping**: If subtotal (sum of all item totals) >= $75: free ($0). If subtotal < $75 AND total item count <= 2: $14.95. If subtotal < $75 AND total item count >= 3: $19.95
    - **Additional discount**: If subtotal > $300: 15% off subtotal (additionalDiscount = 0.15). Else additionalDiscount = 0
    - **Subtotal** = sum of item totals + shipping cost
    - **Total** = subtotal - (subtotal * additionalDiscount) ... wait, re-check the sample: item total=54.99, shipping=14.95, subtotal=69.94, additionalDiscount=0, total=69.94. So subtotal = item_total + shipping. total = subtotal - discount_amount.
  - For Prompt A specifically: 1x DD006 at $54.99 → bundleDiscount=0, item total=54.99, shipping=14.95 (under $75, 1 item), subtotal=69.94, additionalDiscount=0, total=69.94
  - The `replenishInventory` flag: true if (current_stock - order_qty) <= reorder_level. This requires inventory data passed in.
  - Tool signature: `calculate_order_pricing(items: str) -> dict` where items is a JSON string of `[{"product_id": "DD006", "price": 54.99, "quantity": 1, "current_stock": 150, "reorder_level": 50}]`
  - Return format: `{"status": "success", "content": [{"text": json.dumps(result)}]}` where result contains `items`, `shippingCost`, `subtotal`, `additionalDiscount`, `total`

  **Must NOT do**:
  - Do NOT use Decimal — keep it simple with float + round()
  - Do NOT add complex abstractions or classes
  - Do NOT handle multi-product orders beyond what the interface supports (but do support it in the data structure)
  - Do NOT import or depend on any other project files

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, pure Python, deterministic logic — straightforward implementation
  - **Skills**: [`coding-standards`]
    - `coding-standards`: Clean Python patterns, proper docstrings
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: This is a pure function, not an API/server pattern

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3 (orchestrator needs this tool)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `pet_store_agent/inventory_management.py:9-41` — `@tool` decorator pattern with docstring that becomes tool description. Follow this exact pattern: `@tool` decorator, type-hinted params, descriptive docstring with Args section
  - `pet_store_agent/user_management.py:9-47` — Another `@tool` example showing parameter handling

  **API/Type References** (contracts to implement against):
  - `pet_store_agent/pet_store_agent.py:46-65` — Sample 1 Response showing exact expected output structure for Prompt A: items array with productId/price/quantity/bundleDiscount/total/replenishInventory, plus shippingCost/petAdvice/subtotal/additionalDiscount/total at order level
  - `pet_store_agent/pet_store_agent.py:94-175` — Full JSON response schema the output must conform to

  **Business Rules Reference**:
  - `pet_store_agent/pet_store_agent.py:36-40` — Exact business rules text: discount thresholds, shipping tiers, bundle discount, inventory replenishment flag logic

  **External References**:
  - Strands `@tool` decorator: returns `{"status": "success", "content": [{"text": ...}]}` and Strands auto-adds `toolUseId`. Docstring first line → description, `Args:` section → parameter descriptions in schema. Type hints → schema types.

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Single item pricing (Prompt A case)
    Tool: Bash (python3 -c)
    Preconditions: pricing.py exists in pet_store_agent/
    Steps:
      1. cd pet_store_agent && python3 -c "
         import json
         from pricing import calculate_order_pricing
         # Simulate tool call with Prompt A data
         result = calculate_order_pricing(items=json.dumps([{'product_id': 'DD006', 'price': 54.99, 'quantity': 1, 'current_stock': 150, 'reorder_level': 50}]))
         data = json.loads(result['content'][0]['text'])
         assert data['items'][0]['bundleDiscount'] == 0, f'bundleDiscount={data[\"items\"][0][\"bundleDiscount\"]}'
         assert data['items'][0]['total'] == 54.99, f'item total={data[\"items\"][0][\"total\"]}'
         assert data['items'][0]['replenishInventory'] == False
         assert data['shippingCost'] == 14.95, f'shipping={data[\"shippingCost\"]}'
         assert data['subtotal'] == 69.94, f'subtotal={data[\"subtotal\"]}'
         assert data['additionalDiscount'] == 0
         assert data['total'] == 69.94, f'total={data[\"total\"]}'
         print('PASS: Single item pricing correct')
         "
    Expected Result: Prints "PASS: Single item pricing correct" with exit code 0
    Failure Indicators: AssertionError with mismatched values, ImportError
    Evidence: .sisyphus/evidence/task-1-single-item-pricing.txt

  Scenario: Bundle discount pricing (qty > 1)
    Tool: Bash (python3 -c)
    Preconditions: pricing.py exists in pet_store_agent/
    Steps:
      1. cd pet_store_agent && python3 -c "
         import json
         from pricing import calculate_order_pricing
         result = calculate_order_pricing(items=json.dumps([{'product_id': 'BP010', 'price': 16.99, 'quantity': 2, 'current_stock': 100, 'reorder_level': 30}]))
         data = json.loads(result['content'][0]['text'])
         assert data['items'][0]['bundleDiscount'] == 0.10
         assert data['items'][0]['total'] == 32.28, f'expected 32.28, got {data[\"items\"][0][\"total\"]}'
         assert data['shippingCost'] == 14.95
         print('PASS: Bundle discount correct')
         "
    Expected Result: Prints "PASS: Bundle discount correct" with exit code 0
    Evidence: .sisyphus/evidence/task-1-bundle-discount.txt
  ```

  **Commit**: YES (group 1)
  - Message: `feat(pricing): add deterministic pricing calculator tool`
  - Files: `pet_store_agent/pricing.py`

- [x] 2. Create deterministic response formatter tool (`response_formatter.py`)

  **What to do**:
  - Create `pet_store_agent/response_formatter.py` with a `@tool`-decorated function `format_order_response`
  - The tool takes structured data (status, message, customerType, items, pricing, petAdvice) and builds the exact JSON response matching the schema
  - This tool ensures the LLM never has to manually construct JSON — it just provides the semantic data and this tool formats it
  - Parameters (all as simple types the LLM can provide):
    - `status: str` — "Accept", "Reject", or "Error"
    - `message: str` — customer-facing message (max 250 chars)
    - `customer_type: str` — "Guest" or "Subscribed"
    - `items_json: str` — JSON string of items array from pricing tool output
    - `shipping_cost: float` — from pricing tool
    - `pet_advice: str` — pet care advice (empty string if none), default=""
    - `subtotal: float` — from pricing tool
    - `additional_discount: float` — from pricing tool (the rate, 0 or 0.15)
    - `total: float` — from pricing tool
  - The tool returns the complete response JSON as a string (the orchestrator will return this directly)
  - Return format: `{"status": "success", "content": [{"text": json.dumps(response_dict)}]}`

  **Must NOT do**:
  - Do NOT add validation beyond basic type checking
  - Do NOT import or depend on other project files
  - Do NOT add business logic — this is purely formatting

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file, simple data transformation, no complex logic
  - **Skills**: [`coding-standards`]
    - `coding-standards`: Clean Python patterns
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: Not an API endpoint

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3 (orchestrator needs this tool)
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `pet_store_agent/inventory_management.py:9-41` — `@tool` decorator pattern to follow
  - `pet_store_agent/pet_store_agent.py:46-65` — Sample 1 Response: the exact JSON structure this formatter must produce
  - `pet_store_agent/pet_store_agent.py:72-91` — Sample 2 Response: another example of the output structure

  **API/Type References**:
  - `pet_store_agent/pet_store_agent.py:94-175` — Full JSON response schema: required fields are `status` and `message`, optional fields include `customerType`, `items`, `shippingCost`, `petAdvice`, `subtotal`, `additionalDiscount`, `total`

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Format Prompt A response
    Tool: Bash (python3 -c)
    Preconditions: response_formatter.py exists in pet_store_agent/
    Steps:
      1. cd pet_store_agent && python3 -c "
         import json
         from response_formatter import format_order_response
         result = format_order_response(
           status='Accept',
           message='Dear Customer! We offer our 30lb bag of Doggy Delights for just dollar 54.99.',
           customer_type='Guest',
           items_json=json.dumps([{'productId': 'DD006', 'price': 54.99, 'quantity': 1, 'bundleDiscount': 0, 'total': 54.99, 'replenishInventory': False}]),
           shipping_cost=14.95,
           subtotal=69.94,
           additional_discount=0,
           total=69.94
         )
         data = json.loads(result['content'][0]['text'])
         assert data['status'] == 'Accept'
         assert data['customerType'] == 'Guest'
         assert len(data['items']) == 1
         assert data['items'][0]['productId'] == 'DD006'
         assert data['shippingCost'] == 14.95
         assert data['subtotal'] == 69.94
         assert data['total'] == 69.94
         assert data['petAdvice'] == ''
         print('PASS: Response formatting correct')
         "
    Expected Result: Prints "PASS: Response formatting correct" with exit code 0
    Evidence: .sisyphus/evidence/task-2-format-response.txt

  Scenario: Missing optional fields handled gracefully
    Tool: Bash (python3 -c)
    Preconditions: response_formatter.py exists
    Steps:
      1. cd pet_store_agent && python3 -c "
         import json
         from response_formatter import format_order_response
         result = format_order_response(
           status='Reject',
           message='We are sorry, we only sell cat and dog products.',
           customer_type='Guest',
           items_json='[]',
           shipping_cost=0,
           subtotal=0,
           additional_discount=0,
           total=0
         )
         data = json.loads(result['content'][0]['text'])
         assert data['status'] == 'Reject'
         assert 'sorry' in data['message'].lower()
         print('PASS: Reject formatting correct')
         "
    Expected Result: Prints "PASS: Reject formatting correct" with exit code 0
    Evidence: .sisyphus/evidence/task-2-reject-format.txt
  ```

  **Commit**: YES (group 1)
  - Message: `feat(formatter): add response formatter tool`
  - Files: `pet_store_agent/response_formatter.py`

- [x] 3. Rewrite `pet_store_agent.py` as orchestrator agent

  **What to do**:
  - Rewrite `pet_store_agent/pet_store_agent.py` to be an orchestrator agent
  - The orchestrator is a Strands Agent with a focused system prompt and the right tools
  - **System prompt strategy**: Keep it simpler than the current monolith. The orchestrator should:
    1. Use `retrieve_product_info` to look up product information based on user query
    2. Use `get_inventory` to check stock levels for found products
    3. Use `calculate_order_pricing` with the product data to get deterministic pricing
    4. Use `format_order_response` to build the final JSON response
    5. Return the formatted JSON directly
  - **Tools to include**: `retrieve_product_info`, `get_inventory`, `calculate_order_pricing`, `format_order_response`
  - **Tools to EXCLUDE for Wave 1**: `retrieve_pet_care`, `get_user_by_id`, `get_user_by_email` — not needed for Prompt A (guest user, no pet advice)
  - **Keep the same public API**: `create_agent()` returns an Agent, `process_request(prompt)` processes a request
  - The system prompt must include:
    - Clear step-by-step execution plan (1. lookup product → 2. check inventory → 3. calculate pricing → 4. format response)
    - The business rules for status determination: Accept when product found and in stock, Reject when unavailable, Error on system issues
    - The rule that customerType is always "Guest" when no user ID/email is provided
    - Instruction to return ONLY the JSON from format_order_response, no wrapper text
    - The sample input/output from Prompt A (helps the LLM understand the expected flow)
  - **CRITICAL**: The system prompt should tell the agent to pass the product price and quantity to `calculate_order_pricing` and use its output for `format_order_response`. The LLM should NEVER do math itself.

  **Must NOT do**:
  - Do NOT include user management tools (get_user_by_id, get_user_by_email)
  - Do NOT include pet care retrieval (retrieve_pet_care)
  - Do NOT keep the old massive system prompt — write a new focused one
  - Do NOT add multi-agent framework or agent-as-tool patterns — this is just one Agent with good tools
  - Do NOT hardcode any product data or prices

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core orchestrator logic, system prompt engineering, integration of multiple tools — requires careful thought
  - **Skills**: [`coding-standards`]
    - `coding-standards`: Clean Python patterns
  - **Skills Evaluated but Omitted**:
    - `backend-patterns`: Not an API server, it's an agent

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential within wave)
  - **Blocks**: Task 4 (entrypoints depend on this)
  - **Blocked By**: Task 1 (pricing.py), Task 2 (response_formatter.py)

  **References**:

  **Pattern References**:
  - `pet_store_agent/pet_store_agent.py:178-200` — Current `create_agent()` function: shows how Agent is created with BedrockModel, system_prompt, and tools list. Keep this exact pattern but with new tools and prompt
  - `pet_store_agent/pet_store_agent.py:202-215` — Current `process_request()`: keep this exact interface, just point to new agent
  - `pet_store_agent/pet_store_agent.py:1-9` — Current imports: shows how tools are imported (module-level for TOOL_SPEC pattern, function-level for @tool pattern)

  **API/Type References**:
  - `pet_store_agent/pet_store_agent.py:16-176` — Current system prompt: contains all business rules, sample I/O, and response schema. Extract the relevant rules for the new focused prompt
  - `pet_store_agent/pet_store_agent.py:42-65` — Sample 1 (Prompt A): include this sample in the new system prompt so the LLM understands the expected flow

  **Tool References** (tools the orchestrator will use):
  - `pet_store_agent/retrieve_product_info.py:12-42` — TOOL_SPEC for product info retrieval: takes `text` query, returns product descriptions with scores
  - `pet_store_agent/inventory_management.py:9-41` — `get_inventory` tool: takes `product_code`, returns stock quantity, status, reorder_level
  - Task 1 output: `pet_store_agent/pricing.py` — `calculate_order_pricing` tool
  - Task 2 output: `pet_store_agent/response_formatter.py` — `format_order_response` tool

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Agent creates successfully with all tools
    Tool: Bash (python3 -c)
    Preconditions: All tool files exist, env vars set
    Steps:
      1. cd pet_store_agent && python3 -c "
         import os
         os.environ.setdefault('KNOWLEDGE_BASE_1_ID', 'test')
         os.environ.setdefault('KNOWLEDGE_BASE_2_ID', 'test')
         os.environ.setdefault('SYSTEM_FUNCTION_1_NAME', 'test')
         os.environ.setdefault('SYSTEM_FUNCTION_2_NAME', 'test')
         from pet_store_agent import create_agent
         agent = create_agent()
         tool_names = [t if isinstance(t, str) else getattr(t, 'tool_name', getattr(t, '__name__', str(t))) for t in agent.tools]
         print(f'Agent created with tools: {tool_names}')
         assert len(agent.tools) >= 3, f'Expected at least 3 tools, got {len(agent.tools)}'
         print('PASS: Agent creation successful')
         "
    Expected Result: Agent creates with retrieve_product_info, get_inventory, calculate_order_pricing, format_order_response tools
    Failure Indicators: ImportError, missing tools, wrong tool count
    Evidence: .sisyphus/evidence/task-3-agent-creation.txt

  Scenario: System prompt contains required elements
    Tool: Bash (python3 -c)
    Preconditions: pet_store_agent.py rewritten
    Steps:
      1. cd pet_store_agent && python3 -c "
         from pet_store_agent import system_prompt
         required = ['retrieve_product_info', 'get_inventory', 'calculate_order_pricing', 'format_order_response', 'Guest', 'Accept', 'JSON']
         for req in required:
           assert req.lower() in system_prompt.lower(), f'Missing in system prompt: {req}'
         print('PASS: System prompt contains all required elements')
         "
    Expected Result: All required keywords found in system prompt
    Evidence: .sisyphus/evidence/task-3-system-prompt.txt
  ```

  **Commit**: YES (group 2)
  - Message: `refactor(agent): replace monolithic agent with orchestrator pattern`
  - Files: `pet_store_agent/pet_store_agent.py`

- [x] 4. Update entrypoints and deploy

  **What to do**:
  - Verify `pet_store_agent/agentcore_entrypoint.py` still works with the rewritten `pet_store_agent.py` — it should since we kept the same `process_request()` interface. If imports changed, update them.
  - Verify `pet_store_agent/lambda_function.py` still works — same check.
  - Run `./deploy_with_env.sh pet_store_agent` to deploy the updated agent to AgentCore
  - Wait for deployment to complete successfully

  **Must NOT do**:
  - Do NOT change the entrypoint interface (payload handling)
  - Do NOT change the deployment script
  - Do NOT modify .env or .bedrock_agentcore.yaml

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verify 2 small files, run deploy command — minimal work
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - All: Simple file check + deploy command

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 3)
  - **Blocks**: Task 5 (testing requires deployed agent)
  - **Blocked By**: Task 3 (orchestrator must be complete)

  **References**:

  **Pattern References**:
  - `pet_store_agent/agentcore_entrypoint.py:1-13` — Current entrypoint: imports `pet_store_agent` module, calls `process_request()`. Should work as-is if the interface is preserved
  - `pet_store_agent/lambda_function.py:1-6` — Current Lambda handler: same pattern, imports `pet_store_agent`, calls `process_request()`
  - `deploy_with_env.sh:1-110` — Deployment script: reads .env, exports vars, runs `agentcore deploy` from agent directory

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Entrypoints import successfully
    Tool: Bash (python3 -c)
    Preconditions: pet_store_agent.py rewritten
    Steps:
      1. cd pet_store_agent && python3 -c "
         import os
         os.environ.setdefault('KNOWLEDGE_BASE_1_ID', 'test')
         os.environ.setdefault('KNOWLEDGE_BASE_2_ID', 'test')
         os.environ.setdefault('SYSTEM_FUNCTION_1_NAME', 'test')
         os.environ.setdefault('SYSTEM_FUNCTION_2_NAME', 'test')
         import pet_store_agent
         assert hasattr(pet_store_agent, 'process_request')
         assert hasattr(pet_store_agent, 'create_agent')
         print('PASS: Entrypoint imports work')
         "
    Expected Result: No import errors, both functions accessible
    Evidence: .sisyphus/evidence/task-4-imports.txt

  Scenario: Deploy to AgentCore
    Tool: Bash
    Preconditions: Agent code complete, .env configured
    Steps:
      1. ./deploy_with_env.sh pet_store_agent
      2. Wait for "deploy" command to complete (timeout: 5 minutes)
    Expected Result: Deployment succeeds with no errors
    Failure Indicators: "Error" in output, non-zero exit code
    Evidence: .sisyphus/evidence/task-4-deploy.txt
  ```

  **Commit**: YES (group 2)
  - Message: `chore(deploy): update entrypoints for orchestrator agent`
  - Files: `pet_store_agent/agentcore_entrypoint.py`, `pet_store_agent/lambda_function.py` (only if changes needed)

- [x] 5. Test against Prompt A and iterate until passing

  **What to do**:
  - Run `python run_test_a.py` against the deployed agent
  - If any check fails, analyze the response, identify the issue, fix the relevant file, redeploy, and retest
  - Common issues to watch for:
    - Agent returns raw text instead of JSON → fix system prompt to emphasize JSON-only output
    - Wrong shipping cost → fix pricing.py calculation
    - Status is "Error" → check agent logs, fix tool invocation
    - Missing items array → fix system prompt tool usage instructions
    - Wrong productId → fix how retrieve_product_info results are parsed
  - Iterate until ALL 6 checks pass: status=Accept, customerType=Guest, has items, shippingCost=14.95, productId=DD006, price=54.99
  - **Max iterations**: 5 deploy-test cycles. If still failing after 5, analyze root cause deeply before continuing.

  **Must NOT do**:
  - Do NOT hardcode the response
  - Do NOT modify run_test_a.py
  - Do NOT modify existing tools (retrieve_product_info.py, inventory_management.py, etc.)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Debugging loop requiring analysis of agent behavior, system prompt tuning, and iterative fixes — needs deep reasoning
  - **Skills**: [`coding-standards`]
    - `coding-standards`: Clean fixes, no hacks
  - **Skills Evaluated but Omitted**:
    - `tdd-workflow`: No test framework, using run_test_a.py as acceptance test

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 4, final implementation task)
  - **Blocks**: F1-F4 (final verification)
  - **Blocked By**: Task 4 (requires deployed agent)

  **References**:

  **Pattern References**:
  - `run_test_a.py:1-109` — The test script: sends Prompt A to deployed agent, checks 6 assertions. Line 16: prompt text. Lines 85-94: the exact checks. Lines 18-23: expected values
  - `run_evaluation.py:176-271` — Full scoring logic for Prompt A: 30% for status, 20% for customerType, 20% for items, 10% for shipping = need all 4

  **Debugging References**:
  - `pet_store_agent/pet_store_agent.py` — System prompt (the most likely thing to tune)
  - `pet_store_agent/pricing.py` — Pricing logic (if math is wrong)
  - `pet_store_agent/response_formatter.py` — Format issues (if JSON structure is wrong)
  - AgentCore logs: `aws logs get-log-events --log-group-name /aws/bedrock-agentcore/...` — for runtime errors

  **Acceptance Criteria**:

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Prompt A passes all checks
    Tool: Bash
    Preconditions: Agent deployed to AgentCore
    Steps:
      1. python run_test_a.py
      2. Verify output shows all 6 ✅ checks
      3. Verify final line says "PASS"
    Expected Result: 
      ✅ status=Accept
      ✅ customerType=Guest
      ✅ has items
      ✅ shippingCost=14.95
      ✅ productId=DD006
      ✅ price=54.99
      PASS
    Failure Indicators: Any ❌ check, "FAIL" at end, Error in response
    Evidence: .sisyphus/evidence/task-5-test-a-pass.txt

  Scenario: Agent returns valid JSON (not wrapped in markdown)
    Tool: Bash
    Preconditions: Agent deployed
    Steps:
      1. python run_test_a.py 2>&1 | head -20
      2. Check "Raw response" section — must be valid JSON, not wrapped in ```json blocks
    Expected Result: Raw response is clean JSON with status, message, customerType, items
    Evidence: .sisyphus/evidence/task-5-json-format.txt
  ```

  **Commit**: YES (group 3)
  - Message: `fix(agent): tune orchestrator to pass Prompt A at 50/50`
  - Files: Any files modified during fix iterations

---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Review all changed files for: bare except clauses, missing error handling, hardcoded values that should be configurable, unused imports. Check AI slop: excessive comments, over-abstraction, generic names (data/result/item/temp). Verify pricing math is correct by tracing through sample calculations.
  Output: `Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real QA — run_test_a.py** — `unspecified-high`
  Run `python run_test_a.py` against the deployed agent. All 6 checks must pass: status=Accept, customerType=Guest, has items, shippingCost=14.95, productId=DD006, price=54.99. Save full output to `.sisyphus/evidence/final-qa/test-a-output.txt`.
  Output: `Checks [6/6 pass] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  Verify: only the 5 deliverable files were modified/created. No changes to existing tools. No hardcoded Prompt A responses. No over-engineering beyond what's needed for Prompt A.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| Commit | Message | Files | Pre-commit |
|--------|---------|-------|------------|
| 1 | `feat(pricing): add deterministic pricing calculator tool` | `pet_store_agent/pricing.py` | `python -c "from pricing import calculate_order_pricing"` |
| 2 | `feat(formatter): add response formatter tool` | `pet_store_agent/response_formatter.py` | `python -c "from response_formatter import format_order_response"` |
| 3 | `refactor(agent): replace monolithic agent with orchestrator pattern` | `pet_store_agent/pet_store_agent.py`, `pet_store_agent/agentcore_entrypoint.py`, `pet_store_agent/lambda_function.py` | `python -c "from pet_store_agent import create_agent"` |
| 4 | `test(wave1): verify Prompt A passes at 50/50` | — (no file changes, deployment + test) | `python run_test_a.py` |

---

## Success Criteria

### Verification Commands
```bash
python run_test_a.py  # Expected: all 6 checks ✅, PASS
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] `run_test_a.py` passes with all 6 checks
- [ ] Prompt A scores 50/50 in full evaluation
