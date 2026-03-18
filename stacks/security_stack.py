"""
Security Stack - KMS keys, IAM roles, Secrets Manager
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_kms as kms,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class SecurityStack(Stack):
    """Stack for security resources: KMS keys, IAM roles, secrets"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # KMS Key for encryption at rest
        self.kms_key = kms.Key(
            self,
            "AgentKmsKey",
            description="KMS key for Strands agent encryption",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/testing - change for production
        )
        
        # IAM Role for Agent Execution
        self.agent_execution_role = iam.Role(
            self,
            "AgentExecutionRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
            description="Execution role for Strands agent",
        )
        
        # Grant Bedrock model access
        self.agent_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/*",
                ],
            )
        )
        
        # Grant KMS access
        self.kms_key.grant_encrypt_decrypt(self.agent_execution_role)
        
        # CloudWatch Logs permissions
        self.agent_execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )
        
        # Secrets Manager for API keys and sensitive config
        self.agent_secrets = secretsmanager.Secret(
            self,
            "AgentSecrets",
            description="Secrets for Strands agent (API keys, tokens, etc.)",
            encryption_key=self.kms_key,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/testing
        )
        
        # Grant secret read access to agent role
        self.agent_secrets.grant_read(self.agent_execution_role)
