#!/usr/bin/env python3
"""
AWS CDK App for Strands Agent - Clash of Agents Competition
"""
import os
import aws_cdk as cdk
from stacks.security_stack import SecurityStack
from stacks.agentcore_stack import AgentCoreStack


app = cdk.App()

# Get configuration from context or environment
account = app.node.try_get_context("account") or os.environ.get("CDK_DEFAULT_ACCOUNT")
region = app.node.try_get_context("region") or os.environ.get("CDK_DEFAULT_REGION", "us-west-2")

env = cdk.Environment(account=account, region=region)

# Project name for resource naming
project_name = "ClashOfAgents"

# Security Stack - KMS keys, IAM roles, Secrets Manager
security_stack = SecurityStack(
    app,
    f"{project_name}-SecurityStack",
    env=env,
    description="Security resources for Strands Agent deployment"
)

# AgentCore Stack - Bedrock AgentCore Runtime, ECR, S3
agentcore_stack = AgentCoreStack(
    app,
    f"{project_name}-AgentCoreStack",
    env=env,
    kms_key=security_stack.kms_key,
    agent_execution_role=security_stack.agent_execution_role,
    description="AgentCore runtime and agent deployment resources"
)
agentcore_stack.add_dependency(security_stack)

# Add tags to all resources
cdk.Tags.of(app).add("Project", project_name)
cdk.Tags.of(app).add("ManagedBy", "CDK")
cdk.Tags.of(app).add("Environment", "Competition")

app.synth()
