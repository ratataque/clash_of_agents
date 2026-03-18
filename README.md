# AWS Strands Agent - Competition Entry

Minimal Strands agent for AWS Bedrock + CDK deployment.

## Setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Local Test

```bash
python agent/agent.py
```

## Deploy

```bash
# Update cdk.json with your account ID
aws sts get-caller-identity --query Account --output text

# Bootstrap (first time)
cdk bootstrap

# Deploy
cdk deploy --all
```

## Structure

```
agent/
  agent.py       # Agent config
  tools.py       # Custom tools
  prompts.py     # System prompts
stacks/
  agentcore_stack.py   # S3 bucket
  security_stack.py    # IAM role
app.py           # CDK entry
```

## Config

Edit `cdk.json`:
- `account`: AWS account ID
- `region`: AWS region
- `model_id`: Bedrock model

Enable Bedrock model access in AWS Console → Bedrock → Model access.
