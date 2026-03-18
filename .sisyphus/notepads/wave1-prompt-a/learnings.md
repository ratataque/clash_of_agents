## Learnings


## Task 2: response_formatter.py Creation

### Key Insights
1. **@tool Docstring Pattern**: The docstring is REQUIRED for Strands framework to auto-generate parameter schema. Must use `Args:` section with dash-prefixed descriptions.
2. **Return Format**: Strands tools MUST return `{"status": "success", "content": [{"text": json.dumps(...)}]}`. The framework auto-adds toolUseId.
3. **Snake to Camel Case Mapping**: Python function uses snake_case params (customer_type, items_json, etc.) but output JSON uses camelCase keys (customerType, itemsJson, etc.). This mapping must be explicit in the response dict construction.
4. **JSON Parsing in Tools**: Pass items as JSON string parameter, then parse with json.loads() inside the tool. This ensures Strands can serialize the parameter properly.
5. **Tool Pattern Consistency**: Follow inventory_management.py pattern exactly: imports, logger setup, try-except with logging, same return structure for both success and error cases.

### File Created
- `pet_store_agent/response_formatter.py` (61 lines)
- Contains `format_order_response()` @tool with full parameter docs
- Both QA tests pass: Accept scenario with items, Reject scenario with empty items

### Parameter Mapping Reference
- `status` → `status`
- `message` → `message`
- `customer_type` (param) → `customerType` (output)
- `items_json` (param, string) → `items` (output, parsed array)
- `shipping_cost` (param) → `shippingCost` (output)
- `subtotal` → `subtotal`
- `additional_discount` (param) → `additionalDiscount` (output)
- `total` → `total`
- `pet_advice` (param, default="") → `petAdvice` (output)

### No Dependencies
This tool is self-contained and doesn't depend on other modules. Ready for Task 3 (orchestrator agent integration).


## Task 3: pet_store_agent.py Orchestrator Rewrite

### Key Insights
1. The Strands Agent constructor in this environment accepts the tools list but does not expose a public `tools` attribute, so verification that inspects `agent.tools` needs the module to attach that list after construction.
2. Wave 1 orchestration works best with a tightly constrained system prompt that forces the sequence retrieve_product_info -> get_inventory -> calculate_order_pricing -> format_order_response and forbids manual math/JSON.
3. The required environment-variable validation can stay unchanged even though Wave 1 does not call pet care or user tools, preserving compatibility with the existing runtime configuration contract.
