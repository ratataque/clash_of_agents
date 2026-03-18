# AWS Clash of Agents - Strands Agent Project

Production-ready AI agent for the AWS Clash of Agents competition, built with [Strands Agents SDK](https://strandsagents.com/) and deployed on AWS infrastructure using CDK.

## 🏗️ Architecture

```
┌─────────────────┐
│  API Gateway    │
└────────┬────────┘
         │
┌────────▼────────┐      ┌──────────────────────┐
│  Lambda Handler │─────▶│  Strands Agent       │
└────────┬────────┘      └────────┬─────────────┘
         │                        │
         │               ┌────────▼────────────────┐
         │               │  Amazon Bedrock         │
         │               │  Claude Sonnet 4.6      │
         │               │  (1M token context)     │
         │               └─────────────────────────┘
         │
    ┌────▼─────┐
    │    S3    │  (State & Logs)
    └──────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- AWS CLI configured with credentials
- Node.js 18+ (for AWS CDK CLI)
- AWS account with Bedrock access

### 1. Install Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install CDK CLI globally
npm install -g aws-cdk
```

### 2. Configure AWS & Bedrock

```bash
# Configure AWS credentials
aws configure

# Request Bedrock model access (first time only)
# Go to: AWS Console → Bedrock → Model access
# Enable: Claude Sonnet 4.6 (us.anthropic.claude-sonnet-4-6)
```

### 3. Test Locally

```bash
# Test the agent locally
python agent/agent.py
```

### 4. Deploy to AWS

```bash
# Bootstrap CDK (first time only)
cdk bootstrap aws://YOUR-ACCOUNT-ID/us-west-2

# Update cdk.json with your account ID
# Edit cdk.json: "account": "YOUR-ACCOUNT-ID"

# Deploy all stacks
cdk deploy --all

# Note the API Gateway URL from outputs
```

### 5. Test Deployment

```bash
# Test the deployed API
curl -X POST https://YOUR-API-GATEWAY-URL/prod/agent \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! What can you help me with?"}'
```

## 📁 Project Structure

```
.
├── agent/                  # Strands agent implementation
│   ├── agent.py           # Main agent configuration
│   ├── tools.py           # Custom tools
│   └── prompts.py         # System prompts
│
├── stacks/                # CDK infrastructure stacks
│   ├── security_stack.py  # KMS keys, IAM roles, Secrets Manager
│   └── agentcore_stack.py # S3, CloudWatch, runtime resources
│
├── lambda/                # Lambda function handlers
│   └── api_handler/       # API Gateway integration
│
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
│
├── app.py                 # CDK app entry point
├── cdk.json              # CDK configuration
└── requirements.txt      # Python dependencies
```

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agent --cov-report=html

# Run specific test suite
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Local Development

```bash
# Activate environment
source .venv/bin/activate

# Run agent locally
python agent/agent.py

# Synthesize CDK (check for errors)
cdk synth

# View CDK diff before deployment
cdk diff
```

### Adding Custom Tools

1. Define tool in `agent/tools.py`:
```python
from strands import tool

@tool
def my_custom_tool(input: str) -> str:
    """Tool description"""
    return f"Processed: {input}"
```

2. Register in `agent/agent.py`:
```python
agent = Agent(
    model=model,
    tools=[..., my_custom_tool],
    ...
)
```

## 🔐 Security Best Practices

- ✅ KMS encryption for all data at rest
- ✅ IAM roles with least privilege
- ✅ Secrets Manager for API keys
- ✅ VPC isolation (add `vpc_stack.py` for production)
- ✅ CloudWatch logging and monitoring
- ✅ Bedrock Guardrails (configure in `cdk.json`)

## 🚀 Latest Features (Claude 4.6)

- **1 Million Token Context**: Analyze entire codebases, long documents (no premium pricing)
- **64K Max Output**: 8x longer responses than Claude 3.5
- **1-Hour Prompt Caching**: 90% cost reduction + 85% latency reduction for repeated context
- **Extended Thinking**: Native reasoning API for complex multi-step problems
- **Enhanced Tool Use**: Parallel tool calling for faster agent execution
- **Knowledge Cutoff**: April 2025 (vs March 2025 for Claude 4)

## 📊 Monitoring & Observability

### CloudWatch Logs

```bash
# View agent logs
aws logs tail /aws/strands-agent/clash-of-agents --follow

# View Lambda logs
aws logs tail /aws/lambda/api-handler --follow
```

### CloudWatch Metrics

Access metrics in AWS Console:
- Lambda invocations, duration, errors
- Bedrock API calls and token usage
- S3 bucket operations

## 🎯 Competition Focus Areas

This implementation prioritizes:

1. **Security**: Encrypted storage, IAM policies, secret management
2. **Reliability**: Error handling, retries, graceful degradation
3. **Observability**: Structured logging, metrics, tracing
4. **Performance**: Lambda cold start optimization, efficient tool usage

## 📝 Configuration

### Environment Variables

Configure via `cdk.json` context:

```json
{
  "context": {
    "account": "YOUR-ACCOUNT-ID",
    "region": "us-west-2",
    "model_id": "us.anthropic.claude-sonnet-4-6",
    "cloudwatch_log_retention_days": 30,
    "extended_thinking_enabled": false,
    "extended_thinking_budget_tokens": 10000,
    "prompt_caching_enabled": true,
    "prompt_caching_ttl_seconds": 3600
  }
}
```

### Advanced Features

**Enable Extended Thinking** (for complex reasoning tasks):
```python
agent = create_agent(
    enable_extended_thinking=True,
    thinking_budget_tokens=10000
)
```

**Configure Prompt Caching** (default: 1-hour TTL):
```python
agent = create_agent(
    enable_prompt_caching=True,
    cache_ttl_seconds=3600  # 1 hour (3600) or 5 minutes (300)
)
```

**Adjust Max Output Tokens**:
```python
agent = create_agent(
    max_tokens=64000  # Up to 64K tokens (vs 8K in Claude 3.5)
)
```

### Customizing the Agent

Edit `agent/prompts.py` to modify:
- System prompt
- Task-specific prompts
- Error handling behavior
- Response formatting

## 🚢 Deployment Commands

```bash
# Deploy all stacks
cdk deploy --all

# Deploy specific stack
cdk deploy ClashOfAgents-SecurityStack

# Destroy all resources (cleanup)
cdk destroy --all
```

## 📚 Resources

- **Strands Docs**: https://strandsagents.com/docs/
- **AWS Bedrock**: https://aws.amazon.com/bedrock/
- **AWS CDK**: https://docs.aws.amazon.com/cdk/
- **Competition Info**: Contact AWS event organizers

## 🤝 Contributing

This is a competition entry. For collaborators:

1. Create feature branch
2. Add tests for new functionality
3. Ensure `pytest` and `cdk synth` pass
4. Submit PR with description

## 📄 License

MIT License - See LICENSE file for details

---

**Built for AWS Clash of Agents Competition**
