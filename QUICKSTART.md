# Quick Start Guide

## ✅ Project Successfully Initialized!

Your Strands agent project for AWS Clash of Agents is ready to deploy.

## 🔧 What Was Fixed

**Issue**: Cyclic dependency between SecurityStack and AgentCoreStack
**Solution**: Reversed stack order - AgentCoreStack deploys first (no dependencies), then SecurityStack references the S3 bucket and grants IAM permissions

## 📦 Current Stack Order

1. **ClashOfAgents-AgentCoreStack** - S3 bucket, CloudWatch logs (no dependencies)
2. **ClashOfAgents-SecurityStack** - KMS keys, IAM roles, secrets (depends on AgentCoreStack)

## 🚀 Next Steps

### 1. Install Dependencies (if not done)

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure AWS Account

Edit `cdk.json` and add your AWS account ID:

```json
{
  "context": {
    "account": "YOUR-ACCOUNT-ID-HERE",
    "region": "us-west-2"
  }
}
```

Find your account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

### 3. Bootstrap CDK (First Time Only)

```bash
# Install CDK CLI globally
npm install -g aws-cdk

# Bootstrap your account
cdk bootstrap aws://YOUR-ACCOUNT-ID/us-west-2
```

### 4. Enable Bedrock Model Access

Go to AWS Console:
1. Navigate to Amazon Bedrock
2. Click "Model access" in left sidebar
3. Click "Manage model access"
4. Enable: **Claude Sonnet 4** (`us.anthropic.claude-sonnet-4-20250514-v1:0`)
5. Submit request (usually instant approval for most accounts)

### 5. Test Agent Locally

```bash
# Run the agent
python agent/agent.py
```

Expected output:
```
Initializing Strands agent...

Agent Response:
[Agent's response with current time and calculation]
```

### 6. Deploy to AWS

```bash
# View what will be deployed
cdk diff

# Deploy all stacks
cdk deploy --all

# Or deploy individually
cdk deploy ClashOfAgents-AgentCoreStack
cdk deploy ClashOfAgents-SecurityStack
```

### 7. Verify Deployment

Check the outputs for:
- S3 bucket name
- CloudWatch log group name
- IAM role ARN

```bash
# View stack outputs
aws cloudformation describe-stacks \
  --stack-name ClashOfAgents-AgentCoreStack \
  --query 'Stacks[0].Outputs'
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit/

# Run all tests
pytest

# Run with coverage
pytest --cov=agent --cov-report=html
```

## 📝 Customization

### Add Custom Tools

Edit `agent/tools.py`:

```python
@tool
def my_tool(query: str) -> str:
    """Your custom tool logic"""
    return f"Result: {query}"
```

Register in `agent/agent.py`:

```python
agent = Agent(
    model=model,
    tools=[calculator, current_time, my_tool],
    ...
)
```

### Modify System Prompt

Edit `agent/prompts.py` to change agent behavior.

### Add More Stacks

Create new stacks in `stacks/` directory:
- `vpc_stack.py` - For VPC networking
- `api_stack.py` - For API Gateway
- `monitoring_stack.py` - For dashboards and alarms

## 🐛 Troubleshooting

### CDK Synthesis Fails

```bash
# Clear CDK cache
rm -rf cdk.out
cdk synth
```

### Import Errors in Python

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Bedrock Access Denied

Ensure:
1. Model access is enabled in Bedrock console
2. IAM role has `bedrock:InvokeModel` permission
3. Using correct region (us-west-2)

### Stack Deployment Fails

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name ClashOfAgents-SecurityStack \
  --max-items 10
```

## 📚 Resources

- **Strands Docs**: https://strandsagents.com/docs/
- **AWS Bedrock**: https://docs.aws.amazon.com/bedrock/
- **AWS CDK Guide**: https://docs.aws.amazon.com/cdk/v2/guide/home.html
- **Project README**: See `README.md` for full documentation

## 🎯 Competition Checklist

- [x] Strands agent implementation
- [x] AWS CDK infrastructure
- [x] Security (KMS, IAM, Secrets)
- [x] Observability (CloudWatch)
- [x] Testing framework
- [ ] Enable Bedrock model access
- [ ] Deploy to AWS
- [ ] Add custom competition logic
- [ ] Performance optimization
- [ ] Documentation updates

## 💡 Tips

1. **Start simple**: Get basic deployment working before adding complexity
2. **Test locally**: Use `python agent/agent.py` to test agent logic
3. **Monitor costs**: Use AWS Cost Explorer to track Bedrock usage
4. **Use CloudWatch**: Check logs for debugging deployed agent
5. **Iterate fast**: Use `cdk deploy` for quick infrastructure updates

---

**Your project is ready! Start with step 1 above and work through the setup.**
