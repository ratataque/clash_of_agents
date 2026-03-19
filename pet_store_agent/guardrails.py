import re
import unicodedata
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Import Bedrock Guardrails (optional - graceful fallback if not available)
try:
    from bedrock_guardrails import BedrockGuardrailsManager, BedrockGuardrailResult
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False
    BedrockGuardrailsManager = None
    BedrockGuardrailResult = None

logger = logging.getLogger(__name__)


@dataclass
class GuardrailDecision:
    blocked: bool
    code: Optional[str] = None
    message: Optional[str] = None
    matched_patterns: Optional[List[str]] = None
    severity: str = "low"  # low, medium, high, critical
    source: str = "pattern"  # pattern, bedrock_api, hybrid


class GuardrailEngine:
    """
    Hybrid guardrail engine with pattern matching + AWS Bedrock Guardrails API.
    
    Architecture:
    1. Fast pattern-based pre-filter (0-5ms) - blocks obvious attacks
    2. AWS Bedrock Guardrails API (100-300ms) - deep content analysis
    3. Fail-fast on critical threats, fail-open on API errors
    
    Improvements over basic pattern matching:
    - Severity levels for risk scoring
    - Unicode normalization for evasion resistance
    - Contextual commerce vs advice detection
    - Extensible pattern tiers
    - Managed AWS Bedrock policies (PII, toxic content, hallucination prevention)
    
    Inspired by: https://github.com/sendtoshailesh/amazon-bedrock-guardrails-guide
    """
    
    # Standard reject message matching official samples
    STANDARD_REJECT = "Sorry! We can't accept your request. What else do you need?"
    
    def __init__(self, use_bedrock_api: bool = False) -> None:
        """
        Initialize hybrid guardrail engine.
        
        Args:
            use_bedrock_api: Enable AWS Bedrock Guardrails API integration
                            (requires BEDROCK_GUARDRAILS_ENABLED=true env var)
        """
        # Initialize Bedrock Guardrails manager if available
        self.bedrock_manager = None
        if use_bedrock_api and BEDROCK_AVAILABLE:
            self.bedrock_manager = BedrockGuardrailsManager(enable_api=use_bedrock_api)
        
        # Tier 1: Critical security threats (severity: critical)
        # Tier 1: Critical security threats (severity: critical)
        self._injection_patterns = [
            r"ignore\s+all\s+previous\s+instructions",
            r"disregard\s+(?:all\s+)?(?:previous|prior|earlier)\s+(?:instructions?|prompts?)",
            r"reveal\s+(?:your\s+)?(?:system\s+)?prompt",
            r"(?:show|display|print)\s+(?:your\s+)?(?:system\s+)?prompt",
            r"(?:internal|hidden|secret)\s+(?:rules?|instructions?|prompts?)",
            r"jailbreak",
            r"developer\s+(?:message|mode|override)",
            r"bypass\s+(?:policy|guardrail|safety|security)",
            r"sudo\s+mode",
            r"admin\s+(?:mode|access|override)",
            r"forget\s+(?:all\s+)?(?:previous|prior)\s+instructions?",
            r"new\s+instruction",
            r"override\s+(?:previous|system)\s+instructions?",
        ]
        
        # Tier 2: Data exfiltration attempts (severity: critical)
        self._exfiltration_patterns = [
            r"display\s+all\s+customer\s+data",
            r"show\s+all\s+customer\s+(?:data|records|info)",
            r"list\s+all\s+(?:customers?|users?)",
            r"internal\s+product\s+codes?",
            r"dump\s+(?:data|database|records|table)",
            r"export\s+(?:all\s+)?(?:users?|customers?|data)",
            r"leak\s+(?:secrets?|credentials?|passwords?)",
            r"SELECT\s+\*\s+FROM",  # SQL injection attempt
            r"<script>",  # XSS attempt
        ]
        
        # Tier 3: Unsafe/harmful content (severity: high)
        self._unsafe_patterns = [
            r"harm\s+(?:an?\s+)?animals?",
            r"animal\s+cruelty",
            r"kill\s+(?:my\s+)?(?:dog|cat|animal|pet)",
            r"poison\s+(?:a\s+)?(?:dog|cat|animal|pet)",
            r"abuse\s+(?:a\s+)?(?:dog|cat|animal|pet)",
            r"hurt\s+(?:my\s+)?(?:dog|cat|animal|pet)",
            r"euthanize\s+(?:at\s+home|diy)",
        ]
        
        # Tier 4: Out-of-scope species (severity: medium)
        self._out_of_scope_species = [
            r"\bhamsters?\b",
            r"\bparrots?\b",
            r"\bmacaws?\b",
            r"\breptiles?\b",
            r"\bsnakes?\b",
            r"\blizards?\b",
            r"\bbird\s+seed\b",
            r"\bfish\s+(?:food|tank)\b",
            r"\bferrets?\b",
            r"\bgerbils?\b",
            r"\brabbits?\b",
            r"\bturtle\b",
        ]
        
        # Commerce intent markers
        self._commerce_markers = [
            "price",
            "buy",
            "order",
            "purchase",
            "stock",
            "units",
            "packages",
            "packs",
            "interested in",
            "available",
            "discount",
            "how much",
            "cost",
        ]
        
        # Advice-only markers (non-commerce)
        self._advice_markers = [
            "advice",
            "recommended",
            "how long",
            "duration",
            "exercise",
            "care",
            "food for my",
            "what should",
            "is it safe",
            "how often",
        ]

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Normalize text for evasion-resistant pattern matching.
        - Unicode normalization (handles homoglyphs, zero-width chars)
        - Lowercase conversion
        - Whitespace normalization
        """
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = normalized.lower()
        # Collapse multiple spaces and normalize line breaks
        normalized = re.sub(r"\s+", " ", normalized).strip()
        # Remove zero-width characters that might be used to evade
        normalized = re.sub(r"[\u200b-\u200f\ufeff]", "", normalized)
        return normalized

    def _find_matches(self, text: str, patterns: List[str]) -> List[str]:
        """Find all matching patterns in text (case-insensitive)."""
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                matches.append(pattern)
        return matches

    def _has_commerce_intent(self, text: str) -> bool:
        """Check if request has commercial intent (pricing, ordering)."""
        return any(marker in text for marker in self._commerce_markers)

    def _is_non_commerce_advice(self, text: str) -> bool:
        """Check if request is pure advice with no commercial component."""
        has_advice = any(marker in text for marker in self._advice_markers)
        return has_advice and not self._has_commerce_intent(text)
    
    def _calculate_risk_score(self, decision: GuardrailDecision) -> float:
        """Calculate risk score (0.0-1.0) based on severity and pattern count."""
        if not decision.blocked:
            return 0.0
        
        severity_weights = {
            "critical": 1.0,
            "high": 0.75,
            "medium": 0.5,
            "low": 0.25,
        }
        base_score = severity_weights.get(decision.severity, 0.5)
        
        # Escalate if multiple patterns matched
        pattern_multiplier = min(1.0 + (len(decision.matched_patterns or []) - 1) * 0.1, 1.5)
        return min(base_score * pattern_multiplier, 1.0)

    def evaluate(self, prompt: str, customer_request: str) -> GuardrailDecision:
        """
        Evaluate request through hybrid guardrails (pattern + Bedrock API).
        Returns decision with blocking verdict, code, severity, and message.
        
        Evaluation strategy:
        1. Fast pattern-based pre-filter (critical threats only)
        2. If patterns clear, optionally call Bedrock API for deep analysis
        3. Return first block or allow if both pass
        
        Evaluation order (fail-fast on critical threats):
        1. Prompt injection (critical) - pattern-based
        2. Data exfiltration (critical) - pattern-based
        3. Unsafe/harmful content (high) - pattern-based
        4. Out-of-scope species (medium) - pattern-based
        5. Non-commerce advice (low) - pattern-based
        6. Bedrock API validation (if enabled) - managed policies
        """
        normalized_prompt = self._normalize(prompt)
        normalized_request = self._normalize(customer_request)
        combined = f"{normalized_prompt} {normalized_request}".strip()

        # Tier 1: Prompt injection (critical) - fast pattern match
        injection = self._find_matches(combined, self._injection_patterns)
        if injection:
            return GuardrailDecision(
                blocked=True,
                code="prompt-injection",
                message=self.STANDARD_REJECT,
                matched_patterns=injection,
                severity="critical",
                source="pattern",
            )

        # Tier 2: Data exfiltration (critical) - fast pattern match
        exfiltration = self._find_matches(combined, self._exfiltration_patterns)
        if exfiltration:
            return GuardrailDecision(
                blocked=True,
                code="data-exfiltration",
                message=self.STANDARD_REJECT,
                matched_patterns=exfiltration,
                severity="critical",
                source="pattern",
            )

        # Tier 3: Unsafe/harmful content (high) - fast pattern match
        unsafe = self._find_matches(combined, self._unsafe_patterns)
        if unsafe:
            return GuardrailDecision(
                blocked=True,
                code="unsafe-request",
                message=self.STANDARD_REJECT,
                matched_patterns=unsafe,
                severity="high",
                source="pattern",
            )

        # Tier 4: Out-of-scope species (medium) - fast pattern match
        scope = self._find_matches(combined, self._out_of_scope_species)
        if scope:
            return GuardrailDecision(
                blocked=True,
                code="out-of-scope-species",
                message=self.STANDARD_REJECT,
                matched_patterns=scope,
                severity="medium",
                source="pattern",
            )

        # Tier 5: Non-commerce advice (low) - fast pattern match
        if self._is_non_commerce_advice(combined):
            return GuardrailDecision(
                blocked=True,
                code="non-commerce-advice",
                message=self.STANDARD_REJECT,
                matched_patterns=[],
                severity="low",
                source="pattern",
            )

        # Tier 6: AWS Bedrock Guardrails API (if enabled)
        if self.bedrock_manager:
            bedrock_result = self.bedrock_manager.apply_guardrail(
                content=combined,
                source_type="INPUT",
            )
            
            if bedrock_result.blocked:
                return GuardrailDecision(
                    blocked=True,
                    code="bedrock-api-blocked",
                    message=self.STANDARD_REJECT,
                    matched_patterns=[],
                    severity="high",
                    source="bedrock_api",
                )

        # Clean request - allow through
        return GuardrailDecision(
            blocked=False,
            severity="low",
            source="pattern" if not self.bedrock_manager else "hybrid",
        )

    def get_policy_stats(self) -> Dict[str, int]:
        """Return counts of patterns in each policy tier."""
        return {
            "injection_patterns": len(self._injection_patterns),
            "exfiltration_patterns": len(self._exfiltration_patterns),
            "unsafe_patterns": len(self._unsafe_patterns),
            "out_of_scope_species": len(self._out_of_scope_species),
        }
    
    @staticmethod
    def suggested_enhancements() -> List[Dict[str, str]]:
        """
        Advanced guardrail features for production deployments.
        Current implementation provides hybrid pattern + Bedrock API protection.
        
        Best practices from: https://github.com/sendtoshailesh/amazon-bedrock-guardrails-guide
        """
        return [
            {
                "name": "✅ AWS Bedrock Guardrails API (IMPLEMENTED)",
                "description": "Managed policy checks for PII, toxic content, prompt attacks, topic filtering. Reduces pattern maintenance burden.",
            },
            {
                "name": "Contextual grounding validation",
                "description": "Validate responses against Knowledge Base sources to prevent hallucinations. Score threshold: 0.75 for grounding, 0.70 for relevance.",
            },
            {
                "name": "Semantic similarity detection",
                "description": "Embed known attack patterns and compare cosine similarity to detect novel jailbreak attempts that evade regex.",
            },
            {
                "name": "Rate limiting + session tracking",
                "description": "Track repeated policy violations per session/user and apply progressive throttling or blocking.",
            },
            {
                "name": "Output validation guardrails",
                "description": "Scan generated responses for accidental leaks (product codes, PII, system info) before returning to callers. Use Bedrock API with source=OUTPUT.",
            },
            {
                "name": "CloudWatch Metrics + Alarms",
                "description": "Emit guardrail decision telemetry (blocked/allowed, severity, code, latency) for trend analysis and anomaly detection.",
            },
            {
                "name": "Dynamic pattern updates",
                "description": "Load patterns from S3/DynamoDB for zero-downtime policy updates without redeployment.",
            },
            {
                "name": "Adversarial testing suite",
                "description": "Automated red-team attacks (obfuscation, encoding, linguistic tricks) to validate pattern + API robustness.",
            },
            {
                "name": "Versioned guardrail policies",
                "description": "Use Bedrock guardrail versions for stable prod deployments. DRAFT for testing, numbered versions for production.",
            },
            {
                "name": "Automated reasoning validation",
                "description": "Validate numerical calculations and business logic in responses (e.g., pricing math, discount accuracy).",
            },
        ]
