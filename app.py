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

# AgentCore Stack - S3, CloudWatch (deployed first, no dependencies)
agentcore_stack = AgentCoreStack(
    app,
    f"{project_name}-AgentCoreStack",
    env=env,
    description="AgentCore runtime and agent deployment resources"
)

# Security Stack - KMS keys, IAM roles, Secrets Manager
security_stack = SecurityStack(
    app,
    f"{project_name}-SecurityStack",
    env=env,
    agent_bucket=agentcore_stack.agent_bucket,
    description="Security resources for Strands Agent deployment"
)
security_stack.add_dependency(agentcore_stack)

# Add tags to all resources
cdk.Tags.of(app).add("Project", project_name)
cdk.Tags.of(app).add("ManagedBy", "CDK")
cdk.Tags.of(app).add("Environment", "Competition")

app.synth()
