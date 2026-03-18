# Pet Store Agent - Environment Configuration

## Quick Start

### 1. Copy the environment template
```bash
cd pet_store_agent
cp .env.example .env
```

### 2. Fill in your values
Edit `.env` and replace placeholders with your AWS resource IDs:

```bash
# Required: Get these from your CloudFormation stack outputs
KNOWLEDGE_BASE_1_ID=YOUR_PRODUCT_KB_ID_HERE
KNOWLEDGE_BASE_2_ID=YOUR_PET_CARE_KB_ID_HERE

# Required: Get these from your Lambda function names
SYSTEM_FUNCTION_1_NAME=YOUR_INVENTORY_LAMBDA_NAME
SYSTEM_FUNCTION_2_NAME=YOUR_USER_MANAGEMENT_LAMBDA_NAME
```

### 3. Optional: Override defaults
Customize agent behavior by uncommenting and modifying optional settings:

```bash
# Change the model
BEDROCK_MODEL_ID=us.anthropic.claude-3-haiku-20240307-v1:0

# Adjust retrieval quality/quantity
RETRIEVAL_DEFAULT_MIN_SCORE=0.35
RETRIEVAL_DEFAULT_RESULTS=5
```

## Configuration Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `KNOWLEDGE_BASE_1_ID` | Product catalog knowledge base ID | `JZIDPRZPJJ` |
| `KNOWLEDGE_BASE_2_ID` | Pet care advice knowledge base ID | `LN1MKECSKJ` |
| `SYSTEM_FUNCTION_1_NAME` | Inventory management Lambda name/ARN | `team-PetStoreInventory-xyz` |
| `SYSTEM_FUNCTION_2_NAME` | User management Lambda name/ARN | `team-PetStoreUser-abc` |

### Optional Tuning

| Variable | Default | Description |
|----------|---------|-------------|
| `BEDROCK_MODEL_ID` | `us.amazon.nova-pro-v1:0` | Bedrock foundation model to use |
| `BEDROCK_MAX_TOKENS` | `4096` | Maximum tokens per response |
| `BEDROCK_STREAMING` | `false` | Enable/disable streaming responses |
| `RETRIEVAL_DEFAULT_REGION` | `us-west-2` | AWS region for KB retrieval |
| `RETRIEVAL_DEFAULT_RESULTS` | `10` | Max number of retrieval results |
| `RETRIEVAL_DEFAULT_MIN_SCORE` | `0.25` | Minimum relevance score (0.0-1.0) |

### Region Configuration

The agent respects region configuration in this priority order:
1. `AWS_REGION` environment variable
2. `AWS_DEFAULT_REGION` environment variable  
3. Fallback to `us-west-2`

For retrieval tools, you can override with:
```bash
RETRIEVAL_DEFAULT_REGION=us-east-1
```

## Per-User Configuration

Each developer can maintain their own configuration without conflicts:

```bash
# Alice uses development resources
cp .env.example .env.local
# Edit .env.local with dev KB IDs and Lambda names

# Bob uses his own test environment
cp .env.example .env.bob.local
# Edit .env.bob.local with test resources
```

Both `.env.local` and `.env.*.local` are gitignored automatically.

## Deployment

When deploying with `agentcore deploy` or using the deployment scripts, the `.env` values are automatically injected as environment variables into the runtime.

### Via deploy script:
```bash
../deploy_with_env.sh pet_store_agent pet_store_agent/.env
```

### Via notebook:
The deployment notebook reads these values and passes them to the AgentCore runtime.

## Evaluation Script

The evaluation script (`run_evaluation.py`) also respects environment configuration:

```bash
# Override the target agent runtime
export AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/MyRuntime-xyz

# Run evaluation
python run_evaluation.py
```

## Troubleshooting

### Missing required variables
If you see `ValueError: Required environment variables ... must be set`:
- Verify you created `.env` from `.env.example`
- Check all 4 required variables are set (no `<...>` placeholders)

### Invalid model ID
If you see errors about model access:
- Verify model ID exists in your region: `aws bedrock list-foundation-models`
- Request model access in Bedrock console if needed

### Retrieval failures
If KB retrieval fails:
- Verify KB IDs are correct: `aws bedrock-agent list-knowledge-bases`
- Check KB status is ACTIVE and data sources are synced
- Verify region matches where KBs were created

## Git Workflow

✅ **Safe to commit**: `.env.example` (template with placeholders)  
❌ **Never commit**: `.env`, `.env.local`, `.env.*.local` (your actual secrets)

✅ **Safe to ignore**: `.bedrock_agentcore.yaml` (generated after deployment, contains per-account runtime metadata)

The `.gitignore` is configured to protect your local env files automatically.
