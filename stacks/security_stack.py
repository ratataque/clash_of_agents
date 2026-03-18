"""Security Stack - IAM role for Bedrock access"""

from aws_cdk import Stack, aws_iam as iam, aws_s3 as s3
from constructs import Construct


class SecurityStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        agent_bucket: s3.Bucket,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.agent_role = iam.Role(
            self,
            "AgentRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
            ),
        )

        self.agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[f"arn:aws:bedrock:{self.region}::foundation-model/*"],
            )
        )

        agent_bucket.grant_read_write(self.agent_role)
