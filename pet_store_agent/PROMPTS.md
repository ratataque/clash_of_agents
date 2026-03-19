# Agent Prompt Architecture

## Overview

The PetStore agent uses a **microservice orchestration pattern** with XML-structured prompts for each specialist agent. All prompts are designed for:
- **Precision**: Exact input/output contracts and business rules
- **Observability**: Logged at each phase for debugging and auditing
- **Determinism**: Code-driven logic, not LLM reasoning
- **Testability**: Clear success/failure conditions

---

## Orchestrator

**Role**: Master coordinator for commerce requests  
**Model**: `anthropic.claude-3-7-sonnet-20250219-v1:0`

**Responsibilities**:
- Coordinate specialist agents in optimal sequence
- Handle error propagation and graceful degradation
- Ensure response compliance with JSON schema
- Log execution flow for observability

**Invocation Order**:
1. Safety → Block malicious requests
2. Customer → Resolve identity and subscription
3. Product → Extract product codes/names + quantities
4. Inventory → Validate stock for each item
5. Pricing → Calculate totals with business rules
6. Advice → Fetch guidance for subscribed customers (optional)

**Response Contract**:
```json
{
  "status": "Accept|Reject|Error",
  "message": "Customer-facing message",
  "customerType": "Guest|Subscribed",
  "items": [...],
  "shippingCost": 14.95,
  "petAdvice": "",
  "subtotal": 0.0,
  "additionalDiscount": 0.0,
  "total": 0.0
}
```

---

## Safety Agent

**Role**: Security guardrail layer  
**Model**: Pattern-based (no LLM invocation - code execution only)

**Threat Tiers**:
- **Critical**: Prompt injection, data exfiltration (13+9 patterns)
- **High**: Unsafe content (harm animals) (7 patterns)
- **Medium**: Out-of-scope species (hamster, parrot, etc.) (12 patterns)
- **Low**: Non-commerce advice requests

**Detection Strategy**:
- Unicode normalization + zero-width char removal
- Fail-fast regex matching on normalized text
- Combined analysis of raw prompt + customer request

**Output**:
```python
GuardrailDecision(
    blocked=True|False,
    code="prompt-injection|data-exfiltration|unsafe-request|out-of-scope-species|non-commerce-advice",
    message="Sorry! We can't accept your request. What else do you need?",
    matched_patterns=["pattern1", "pattern2"],
    severity="critical|high|medium|low"
)
```

---

## Customer Agent

**Role**: Identity and subscription resolver  
**Integration**: `user_management` Lambda

**Input Patterns**:
- `CustomerId: usr_XXX`
- `Email Address: user@domain.com`
- `User usr_XXX is inquiring...`
- Implicit: "A new user" → defaults to Guest

**Resolution Logic**:
1. Parse prompt for explicit identifiers
2. If found, invoke user service Lambda
3. If not found or service error, default to Guest
4. Return `CustomerContext` with subscription flag

**Subscription Rules**:
- Only "active" subscriptions → `Subscribed` customer type
- Expired subscriptions → downgrade to `Guest`
- Pet advice requires active subscription

**Output**:
```python
CustomerContext(
    customer_type="Guest|Subscribed",
    name=Optional[str],
    user_id=Optional[str],
    email=Optional[str],
    is_subscribed=bool
)
```

---

## Product Agent

**Role**: Product identification with Knowledge Base fuzzy matching  
**Integration**: Bedrock Knowledge Base 1 (product catalog)

**Extraction Strategy**:
1. **Explicit codes**: Scan for `[A-Z]{2}\d{3}` pattern (DD006, BP010, etc.)
2. **Natural language**: Extract product names/descriptions
3. **Quantity parsing**: Numbers or words (one, two, three...)

**KB Matching Algorithm**:
```
Score = similarity(phrase, name) * 0.45
      + token_overlap(phrase, name) * 0.35
      + token_overlap(phrase, description) * 0.35
      + token_overlap(phrase, snippet) * 0.45

Threshold: score >= 0.17
```

**Critical Rules**:
- ❌ NEVER use hardcoded product mappings
- ✅ ALWAYS query Knowledge Base for each request
- ✅ Support multi-item requests
- ✅ Return empty list if no matches (triggers Reject)

**Output**:
```python
List[RequestedItem(product_id=str, quantity=int)]
```

---

## Inventory Agent

**Role**: Stock validation and availability checker  
**Integration**: `inventory_management` Lambda

**Validation Flow**:
1. Invoke Lambda for each `product_id`
2. Check for service error → return `Error` status
3. Check `status == "out_of_stock"` → return `Reject`
4. Compare `quantity` vs requested → return `Reject` if insufficient
5. Calculate `replenishInventory` flag (projected stock <= reorder level)

**Error Handling**:
- Lambda timeout → Error status
- Service returns `{"error": "..."}` → Error status
- Product not found → Treat as out_of_stock

**Output**:
```python
{
    "name": "Product Name",
    "quantity": 50,
    "status": "in_stock",
    "reorder_level": 10,
    "replenishInventory": False  # projected > reorder_level
}
# OR
{"error": "Service unavailable"}
```

---

## Pricing Agent

**Role**: Deterministic pricing calculator  
**Tool**: `calculate_pricing_data()` (programmatic, not LLM)

**Business Rules**:

### 1. Bundle Discount
- **Condition**: `quantity >= 2` for any single product
- **Discount**: 10% (0.10)
- **Application**: `price * quantity * (1 - 0.10)`

### 2. Shipping Cost
- **Base rate**: $14.95
- **Free shipping**: `subtotal >= $300.00`

### 3. Additional Discount (Bulk Order)
- **Condition**: `subtotal >= $300.00`
- **Discount**: 15% (0.15) applied to subtotal
- **Note**: Separate from bundle discount (both can apply)

### 4. Calculation Sequence
```
1. Per-item totals = price × quantity × (1 - bundleDiscount)
2. Subtotal = sum(item totals)
3. Apply additional discount if subtotal >= $300
4. Add shipping ($14.95 or $0 if free)
5. Final total
```

**Critical Rules**:
- ❌ NEVER manually calculate pricing in code
- ✅ ALWAYS use `calculate_pricing_data()` tool
- ✅ Prices from KB retrieval, not hardcoded
- ✅ Round all values to 2 decimal places

**Output**:
```python
{
    "items": [
        {
            "productId": "DD006",
            "price": 54.99,
            "quantity": 1,
            "bundleDiscount": 0,      # No discount (qty=1)
            "total": 54.99,
            "replenishInventory": False
        }
    ],
    "shippingCost": 14.95,
    "subtotal": 54.99,
    "additionalDiscount": 0,
    "total": 69.94
}
```

---

## Advice Agent

**Role**: Pet care guidance provider  
**Integration**: Bedrock Knowledge Base 2 (pet care advice)

**Eligibility**:
- ✅ Customer has `is_subscribed=True`
- ✅ Request contains advice-seeking intent markers

**Intent Markers**:
- "suitable for", "bathing my dog"
- "tips for", "advice for", "help with"
- "how often", "how long", "recommended"
- "is it safe", "can I use", "should I"

**KB Retrieval**:
1. Check `is_subscribed` flag
2. Check `_needs_pet_advice(customer_request)`
3. If both true, query KB2 with full customer request
4. Extract and concatenate top passages (max 200 words)
5. Return as `petAdvice` field

**Output**:
- Guest customer → `""`
- Subscribed, no intent → `""`
- Subscribed, with intent → KB-sourced guidance text

---

## Prompt Enhancement Features

### 1. **Structured XML Contracts**
Each agent has explicit:
- Role definition
- Goal statement
- Input/output schemas
- Business rules with priorities
- Error handling strategies

### 2. **Observability**
- Logged at each phase: `logger.info(AGENT_PROMPT_XML)`
- Enables CloudWatch correlation with request outcomes
- Supports debugging with exact agent invocation sequence

### 3. **Fail-Fast Design**
- Safety checks BEFORE customer resolution
- Inventory validation BEFORE pricing calculation
- Reduces wasted computation on doomed requests

### 4. **Deterministic Execution**
- Code/tools handle all logic (not LLM reasoning)
- Reproducible results for same inputs
- Testable without LLM variance

### 5. **Priority Annotations**
Rules marked as:
- `critical`: Must never violate (security, correctness)
- `high`: Important for business logic
- `medium`: Best practice, optimization
- `low`: Nice-to-have, observability

---

## Testing Agent Prompts

```bash
# Test local execution with all prompts
cd /Users/grimaldev/Code/Projects/innovation_day_2026
python - <<'PY'
import sys
sys.path.insert(0, 'pet_store_agent')
import pet_store_agent as a

# Test orchestrator loads all prompts
print("Testing agent prompt loading...")
prompts = [
    ("ORCHESTRATOR", a.ORCHESTRATOR_PROMPT_XML),
    ("SAFETY", a.SAFETY_PROMPT_XML),
    ("CUSTOMER", a.CUSTOMER_PROMPT_XML),
    ("PRODUCT", a.PRODUCT_PROMPT_XML),
    ("INVENTORY", a.INVENTORY_PROMPT_XML),
    ("PRICING", a.PRICING_PROMPT_XML),
    ("ADVICE", a.ADVICE_PROMPT_XML),
]
for name, prompt in prompts:
    lines = prompt.strip().split('\n')
    print(f"✅ {name:12} {len(lines):3} lines, {len(prompt):4} chars")
PY
```

---

## Deployment

Enhanced prompts are **automatically included** in runtime deployment:

```bash
./deploy_with_env.sh pet_store_agent pet_store_agent/.env
```

No changes to infrastructure or Lambda configuration needed.

---

## Future Enhancements

1. **Dynamic Prompt Loading**: Load from S3 for zero-downtime updates
2. **A/B Testing**: Compare prompt variants with split traffic
3. **Prompt Versioning**: Track prompt evolution with Git-like diffs
4. **Semantic Validation**: Ensure prompts match actual code behavior
5. **Multi-language Support**: Localized prompts for international customers
