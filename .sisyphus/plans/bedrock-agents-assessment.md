# AWS Bedrock Multi-Agent Customer Service Assessment

## TL;DR

> **Quick Summary**: Build a graded AI customer service system using Strands Agents SDK on AWS Bedrock AgentCore. The system must pass 11 evaluation prompts (900 points total) covering product inquiries, pricing, security, error handling, and ethical guardrails.
> 
> **Deliverables**:
> - 2 Bedrock Knowledge Bases (CloudFormation): Product catalog + Pet care advice
> - 1 Lambda function: Pricing calculator with extensible business rules
> - 1 Strands orchestrator agent: Intent classification, tool orchestration, response formatting
> - 4 custom tool functions: KB retrieval, user lookup, inventory check, pricing calc
> - Bedrock Guardrails: Prompt injection, PII masking, scope enforcement
> - 11 automated test cases matching evaluation prompts (Jupyter notebook)
> - Deployment notebook for AgentCore runtime
> 
> **Estimated Effort**: Large (40-60 hours)  
> **Parallel Execution**: YES - 4 waves  
> **Critical Path**: KB setup → Lambda pricing → Tool functions → Agent notebook → Testing

---

## Context

### Original Request
User needs to build a PoC multi-agent system for AWS Bedrock to handle customer service inquiries for a virtual pet store. Initial example: "A new user is asking about the price of Doggy Delights?" → structured JSON response with pricing, inventory, and business logic.

### Interview Summary
**Key Discussions**:
- User revealed this is actually a **graded assessment system** with 11 evaluation prompts worth 900 points
- Evaluation criteria include: accuracy, security (prompt injection detection), customer service quality, scope enforcement (cats/dogs only), ethical guardrails
- Existing infrastructure: 2 Lambda functions (inventory, user management), S3 bucket with product PDFs
- Architecture evolution: Initially considered Native Bedrock Multi-Agent → User specified Strands Agents SDK deployment
- Deployment decisions: AgentCore runtime, CloudFormation for KBs, Bedrock Guardrails service
- Error handling: Production-grade (retries, backoff, circuit breakers)
- Pricing logic: Extensible plugin architecture for future business rules

**Research Findings**:
- AWS Bedrock supports Supervisor + up to 10 specialist agents (Native) OR single orchestrator with tools (Strands)
- Strands pattern uses Jupyter notebooks for agent development, custom tool functions, deploy to AgentCore or Lambda
- 15 products in catalog: DD006 (Doggy Delights - $54.99), CM001 (Meow Munchies), etc.
- Sample messages show complex requirements: multi-item orders, conditional logic, subscription status checks, graceful error handling

### Metis Review
**Identified Gaps** (addressed):
- Infrastructure ambiguity → Resolved: Strands on AgentCore with CloudFormation KBs
- Scope creep risks → Locked: 11 evaluation prompts define exact scope, no feature additions
- Business logic extensibility → Resolved: Plugin architecture for pricing rules, but implement only required rules for assessment
- Edge case handling → Covered: Missing inventory data (Prompt Y), expired subscriptions (Prompt E), out-of-scope products (Prompts F, N, U)
- Security requirements → Explicit: Bedrock Guardrails for Prompts C and U
- Testing strategy → Defined: 11 automated tests in Jupyter notebook matching evaluation prompts

---

## Work Objectives

### Core Objective
Build a Strands-based AWS Bedrock agent system that achieves a passing score (target: 800+/900 points) on the Virtual Pet Store customer service assessment by correctly handling product inquiries, pricing calculations, user management, security threats, and ethical boundaries.

### Concrete Deliverables
- `cloudformation/knowledge-bases.yaml`: CFN template creating 2 Bedrock KBs (products, pet care)
- `lambda/pricing-calculator/`: Python Lambda function with extensible pricing rules engine
- `notebooks/agent-development.ipynb`: Strands agent with 4 custom tool functions
- `notebooks/deployment.ipynb`: AgentCore deployment configuration
- `notebooks/evaluation-tests.ipynb`: 11 automated test cases with scoring
- `guardrails/policies.json`: Bedrock Guardrails configuration (prompt injection, PII, denied topics)

### Definition of Done
- [ ] All 2 Knowledge Bases created and synced: `aws bedrock-agent list-knowledge-bases` shows both with ACTIVE status
- [ ] Pricing Lambda deployed and tested: `aws lambda invoke --function-name PricingCalculator` returns valid calculation
- [ ] Agent deployed to AgentCore: Invoke returns structured JSON responses
- [ ] Guardrails integrated: Malicious prompts blocked (Prompt C test passes)
- [ ] All 11 evaluation tests pass with score ≥ 800/900: `jupyter nbconvert --execute evaluation-tests.ipynb` shows passing verdicts

### Must Have
- **Accurate product information**: KB retrieval returns correct prices, descriptions, ingredients (Prompts A, B, T, K, P)
- **Correct pricing calculations**: Bundle discounts (10% qty>1), free shipping ($300+ subtotal), subscriber discounts, inventory replenishment flags (Prompts T, K)
- **User recognition**: Lookup by user_id or email, identify customer by name in response (Prompts B, E, P)
- **Security guardrails**: Block prompt injections (Prompt C), reject unethical requests (Prompt U)
- **Scope enforcement**: Cats/dogs only, reject birds/reptiles/exotics (Prompts F, N)
- **Graceful error handling**: Missing inventory data, expired subscriptions, unavailable products (Prompts Y, E, P)
- **Zero internal exposure**: Never show product codes, inventory numbers, system errors in customer-facing messages

### Must NOT Have (Guardrails)
- **No shopping cart persistence**: Each query independent, no session state
- **No payment processing**: Quote generation only, no transactions
- **No email/SMS sending**: Response JSON only, no notifications
- **No admin UI**: Agent interface only, no management console
- **No feature additions beyond evaluation**: Stick to 11 prompts, no promo codes/loyalty/referrals unless evaluation requires
- **No over-engineering**: Extensible architecture but only implement rules needed for assessment
- **No manual test dependencies**: All 11 tests automated in notebook, zero human intervention

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed via Jupyter notebooks.

### Test Decision
- **Infrastructure exists**: NO automated testing framework exists
- **Automated tests**: Tests-after (implement then validate)
- **Framework**: Jupyter notebooks with pytest assertions + boto3 SDK
- **Test strategy**: Each evaluation prompt = 1 automated test function with expected JSON structure assertions

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **AWS Resources**: Use `aws` CLI commands — Verify CF stacks, Lambda functions, KB status
- **Lambda Functions**: Use `aws lambda invoke` — Call with test payloads, assert response structure
- **Agent Responses**: Use boto3 `bedrock-agent-runtime.invoke_agent()` — Send prompt, parse response, assert JSON schema
- **Notebooks**: Use `jupyter nbconvert --execute` — Run cells, capture outputs, assert no exceptions

**All QA scenarios executed programmatically. No "manually verify" or "visually confirm" acceptance criteria.**

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput. Each wave completes before next begins.
> Target: 5-8 tasks per wave.

```
Wave 1 (Infrastructure Foundation — can start immediately):
├── Task 1: Project scaffolding + directory structure [quick]
├── Task 2: CloudFormation template for 2 Knowledge Bases [quick]
├── Task 3: Deploy CF stack + verify KB creation [quick]
├── Task 4: S3 product PDFs verification [quick]
├── Task 5: Pricing Lambda function scaffold [quick]
└── Task 6: Bedrock Guardrails policy definition [quick]

Wave 2 (Business Logic + Tool Functions — after Wave 1):
├── Task 7: Pricing calculator business rules implementation [deep]
├── Task 8: Deploy pricing Lambda + IAM role [quick]
├── Task 9: Tool function: KB retrieval wrapper [quick]
├── Task 10: Tool function: User management wrapper [quick]
├── Task 11: Tool function: Inventory management wrapper [quick]
└── Task 12: Tool function: Pricing calculator wrapper [quick]

Wave 3 (Agent Development — after Wave 2):
├── Task 13: Strands agent notebook: orchestrator logic [deep]
├── Task 14: Agent instructions: intent classification prompts [unspecified-high]
├── Task 15: Agent instructions: tool selection logic [deep]
├── Task 16: Agent instructions: response formatting rules [unspecified-high]
├── Task 17: Integrate 4 tool functions into agent [quick]
├── Task 18: Integrate Bedrock Guardrails [quick]
└── Task 19: Deploy agent to AgentCore runtime [quick]

Wave 4 (Testing + Validation — after Wave 3):
├── Task 20: Evaluation test notebook scaffold [quick]
├── Task 21: Tests for Prompts A, B, C (security + basic) [unspecified-high]
├── Task 22: Tests for Prompts T, K (complex pricing) [deep]
├── Task 23: Tests for Prompts N, F, U (scope + ethics) [unspecified-high]
├── Task 24: Tests for Prompts E, Y, P (errors + edge cases) [deep]
└── Task 25: Aggregate test results + scoring report [quick]

Wave FINAL (Compliance Audit — after all tasks):
├── Task F1: Evaluation score verification (≥800/900) [deep]
├── Task F2: Security audit (Prompts C, U validation) [unspecified-high]
├── Task F3: Scope fidelity check (no feature creep) [deep]
└── Task F4: Documentation completeness review [quick]

Critical Path: T1 → T2 → T3 → T7 → T8 → T9-T12 → T13 → T17 → T19 → T20 → T21-T24 → T25 → F1
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 6 (Wave 1)
```

### Dependency Matrix

Wave 1:
- T1: — → T2, T5, T6
- T2: T1 → T3
- T3: T2 → T7, T9
- T4: — → T3 (verification only)
- T5: T1 → T7
- T6: T1 → T18

Wave 2:
- T7: T3, T5 → T8, T12
- T8: T7 → T12, T13
- T9: T3 → T17
- T10: — → T17
- T11: — → T17
- T12: T7, T8 → T17

Wave 3:
- T13: T8 → T14, T15, T16, T17
- T14: T13 → T19
- T15: T13 → T19
- T16: T13 → T19
- T17: T9, T10, T11, T12, T13 → T19
- T18: T6, T17 → T19
- T19: T14, T15, T16, T17, T18 → T20, T21, T22, T23, T24

Wave 4:
- T20: T19 → T21, T22, T23, T24
- T21: T20 → T25
- T22: T20 → T25
- T23: T20 → T25
- T24: T20 → T25
- T25: T21, T22, T23, T24 → F1, F2, F3, F4

Wave FINAL:
- F1: T25 → user okay
- F2: T25 → user okay
- F3: T25 → user okay
- F4: T25 → user okay

### Agent Dispatch Summary

- **Wave 1**: 6 tasks → 5× `quick`, 1× `unspecified-high`
- **Wave 2**: 6 tasks → 1× `deep`, 5× `quick`
- **Wave 3**: 7 tasks → 2× `deep`, 2× `unspecified-high`, 3× `quick`
- **Wave 4**: 6 tasks → 2× `deep`, 2× `unspecified-high`, 2× `quick`
- **Wave FINAL**: 4 tasks → 2× `deep`, 1× `unspecified-high`, 1× `quick`

**Total**: 29 tasks (25 implementation + 4 final audit)

---

## TODOs

- [ ] 1. Project scaffolding + directory structure

  **What to do**:
  - Create directory structure: `cloudformation/`, `lambda/pricing-calculator/`, `notebooks/`, `guardrails/`, `.sisyphus/evidence/`
  - Initialize Python requirements.txt with: boto3, aws-cdk-lib, strands-agents-sdk, pytest, jupyter
  - Create .gitignore for Python, Jupyter, AWS credentials
  - Create README.md scaffold with sections: Overview, Prerequisites, Setup, Deployment, Testing

  **Must NOT do**:
  - Don't add unneeded directories (no `docs/`, no `frontend/`, no `tests/` separate from notebooks)
  - Don't initialize npm/package.json (Python project only)
  - Don't add CI/CD configs yet (focus on local development first)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple file/directory creation, no complex logic
  - **Skills**: []
    - No specialized skills needed for scaffolding

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 4, 5, 6)
  - **Blocks**: Tasks 2, 5, 6 (need directory structure)
  - **Blocked By**: None (can start immediately)

  **References**:
  - Project conventions: Standard Python project layout (no specific reference needed)
  - AWS CDK patterns: https://docs.aws.amazon.com/cdk/v2/guide/best-practices.html (directory structure)

  **Acceptance Criteria**:
  - [ ] Directory structure exists: `ls -la` shows cloudformation/, lambda/, notebooks/, guardrails/, .sisyphus/evidence/
  - [ ] requirements.txt created: `cat requirements.txt` shows boto3, aws-cdk-lib, strands-agents-sdk, pytest, jupyter
  - [ ] .gitignore created: `cat .gitignore` includes *.pyc, __pycache__/, .env, .aws/
  - [ ] README.md created: `cat README.md` shows Overview, Prerequisites, Setup, Deployment, Testing sections

  **QA Scenarios**:
  ```
  Scenario: Verify directory structure created
    Tool: Bash
    Preconditions: Clean workspace
    Steps:
      1. ls -la | grep cloudformation && echo "PASS" || echo "FAIL"
      2. ls -la | grep lambda && echo "PASS" || echo "FAIL"
      3. ls -la | grep notebooks && echo "PASS" || echo "FAIL"
      4. ls -la | grep guardrails && echo "PASS" || echo "FAIL"
      5. ls -la .sisyphus/ | grep evidence && echo "PASS" || echo "FAIL"
    Expected Result: All 5 directories present, each command outputs "PASS"
    Failure Indicators: Any "FAIL" output, "No such file or directory" errors
    Evidence: .sisyphus/evidence/task-1-directory-structure.txt

  Scenario: Verify requirements.txt has all dependencies
    Tool: Bash
    Preconditions: requirements.txt created
    Steps:
      1. cat requirements.txt | grep boto3 && echo "PASS" || echo "FAIL"
      2. cat requirements.txt | grep aws-cdk-lib && echo "PASS" || echo "FAIL"
      3. cat requirements.txt | grep strands-agents-sdk && echo "PASS" || echo "FAIL"
      4. cat requirements.txt | grep pytest && echo "PASS" || echo "FAIL"
      5. cat requirements.txt | grep jupyter && echo "PASS" || echo "FAIL"
    Expected Result: All 5 dependencies listed, each grep outputs "PASS"
    Failure Indicators: Missing dependencies, "FAIL" outputs
    Evidence: .sisyphus/evidence/task-1-requirements.txt
  ```

  **Evidence to Capture**:
  - [ ] task-1-directory-structure.txt: Output of `ls -laR` showing all created directories
  - [ ] task-1-requirements.txt: Contents of requirements.txt file

  **Commit**: YES
  - Message: `chore(infra): scaffolding + CloudFormation template for Knowledge Bases`
  - Files: `cloudformation/`, `lambda/`, `notebooks/`, `guardrails/`, `requirements.txt`, `.gitignore`, `README.md`
  - Pre-commit: N/A (no tests yet)

---

- [ ] 2. CloudFormation template for 2 Knowledge Bases

  **What to do**:
  - Create `cloudformation/knowledge-bases.yaml` with 2 AWS::Bedrock::KnowledgeBase resources
  - KB #1: "ProductCatalog" with S3 data source (team-databucketforknowledge-ixntv3yqclsm/pet-store-products/)
  - KB #2: "PetCareAdvice" with web crawler data source (4 Wikipedia URLs from requirements)
  - Both use Amazon Titan Embeddings, chunking strategy: 300 tokens with 20% overlap
  - Include IAM role for Bedrock to access S3 and invoke embeddings
  - Output: KB IDs for use in agent configuration

  **Must NOT do**:
  - Don't create additional KBs beyond these 2 (no FAQ KB, no troubleshooting KB)
  - Don't use custom embedding models (stick to Titan)
  - Don't add S3 buckets in this template (use existing bucket)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Declarative CloudFormation, well-documented Bedrock KB resources
  - **Skills**: []
    - AWS CDK/CloudFormation knowledge (general)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 4, 5, 6)
  - **Blocks**: Task 3 (deployment depends on template)
  - **Blocked By**: Task 1 (needs cloudformation/ directory)

  **References**:
  - AWS Bedrock KB CloudFormation: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-bedrock-knowledgebase.html
  - S3 data source config: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ds.html
  - Web crawler data source: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ds-web.html
  - Wikipedia URLs from requirements:
    - https://en.wikipedia.org/wiki/Cat_food
    - https://en.wikipedia.org/wiki/Cat_play_and_toys
    - https://en.wikipedia.org/wiki/Dog_food
    - https://en.wikipedia.org/wiki/Dog_grooming

  **Acceptance Criteria**:
  - [ ] CloudFormation template exists: `cat cloudformation/knowledge-bases.yaml` shows valid YAML
  - [ ] Template defines 2 KB resources: `grep 'AWS::Bedrock::KnowledgeBase' cloudformation/knowledge-bases.yaml | wc -l` outputs 2
  - [ ] S3 data source configured: `grep 's3://team-databucketforknowledge' cloudformation/knowledge-bases.yaml` shows bucket URI
  - [ ] Web crawler configured: `grep 'wikipedia.org' cloudformation/knowledge-bases.yaml | wc -l` outputs 4
  - [ ] IAM role defined: `grep 'AWS::IAM::Role' cloudformation/knowledge-bases.yaml` shows role for Bedrock
  - [ ] Template validates: `aws cloudformation validate-template --template-body file://cloudformation/knowledge-bases.yaml` returns success

  **QA Scenarios**:
  ```
  Scenario: Validate CloudFormation template syntax
    Tool: Bash
    Preconditions: cloudformation/knowledge-bases.yaml created
    Steps:
      1. aws cloudformation validate-template --template-body file://cloudformation/knowledge-bases.yaml --query 'Description' 2>&1
    Expected Result: Command succeeds, returns template description, no syntax errors
    Failure Indicators: "Template format error", "Invalid template", "ValidationError"
    Evidence: .sisyphus/evidence/task-2-cfn-validate.txt

  Scenario: Verify 2 Knowledge Base resources defined
    Tool: Bash
    Preconditions: Template created
    Steps:
      1. grep -c 'Type: AWS::Bedrock::KnowledgeBase' cloudformation/knowledge-bases.yaml
    Expected Result: Output is "2" (exactly 2 KB resources)
    Failure Indicators: Output is "0", "1", or ">2"
    Evidence: .sisyphus/evidence/task-2-kb-count.txt
  ```

  **Evidence to Capture**:
  - [ ] task-2-cfn-validate.txt: CloudFormation validation output
  - [ ] task-2-kb-count.txt: Grep count showing 2 KBs defined

  **Commit**: Groups with Task 1
  - Message: `chore(infra): scaffolding + CloudFormation template for Knowledge Bases`

---

- [ ] 3. Deploy CF stack + verify KB creation

  **What to do**:
  - Deploy CloudFormation stack: `aws cloudformation create-stack --stack-name bedrock-knowledge-bases --template-body file://cloudformation/knowledge-bases.yaml`
  - Wait for CREATE_COMPLETE: `aws cloudformation wait stack-create-complete --stack-name bedrock-knowledge-bases`
  - Extract KB IDs from stack outputs: `aws cloudformation describe-stacks --stack-name bedrock-knowledge-bases --query 'Stacks[0].Outputs'`
  - Verify both KBs are ACTIVE: `aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[?status==\`ACTIVE\`].name'`
  - Trigger initial sync for both KBs: `aws bedrock-agent start-ingestion-job --knowledge-base-id <ID> --data-source-id <ID>`
  - Save KB IDs to `notebooks/config.py` for agent configuration

  **Must NOT do**:
  - Don't manually create KBs via console (use CloudFormation only)
  - Don't proceed to Wave 2 until both KBs show ACTIVE status
  - Don't modify KB chunking strategy after deployment (define correctly in template)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: AWS CLI commands, wait for stack completion
  - **Skills**: []
    - Standard AWS deployment

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Task 2)
  - **Parallel Group**: Sequential
  - **Blocks**: Tasks 7, 9 (pricing and tool functions need KB IDs)
  - **Blocked By**: Task 2 (needs CloudFormation template)

  **References**:
  - CloudFormation CLI: https://docs.aws.amazon.com/cli/latest/reference/cloudformation/create-stack.html
  - Bedrock KB status check: https://docs.aws.amazon.com/cli/latest/reference/bedrock-agent/list-knowledge-bases.html
  - Ingestion job: https://docs.aws.amazon.com/cli/latest/reference/bedrock-agent/start-ingestion-job.html

  **Acceptance Criteria**:
  - [ ] CloudFormation stack deployed: `aws cloudformation describe-stacks --stack-name bedrock-knowledge-bases --query 'Stacks[0].StackStatus'` returns CREATE_COMPLETE
  - [ ] 2 Knowledge Bases active: `aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[?status==\`ACTIVE\`].name' | jq length` returns 2
  - [ ] KB IDs saved: `cat notebooks/config.py` shows PRODUCT_KB_ID and PETCARE_KB_ID variables
  - [ ] Ingestion jobs started: `aws bedrock-agent list-ingestion-jobs --knowledge-base-id <PRODUCT_KB_ID> --max-results 1 --query 'ingestionJobSummaries[0].status'` returns IN_PROGRESS or COMPLETE

  **QA Scenarios**:
  ```
  Scenario: Verify CloudFormation stack deployment success
    Tool: Bash
    Preconditions: CloudFormation stack created
    Steps:
      1. aws cloudformation describe-stacks --stack-name bedrock-knowledge-bases --query 'Stacks[0].StackStatus' --output text
    Expected Result: Output is "CREATE_COMPLETE"
    Failure Indicators: "CREATE_FAILED", "ROLLBACK_COMPLETE", stack not found
    Evidence: .sisyphus/evidence/task-3-stack-status.txt

  Scenario: Verify both Knowledge Bases are active
    Tool: Bash
    Preconditions: Stack deployed
    Steps:
      1. aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[?status==`ACTIVE`].name' --output json
      2. echo $? # Exit code should be 0
    Expected Result: JSON array with 2 KB names (ProductCatalog, PetCareAdvice), exit code 0
    Failure Indicators: Empty array, only 1 KB, "CREATING" status, non-zero exit code
    Evidence: .sisyphus/evidence/task-3-kb-active.json
  ```

  **Evidence to Capture**:
  - [ ] task-3-stack-status.txt: CloudFormation stack status output
  - [ ] task-3-kb-active.json: List of active Knowledge Bases

  **Commit**: YES
  - Message: `feat(kb): deploy and verify Product + Pet Care Knowledge Bases`
  - Files: `cloudformation/knowledge-bases.yaml`, `notebooks/config.py`
  - Pre-commit: `aws cloudformation validate-template --template-body file://cloudformation/knowledge-bases.yaml`

---

> 4 review agents run in PARALLEL after ALL implementation tasks.
> ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Evaluation Score Verification** — `deep`

  Run all 11 evaluation tests via `jupyter nbconvert --execute evaluation-tests.ipynb`. Parse output JSON for each prompt: extract score, status (PASS/FAIL), actual vs expected response. Aggregate total score. VERDICT: PASS if ≥800/900 points AND zero critical failures (Prompts C, U must pass). If <800, identify lowest-scoring prompts and recommend fixes.
  
  Output: `Score: X/900 | Critical (C,U): PASS/FAIL | Recommend: [specific fixes] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Security Audit** — `unspecified-high`

  Manually craft 5 adversarial prompts beyond Prompt C: jailbreak attempts, system prompt extraction, PII injection, cross-site scripting patterns, SQL injection in product names. Send via `bedrock-agent-runtime.invoke_agent()`. Verify ALL are blocked or return safe rejections. Check CloudWatch logs for guardrail triggers. Confirm no internal data leaked (product codes, inventory numbers, Lambda ARNs).
  
  Output: `Adversarial Prompts: 5/5 blocked | Guardrail Triggers: X events | PII Exposure: NONE | VERDICT: APPROVE/REJECT`

- [ ] F3. **Scope Fidelity Check** — `deep`

  Review all implemented code (pricing Lambda, tool functions, agent instructions, test notebooks). Verify ZERO features beyond evaluation requirements: no promo codes, no loyalty points, no email sending, no admin UI, no shopping cart. Check tool function signatures match ONLY what's needed for 11 prompts. Confirm no TODO comments suggesting future features were started.
  
  Output: `Code Review: X files | Out-of-Scope Features: NONE/[list] | TODO Comments: [count] | VERDICT: APPROVE/REJECT`

- [ ] F4. **Documentation Completeness Review** — `quick`

  Verify all deliverables present: CloudFormation template, Lambda code, Jupyter notebooks (agent dev, deployment, testing), guardrails policy JSON, README with setup instructions. Check each file has header comments explaining purpose. Confirm evaluation test notebook includes scoring rubric and output examples. Test README instructions on clean AWS account (if possible) or document assumptions.
  
  Output: `Deliverables: X/6 present | Documentation: COMPLETE/INCOMPLETE | README Validated: YES/NO | VERDICT: APPROVE/REJECT`

---

## Commit Strategy

- **Commit 1**: `chore(infra): scaffolding + CloudFormation template for Knowledge Bases` — Task 1, 2
- **Commit 2**: `feat(kb): deploy and verify Product + Pet Care Knowledge Bases` — Task 3, 4
- **Commit 3**: `feat(lambda): pricing calculator with extensible business rules` — Task 5, 7, 8
- **Commit 4**: `feat(tools): implement 4 custom Strands tool functions` — Task 9, 10, 11, 12
- **Commit 5**: `feat(guardrails): Bedrock Guardrails policy for security` — Task 6, 18
- **Commit 6**: `feat(agent): Strands orchestrator notebook with tool integration` — Task 13, 14, 15, 16, 17
- **Commit 7**: `feat(deploy): AgentCore deployment configuration` — Task 19
- **Commit 8**: `test(eval): 11 automated evaluation tests with scoring` — Task 20, 21, 22, 23, 24, 25
- **Commit 9**: `docs(final): audit results + deployment README` — Task F1, F2, F3, F4

---

## Success Criteria

### Verification Commands
```bash
# Knowledge Bases active
aws bedrock-agent list-knowledge-bases --query 'knowledgeBaseSummaries[?status==`ACTIVE`].name' | grep -c 'Product\|Pet Care'  # Expected: 2

# Lambda function deployed
aws lambda get-function --function-name PricingCalculator --query 'Configuration.State'  # Expected: "Active"

# Agent deployed to AgentCore
aws bedrock-agent-runtime invoke-agent --agent-id <AGENT_ID> --agent-alias-id <ALIAS> --session-id test --input-text "Test" --query 'completion' # Expected: JSON response

# Evaluation tests pass
jupyter nbconvert --execute notebooks/evaluation-tests.ipynb && grep 'Total Score:' evaluation-tests.json | awk '{print $3}'  # Expected: ≥800

# Guardrails active
aws bedrock list-guardrails --query 'guardrails[?status==`READY`].name' | grep 'PetStore'  # Expected: 1 result
```

### Final Checklist
- [ ] CloudFormation stack deployed: `aws cloudformation describe-stacks --stack-name bedrock-knowledge-bases` shows CREATE_COMPLETE
- [ ] Both KBs synced: Product catalog KB + Pet care KB show ACTIVE status with >0 documents
- [ ] Pricing Lambda responds: Test invocation returns valid JSON with subtotal, discounts, total
- [ ] Agent responds to test query: "What's the price of Doggy Delights?" returns DD006 product info with $54.99 price
- [ ] Security tests pass: Prompt C (injection) and Prompt U (unethical) both return rejection status
- [ ] All 11 evaluation prompts pass: Score ≥ 800/900 with no critical failures
- [ ] No internal data exposed: Sample responses contain zero product codes, inventory levels, or system errors
- [ ] Guardrails integrated: CloudWatch shows guardrail evaluation logs for malicious prompts
- [ ] Documentation complete: README, code comments, notebook markdown cells all present
