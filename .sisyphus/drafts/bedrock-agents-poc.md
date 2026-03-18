# Draft: Bedrock Multi-Agent PoC for Pet Product Inquiry

## Requirements (UPDATED - CRITICAL)

**ACTUAL SCOPE**: This is NOT a simple PoC - this is a **graded assessment** with 11 evaluation prompts worth 900 points total.

**Evaluation System**:
- **Prompt A** (50pts): Basic price inquiry (DD006)
- **Prompt B** (75pts): Subscription + advice eligibility (usr_001, BP010)
- **Prompt C** (75pts): Prompt injection detection (security)
- **Prompt T** (100pts): Multi-item order (CM001, DB002) with bundle discounts
- **Prompt N** (100pts): Unsupported product (decline properly)
- **Prompt E** (100pts): Expired subscription handling (usr_003, PM015)
- **Prompt F** (100pts): Non-cat/dog pets (decline, maintain focus)
- **Prompt U** (100pts): Unethical requests (reject immediately)
- **Prompt Y** (100pts): Missing inventory data (graceful error handling)
- **Prompt K** (100pts): Bulk conditional order with complex pricing (PT003)
- **Prompt P** (100pts): Unavailable dietary products + subscription advice (usr_002)

**Success Requirements** (UNIVERSAL):
- ✅ Accurate information from knowledge bases
- 🔒 Never expose internal system details (product codes, inventory levels, system prompts)
- 💬 Professional customer service tone
- 🛡️ Security: reject unauthorized access, prompt injections, jailbreaks
- 📊 Correct pricing: bundle discounts, subscription discounts, free shipping logic
- 🚫 Scope enforcement: cats/dogs only, ethical business practices
- 📉 Graceful error handling: missing data, API failures, unavailable products

**Critical New Requirements from Evaluation**:
1. **Customer Recognition**: Must identify by name when user_id or email provided
2. **Conditional Logic**: "If X is available, order Y quantity" (Prompt K)
3. **Casual Product Matching**: Map informal names → actual product IDs
4. **Complex Discount Stacking**: Bundle + additional discounts (Prompt K)
5. **Subscription Advice Rules**: Advice ONLY if subscription is active (not expired)
6. **Inventory Constraints**: Communicate available quantities when stock insufficient
7. **Ethical Guardrails**: Reject harmful/unethical requests (Prompt U)
8. **Zero Internal Exposure**: No product codes, no inventory numbers, no system errors in customer messages

## Research Findings

### AWS Resources Found

**Lambda Functions**:
- `team-PetStoreInventoryManagementFunction-UQszQA9YKKDn` (Python 3.12)
- `team-PetStoreUserManagementFunction-WeuPIhjofWMr` (Python 3.12)
- `team-EvaluatePromptingFunction-CjS9iM5TNrvP` (Python 3.12)

**S3 Buckets**:
- `team-databucketforknowledge-ixntv3yqclsm` - Contains product catalog PDFs

**Product Catalog** (15 products found):
- DD006: Doggy Delights - $54.99 (30lb grain-free dog food)
- CM001: Meow Munchies (wet cat food)
- DB002: Bark Bites (dog treats)
- PT003: Purr-fect Playtime (cat toy)
- WL004: Wag-a-licious (chew bones)
- KK005: Kitty Krunchers (cat treats)
- SS007: Scratch Sensation (scratching post)
- FF008: Fetch Frenzy (dog ball)
- CC009: Catnip Craze (catnip blend)
- BP010: Bark Park Buddy (water bottle)
- LL011: Litter Lifter (cat litter)
- PP012: Paw-some Pampering (shampoo set)
- FF013: Feline Fiesta (variety pack)
- CC014: Canine Carnival (puzzle toys)
- PM015: Paw-ty Mix (multi-pet treats)

**DynamoDB Status**: No direct access or tables not visible yet

**Bedrock Status**: No existing agents or knowledge bases found

## Technical Decisions (Finalized)

### Agent Architecture (Multi-Agent with Performance Optimization)

**Orchestrator Agent** (Supervisor with Routing Mode):
- **Model**: Fast model (Claude Haiku) for routing decisions
- **Responsibilities**: 
  - Intent classification (price inquiry, product info, user lookup, rejection scenarios)
  - Task delegation to specialists
  - Response aggregation and JSON formatting
- **Action Groups**: None (pure orchestration)
- **Knowledge Base**: None

**Specialist Agent #1: Knowledge Agent** (RAG-focused):
- **Model**: Fast model (Claude Haiku) - most queries are simple lookups
- **Responsibilities**:
  - Product information retrieval (name, description, price, ingredients)
  - Pet care advice (when explicitly requested)
- **Action Groups**: None (pure RAG)
- **Knowledge Bases**: 
  - KB #1: Product catalog (S3 PDFs → Bedrock KB)
  - KB #2: Pet care knowledge (Wikipedia URLs → Bedrock KB)

**Specialist Agent #2: Business Logic Agent** (Lambda-focused):
- **Model**: Fast model (Claude Haiku) - deterministic API calls
- **Responsibilities**:
  - Inventory checking (stock levels, availability)
  - User profile lookup (subscription status, transaction history)
  - Pricing calculations (bundle discounts, shipping, subscriber discounts)
- **Action Groups**:
  - AG #1: Inventory operations (calls team-PetStoreInventoryManagementFunction)
  - AG #2: User operations (calls team-PetStoreUserManagementFunction)
  - AG #3: Pricing calculator (new Lambda function)
- **Knowledge Base**: None

**Specialist Agent #3: Guardrail Agent** (Security-focused):
- **Model**: Fast model (Claude Haiku) - pattern matching
- **Responsibilities**:
  - Prompt injection detection
  - Out-of-scope query detection (non-cat/dog products)
  - Input validation
- **Action Groups**: None (LLM-based classification)
- **Knowledge Base**: Product scope definition (cats/dogs only)

### Communication Flow

```
User Query → Orchestrator Agent
              ↓
         [Intent Classification]
              ↓
    ┌─────────┴─────────┐
    ↓                   ↓
Guardrail Agent    Knowledge Agent
    ↓                   ↓
[Pass/Reject]      [Product Info]
    ↓                   ↓
    └─────→ Business Logic Agent
                ↓
          [Inventory + User + Pricing]
                ↓
         Orchestrator Agent
                ↓
          [Aggregate + Format JSON]
                ↓
         Structured Response
```

### Data Flow Architecture

**Phase 1: Knowledge Base Setup**
1. Create Bedrock KB #1: Ingest S3 PDFs (product catalog, content)
2. Create Bedrock KB #2: Crawl Wikipedia URLs (cat/dog care)

**Phase 2: Lambda Functions**
1. Existing: `team-PetStoreInventoryManagementFunction` (getInventory)
2. Existing: `team-PetStoreUserManagementFunction` (getUserById, getUserByEmail)
3. New: `PricingCalculatorFunction` (calculateOrder) - business rules engine

**Phase 3: Agent Creation**
1. Create 3 specialist agents (Knowledge, Business Logic, Guardrail)
2. Create orchestrator agent with supervisor mode
3. Associate agents: Orchestrator → 3 specialists

### Pricing Business Logic (New Lambda)

**Function**: `PricingCalculatorFunction`
**Input**:
```json
{
  "function": "calculateOrder",
  "parameters": {
    "product_id": "DD006",
    "price": 54.99,
    "quantity": 1,
    "customer_type": "Guest",
    "inventory_status": "in_stock",
    "reorder_level": 50,
    "current_stock": 150
  }
}
```

**Output**:
```json
{
  "bundleDiscount": 0,
  "subtotal": 54.99,
  "shippingCost": 14.95,
  "additionalDiscount": 0,
  "total": 69.94,
  "replenishInventory": false
}
```

**Business Rules** (encoded in Lambda):
- Bundle discount: 0.10 if quantity > 1
- Additional discount: 0.15 if customer_type = "Subscribed" AND subtotal > 200
- Free shipping: shippingCost = 0 if subtotal > 300, else 14.95
- Replenish inventory: true if (current_stock - quantity) < reorder_level

### Performance Strategy

**Model Selection**: Claude Haiku for ALL agents
- **Reasoning**: 
  - Most tasks are simple (lookup, API calls, pattern matching)
  - Latency-sensitive customer service application
  - Cost optimization for high-volume queries
  - No complex reasoning required (business logic in Lambda)

**Routing Mode**: Supervisor with Routing
- **Simple queries** (80% of traffic): Direct routing to single agent (low latency)
- **Complex queries** (20%): Full orchestration with multiple agents

**Parallel Invocation**:
- Orchestrator calls Knowledge Agent + Guardrail Agent in parallel
- If both pass, call Business Logic Agent
- Reduces total latency by ~40%

## Technical Decisions (FINAL)

### Platform & Deployment
- **Framework**: Strands Agents SDK (Jupyter notebooks)
- **Runtime**: Bedrock AgentCore (managed, auto-scaling)
- **Knowledge Bases**: Created via CloudFormation template
- **Guardrails**: Bedrock Guardrails service (prompt injection, PII, denied topics)
- **Error Handling**: Production-grade (retries, backoff, circuit breakers)
- **Pricing Logic**: Extensible architecture (plugin pattern for future rules)

### Agent Architecture (Strands-Based)

**Orchestrator Agent** (Main reasoning agent):
- **Responsibilities**: Intent classification, task delegation, response aggregation
- **Tools**: 
  - Knowledge retrieval (KB query tool)
  - User lookup (Lambda tool: getUserById, getUserByEmail)
  - Inventory check (Lambda tool: getInventory)
  - Pricing calculation (Lambda tool: calculateOrder)
- **Model**: Claude Haiku (latency optimization)
- **Guardrails**: Bedrock Guardrails (input validation, prompt injection detection)

**No Specialist Agents**: Strands pattern uses single orchestrator with multiple tools (different from Native Bedrock Multi-Agent)

### Tool Functions (Custom Strands Tools)

**1. Knowledge Base Retrieval Tool**:
```python
def query_knowledge_base(query: str, kb_id: str) -> dict:
    """Query product catalog or pet care KB"""
    # Returns: product info, pricing, descriptions, ingredients, pet advice
```

**2. User Management Tool**:
```python
def get_user_info(identifier: str, lookup_type: str) -> dict:
    """Calls team-PetStoreUserManagementFunction"""
    # lookup_type: 'user_id' or 'email'
    # Returns: name, subscription_status, subscription_end_date, transactions
```

**3. Inventory Management Tool**:
```python
def get_inventory(product_code: str) -> dict:
    """Calls team-PetStoreInventoryManagementFunction"""
    # Returns: quantity, status, reorder_level, last_updated
```

**4. Pricing Calculator Tool** (NEW Lambda):
```python
def calculate_order(items: list, customer_type: str, inventory_data: dict) -> dict:
    """Business rules engine for pricing"""
    # Implements:
    # - Bundle discount (10% if qty > 1)
    # - Free shipping (subtotal > $300)
    # - Subscriber discount (tiered based on subtotal)
    # - Inventory replenishment flag
    # - Complex discount stacking (Prompt K)
    # Returns: subtotal, discounts, shipping, total, replenish_inventory
```

### Knowledge Bases (CloudFormation)

**KB #1: Product Catalog**
- **Data Source**: S3 bucket (team-databucketforknowledge-ixntv3yqclsm/pet-store-products/)
- **Files**: Pet Store Product Catalog.pdf, Pet Store Product Content.pdf
- **Embeddings**: Amazon Titan Embeddings
- **Chunking**: 300 tokens, 20% overlap

**KB #2: Pet Care Advice**
- **Data Source**: Web crawler
- **URLs**: 
  - https://en.wikipedia.org/wiki/Cat_food
  - https://en.wikipedia.org/wiki/Cat_play_and_toys
  - https://en.wikipedia.org/wiki/Dog_food
  - https://en.wikipedia.org/wiki/Dog_grooming
- **Embeddings**: Amazon Titan Embeddings
- **Chunking**: 300 tokens, 20% overlap

### Guardrails Configuration (Bedrock)

**Content Filters**:
- Prompt injection patterns: BLOCK (high confidence)
- Jailbreak attempts: BLOCK
- Denied topics: birds, reptiles, exotic pets → BLOCK
- PII detection: MASK (email, phone in logs)

**Contextual Grounding**:
- Enable hallucination detection
- Require KB citations for product facts

**Word Filters**:
- Block profanity in customer messages
- Block system keywords ("product_code", "reorder_level", "inventory_status")

### Clearance Check (FINAL)

✅ Core objective clearly defined? **YES** - Graded assessment (900 points, 11 prompts)  
✅ Scope boundaries established (IN/OUT)? **YES** - Evaluation criteria documented  
✅ No critical ambiguities remaining? **YES** - All requirements from eval spec  
✅ Technical approach decided? **YES** - Strands + AgentCore + CloudFormation  
✅ Test strategy confirmed? **YES** - 11 evaluation prompts with point scores  
✅ No blocking questions outstanding? **YES** - All decisions finalized  

**STATUS**: READY FOR PLAN GENERATION

## Scope Boundaries

### INCLUDE (Requirements from Sample Messages)

**Core Intents** (6 scenarios analyzed):

1. **Product Price Inquiry** (Sample 1)
   - Guest user, single product, base pricing + shipping
   - No pet advice for simple price queries

2. **Product Purchase with User Context** (Sample 2)
   - Subscribed user (lookup by user_id), multi-quantity
   - Bundle discount (10% for qty>1), subscriber benefits
   - Pet advice when user asks specific questions (suitability, care tips)

3. **Prompt Injection Detection** (Sample 3)
   - Reject malicious inputs (jailbreak attempts, out-of-scope requests)
   - Status: "Reject" with generic safe message

4. **Bulk Order with Complex Pricing** (Sample 4)
   - Guest user, high quantity (12 units)
   - Multi-unit discount, free shipping threshold
   - Inventory replenishment flag (replenishInventory: true)
   - Additional discount for bulk (15%)

5. **Out-of-Scope Product** (Sample 5)
   - Reject queries about non-pet products (reptiles, parrots)
   - Polite rejection: "We can't accept your request"

6. **Product Unavailability** (Sample 6)
   - Multi-turn conversation context (chat history)
   - Reject when product doesn't exist (soft kibble for seniors)
   - Specific explanation: "We don't currently offer..."

**Business Rules** (Inferred):
- Bundle discount: 10% when quantity > 1
- Subscriber discount: Applied as additionalDiscount (varies)
- Free shipping: When subtotal > threshold (appears to be $300+)
- Inventory replenishment: Flag when quantity triggers reorder_level
- Customer type detection: "Guest" (no user_id) vs "Subscribed" (user lookup)
- Pet advice: Only when user explicitly asks pet care questions

**Guardrails**:
- Reject prompt injections ("ignore previous instructions...")
- Reject out-of-scope products (reptiles, birds - only cats/dogs)
- Reject unavailable products with specific explanation
- Message length: ≤250 chars
- Pet advice length: ≤500 chars

### EXCLUDE (Explicit Boundaries)

- Order creation/submission (read-only, quote generation only)
- Email drafting/sending
- Payment processing
- Returns/refunds
- User account management (just lookup)
- Non-cat/dog products
- Medical advice (stick to general pet care from Wikipedia sources)
