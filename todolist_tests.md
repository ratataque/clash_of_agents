# Test Todo List (Orchestrator + Micro-Agents)

## Global Non-Regression Checklist

- [x] Deploy latest runtime with `./deploy_with_env.sh pet_store_agent pet_store_agent/.env`
- [x] Validate env vars are current (KB IDs + Lambda function names)
- [x] Run targeted tests for changed behavior
- [x] Run full suite `./test_runtime.sh`
- [x] Review `evaluation-results.json` and update this file

## Per-Test Tracking

### A — Basic Pricing (DD006, guest)
- [x] Product parsing for name-based request
- [x] Inventory function call for `DD006`
- [x] Pricing tool output (shipping = 14.95)
- [x] Expected status/customerType fields

### B — Subscription + Advice (usr_001, BP010)
- [x] Customer function call (`usr_001`) and active subscription detection
- [x] Quantity extraction (2 units)
- [x] Bundle discount tool output (`0.10`)
- [x] Pet-care retrieval only when advice needed

### C — Prompt Injection
- [x] Injection detection in safety agent
- [x] Guaranteed `Reject` without internal prompt disclosure

### T — Multi-item (CM001 x2, DB002 x1)
- [x] Multi-item parsing
- [x] Per-item inventory checks
- [x] Pricing for mixed quantities and shipping

### N — Unsupported Product (hamster)
- [x] Out-of-scope species detection
- [x] Guaranteed `Reject`

### E — Expired Subscription (usr_003)
- [x] User lookup for `usr_003`
- [x] Expired subscription mapped to `Guest`
- [x] Accept flow still works

### F — Non-cat/dog (bird seed)
- [x] Out-of-scope detection for parrot/bird requests
- [x] Guaranteed `Reject`

### U — Unethical Request
- [x] Harm/cruelty intent detection
- [x] Guaranteed `Reject`

### Y — Missing Inventory Data (XYZ999)
- [x] Unknown product code handling
- [x] Inventory error path returns graceful `Error` message

### K — Bulk Order (PT003 x10)
- [x] Quantity extraction for bulk request
- [x] Bundle discount and totals from pricing tool
- [x] Shipping rule validation from subtotal

### P — Unavailable + Advice
- [x] Sold-out/unavailable handling returns `Reject`
- [x] Ensure no pet advice in reject response
