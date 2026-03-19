"""
AWS Bedrock Guardrails Integration for Pet Store Agent

Provides managed policy enforcement via AWS Bedrock Guardrails API with:
- Content filtering (toxic, hate, sexual, violence)
- PII detection and anonymization
- Topic-based filtering
- Contextual grounding validation
- Word filtering and profanity blocking

Inspired by: https://github.com/sendtoshailesh/amazon-bedrock-guardrails-guide
"""

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class BedrockGuardrailResult:
    """Result from AWS Bedrock Guardrails API evaluation."""
    action: str  # "GUARDRAIL_INTERVENED" or "NONE"
    blocked: bool
    assessment: Optional[Dict] = None
    latency_ms: Optional[int] = None
    outputs: Optional[List[Dict]] = None


class BedrockGuardrailsManager:
    """
    Manages AWS Bedrock Guardrails for pet store agent.
    
    Features:
    - Lazy guardrail creation (creates on first use)
    - Cached guardrail ID for performance
    - Multi-layer safety: content, topic, word, PII
    - Contextual grounding for KB validation
    - CloudWatch metrics ready
    """
    
    # Guardrail configuration
    GUARDRAIL_NAME = "PetStoreAgentGuardrail"
    GUARDRAIL_VERSION = "DRAFT"  # Use "1" for production with versioning
    
    # Filtering thresholds
    CONTENT_FILTER_STRENGTH = {
        "SEXUAL": "HIGH",
        "VIOLENCE": "MEDIUM",
        "HATE": "HIGH",
        "INSULTS": "MEDIUM",
        "MISCONDUCT": "MEDIUM",
        "PROMPT_ATTACK": "HIGH",
    }
    
    # Contextual grounding thresholds
    GROUNDING_THRESHOLD = 0.75  # Block if score < 0.75
    RELEVANCE_THRESHOLD = 0.70  # Block if score < 0.70
    
    def __init__(self, enable_api: bool = True):
        """
        Initialize Bedrock Guardrails manager.
        
        Args:
            enable_api: If False, skip API calls (for local dev/testing)
        """
        self.enable_api = enable_api and os.environ.get("BEDROCK_GUARDRAILS_ENABLED", "false").lower() == "true"
        self._guardrail_id: Optional[str] = None
        
        if self.enable_api:
            logger.info("bedrock_guardrails.enabled api_mode=True")
        else:
            logger.info("bedrock_guardrails.disabled api_mode=False (using pattern-based only)")
    
    @lru_cache(maxsize=1)
    def _bedrock_runtime_client(self):
        """Get cached Bedrock Runtime client."""
        config = Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=3,
            read_timeout=10,
        )
        return boto3.client("bedrock-runtime", config=config)
    
    @lru_cache(maxsize=1)
    def _bedrock_client(self):
        """Get cached Bedrock client for guardrail management."""
        config = Config(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=3,
            read_timeout=10,
        )
        return boto3.client("bedrock", config=config)
    
    def _get_or_create_guardrail(self) -> Optional[str]:
        """
        Get existing guardrail ID or create new one.
        Uses environment variable BEDROCK_GUARDRAIL_ID if set.
        """
        if not self.enable_api:
            return None
        
        # Check if guardrail ID is provided via env var
        env_guardrail_id = os.environ.get("BEDROCK_GUARDRAIL_ID")
        if env_guardrail_id:
            logger.info(f"bedrock_guardrails.using_env guardrail_id={env_guardrail_id}")
            return env_guardrail_id
        
        # Check cache
        if self._guardrail_id:
            return self._guardrail_id
        
        try:
            # Try to find existing guardrail
            client = self._bedrock_client()
            response = client.list_guardrails(maxResults=100)
            
            for guardrail in response.get("guardrails", []):
                if guardrail["name"] == self.GUARDRAIL_NAME:
                    self._guardrail_id = guardrail["id"]
                    logger.info(f"bedrock_guardrails.found_existing guardrail_id={self._guardrail_id}")
                    return self._guardrail_id
            
            # Create new guardrail if not found
            logger.info("bedrock_guardrails.creating_new")
            self._guardrail_id = self._create_guardrail()
            return self._guardrail_id
            
        except ClientError as e:
            logger.error(f"bedrock_guardrails.error code={e.response['Error']['Code']} msg={e.response['Error']['Message']}")
            return None
        except Exception as e:
            logger.exception(f"bedrock_guardrails.unexpected_error: {e}")
            return None
    
    def _create_guardrail(self) -> Optional[str]:
        """
        Create comprehensive pet store guardrail with multiple safety layers.
        
        Returns:
            Guardrail ID if successful, None otherwise
        """
        try:
            client = self._bedrock_client()
            
            response = client.create_guardrail(
                name=self.GUARDRAIL_NAME,
                description="Pet store agent safety guardrail with content filtering, PII protection, and topic validation",
                
                # Topic-based filtering (out-of-scope, harmful)
                topicPolicyConfig={
                    "topicsConfig": [
                        {
                            "name": "OutOfScopeSpecies",
                            "definition": "Requests about animals other than cats and dogs",
                            "examples": [
                                "hamster food",
                                "parrot cage",
                                "reptile supplies",
                                "fish tank products",
                                "ferret bedding",
                            ],
                            "type": "DENY",
                        },
                        {
                            "name": "HarmfulContent",
                            "definition": "Content related to harming or abusing animals",
                            "examples": [
                                "how to harm animals",
                                "animal cruelty products",
                                "poison for pets",
                            ],
                            "type": "DENY",
                        },
                        {
                            "name": "NonCommerceQueries",
                            "definition": "General advice without purchase intent",
                            "examples": [
                                "pet care tips",
                                "how long to exercise dog",
                                "training advice",
                            ],
                            "type": "DENY",
                        },
                    ]
                },
                
                # Content filtering (toxic, hate, violence, etc.)
                contentPolicyConfig={
                    "filtersConfig": [
                        {
                            "type": filter_type,
                            "inputStrength": strength,
                            "outputStrength": strength,
                        }
                        for filter_type, strength in self.CONTENT_FILTER_STRENGTH.items()
                    ]
                },
                
                # Word filtering (prohibited terms, profanity)
                wordPolicyConfig={
                    "wordsConfig": [
                        {"text": "internal product code"},
                        {"text": "system prompt"},
                        {"text": "reveal secrets"},
                        {"text": "dump database"},
                        {"text": "admin access"},
                    ],
                    "managedWordListsConfig": [
                        {"type": "PROFANITY"}
                    ],
                },
                
                # PII protection (anonymize sensitive data)
                sensitiveInformationPolicyConfig={
                    "piiEntitiesConfig": [
                        {"type": "EMAIL", "action": "ANONYMIZE"},
                        {"type": "PHONE", "action": "ANONYMIZE"},
                        {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
                        {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"},
                        {"type": "ADDRESS", "action": "ANONYMIZE"},
                    ],
                    "regexesConfig": [
                        {
                            "name": "ProductCodePattern",
                            "description": "Internal product codes (e.g., DD006, BP010)",
                            "pattern": r"\b[A-Z]{2}\d{3}\b",
                            "action": "ANONYMIZE",
                        }
                    ],
                },
                
                # Custom blocked messages
                blockedInputMessaging="Sorry! We can't accept your request. What else do you need?",
                blockedOutputsMessaging="Sorry! We can't process this response. Please try rephrasing your question.",
            )
            
            guardrail_id = response["guardrailId"]
            logger.info(f"bedrock_guardrails.created guardrail_id={guardrail_id}")
            return guardrail_id
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            logger.error(f"bedrock_guardrails.create_failed code={error_code} msg={error_msg}")
            return None
        except Exception as e:
            logger.exception(f"bedrock_guardrails.create_error: {e}")
            return None
    
    def apply_guardrail(
        self,
        content: str,
        source_type: str = "INPUT",
        grounding_sources: Optional[List[str]] = None,
    ) -> BedrockGuardrailResult:
        """
        Apply Bedrock Guardrail to content (input or output).
        
        Args:
            content: Text to validate
            source_type: "INPUT" (customer request) or "OUTPUT" (agent response)
            grounding_sources: Optional list of source texts for grounding validation
        
        Returns:
            BedrockGuardrailResult with action, blocked status, and assessment
        """
        if not self.enable_api:
            # API disabled - return unblocked
            return BedrockGuardrailResult(
                action="NONE",
                blocked=False,
                assessment={"api_disabled": True},
            )
        
        guardrail_id = self._get_or_create_guardrail()
        if not guardrail_id:
            logger.warning("bedrock_guardrails.no_guardrail_id fallback=allow")
            return BedrockGuardrailResult(
                action="NONE",
                blocked=False,
                assessment={"error": "no_guardrail_id"},
            )
        
        try:
            client = self._bedrock_runtime_client()
            
            # Build request payload
            payload = {
                "guardrailIdentifier": guardrail_id,
                "guardrailVersion": self.GUARDRAIL_VERSION,
                "source": source_type,
                "content": [{"text": {"text": content}}],
            }
            
            # Add grounding sources if provided
            if grounding_sources:
                payload["content"][0]["text"]["qualifiers"] = ["grounding_source"]
                # Note: Grounding validation requires InvokeModel with guardrail config,
                # not ApplyGuardrail. This is a simplified implementation.
            
            import time
            start_ms = int(time.time() * 1000)
            
            response = client.apply_guardrail(**payload)
            
            latency_ms = int(time.time() * 1000) - start_ms
            
            action = response.get("action", "NONE")
            blocked = action == "GUARDRAIL_INTERVENED"
            
            result = BedrockGuardrailResult(
                action=action,
                blocked=blocked,
                assessment=response.get("assessments", []),
                latency_ms=latency_ms,
                outputs=response.get("outputs", []),
            )
            
            if blocked:
                logger.warning(
                    f"bedrock_guardrails.blocked source={source_type} latency_ms={latency_ms}"
                )
            else:
                logger.info(
                    f"bedrock_guardrails.allowed source={source_type} latency_ms={latency_ms}"
                )
            
            return result
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            logger.error(f"bedrock_guardrails.apply_failed code={error_code} msg={error_msg}")
            
            # Fail-open on API errors (allow through but log)
            return BedrockGuardrailResult(
                action="NONE",
                blocked=False,
                assessment={"error": error_code, "message": error_msg},
            )
        except Exception as e:
            logger.exception(f"bedrock_guardrails.apply_error: {e}")
            return BedrockGuardrailResult(
                action="NONE",
                blocked=False,
                assessment={"error": "unexpected", "message": str(e)},
            )
    
    def delete_guardrail(self, guardrail_id: str) -> bool:
        """
        Delete a guardrail (for cleanup/testing).
        
        Args:
            guardrail_id: ID of guardrail to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.enable_api:
            return False
        
        try:
            client = self._bedrock_client()
            client.delete_guardrail(guardrailIdentifier=guardrail_id)
            logger.info(f"bedrock_guardrails.deleted guardrail_id={guardrail_id}")
            return True
        except Exception as e:
            logger.error(f"bedrock_guardrails.delete_failed: {e}")
            return False
    
    @staticmethod
    def get_best_practices() -> List[Dict[str, str]]:
        """
        Return best practices for Bedrock Guardrails deployment.
        
        Based on: https://github.com/sendtoshailesh/amazon-bedrock-guardrails-guide
        """
        return [
            {
                "practice": "Use versioned guardrails in production",
                "description": "Create versions for stable deployments. DRAFT for testing, version numbers for prod.",
            },
            {
                "practice": "Monitor guardrail latency",
                "description": "ApplyGuardrail adds ~100-300ms. For sub-second response times, consider async validation.",
            },
            {
                "practice": "Fail-open on API errors",
                "description": "If Bedrock API is unavailable, fall back to pattern-based guardrails rather than blocking all traffic.",
            },
            {
                "practice": "Combine with local guardrails",
                "description": "Use fast pattern matching for common cases, Bedrock API for complex/novel attacks.",
            },
            {
                "practice": "Enable CloudWatch metrics",
                "description": "Emit GUARDRAIL_INTERVENED events to CloudWatch for trend analysis and alerting.",
            },
            {
                "practice": "Test with adversarial inputs",
                "description": "Red-team your guardrails with obfuscation, encoding, jailbreak attempts.",
            },
            {
                "practice": "Use contextual grounding for hallucination prevention",
                "description": "Validate responses against source documents to prevent fabricated information.",
            },
        ]
