"""
AgentCore Stack - Bedrock AgentCore Runtime, S3, ECR
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
    aws_kms as kms,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput,
)
from constructs import Construct


class AgentCoreStack(Stack):
    """Stack for AgentCore runtime and storage resources"""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        kms_key: kms.Key,
        agent_execution_role: iam.Role,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 Bucket for agent state, logs, and artifacts
        self.agent_bucket = s3.Bucket(
            self,
            "AgentBucket",
            encryption_key=kms_key,
            encryption=s3.BucketEncryption.KMS,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/testing
            auto_delete_objects=True,  # For dev/testing
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    noncurrent_version_expiration=Duration.days(30),
                ),
                s3.LifecycleRule(
                    id="TransitionToIA",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(90),
                        )
                    ],
                ),
            ],
        )
        
        # Grant bucket access to agent execution role
        self.agent_bucket.grant_read_write(agent_execution_role)
        
        # CloudWatch Log Group for agent logs
        self.agent_log_group = logs.LogGroup(
            self,
            "AgentLogGroup",
            log_group_name="/aws/strands-agent/clash-of-agents",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # Outputs
        CfnOutput(
            self,
            "AgentBucketName",
            value=self.agent_bucket.bucket_name,
            description="S3 bucket for agent storage",
        )
        
        CfnOutput(
            self,
            "AgentLogGroupName",
            value=self.agent_log_group.log_group_name,
            description="CloudWatch log group for agent logs",
        )
