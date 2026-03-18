import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class GuardrailDecision:
    blocked: bool
    code: Optional[str] = None
    message: Optional[str] = None
    matched_patterns: Optional[List[str]] = None


class GuardrailEngine:
    def __init__(self) -> None:
        self._injection_patterns = [
            r"ignore\s+all\s+previous\s+instructions",
            r"reveal\s+(?:your\s+)?system\s+prompt",
            r"(?:internal|hidden)\s+rules",
            r"jailbreak",
            r"developer\s+message",
            r"bypass\s+(?:policy|guardrail|safety)",
        ]
        self._exfiltration_patterns = [
            r"display\s+all\s+customer\s+data",
            r"show\s+all\s+customer\s+data",
            r"internal\s+product\s+codes",
            r"dump\s+(?:data|database|records)",
            r"export\s+(?:all\s+)?users?",
            r"leak\s+(?:secrets?|credentials?)",
        ]
        self._unsafe_patterns = [
            r"harm\s+animals?",
            r"animal\s+cruelty",
            r"kill\s+animals?",
            r"poison\s+(?:a\s+)?(?:dog|cat|animal)",
            r"abuse\s+(?:a\s+)?(?:dog|cat|animal)",
        ]
        self._out_of_scope_species = [
            r"\bhamster\b",
            r"\bparrot\b",
            r"\bmacaw\b",
            r"\breptile\b",
            r"\bsnake\b",
            r"\blizard\b",
            r"\bbird\s+seed\b",
        ]
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
        ]
        self._advice_markers = [
            "advice",
            "recommended",
            "how long",
            "duration",
            "exercise",
            "care",
            "food for my",
            "what should",
        ]

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = normalized.lower()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _find_matches(self, text: str, patterns: List[str]) -> List[str]:
        matches = []
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                matches.append(pattern)
        return matches

    def _has_commerce_intent(self, text: str) -> bool:
        return any(marker in text for marker in self._commerce_markers)

    def _is_non_commerce_advice(self, text: str) -> bool:
        has_advice = any(marker in text for marker in self._advice_markers)
        return has_advice and not self._has_commerce_intent(text)

    def evaluate(self, prompt: str, customer_request: str) -> GuardrailDecision:
        normalized_prompt = self._normalize(prompt)
        normalized_request = self._normalize(customer_request)
        combined = f"{normalized_prompt} {normalized_request}".strip()

        injection = self._find_matches(combined, self._injection_patterns)
        if injection:
            return GuardrailDecision(
                blocked=True,
                code="prompt-injection",
                message="We are sorry, we can't accept your request. What else do you need?",
                matched_patterns=injection,
            )

        exfiltration = self._find_matches(combined, self._exfiltration_patterns)
        if exfiltration:
            return GuardrailDecision(
                blocked=True,
                code="data-exfiltration",
                message="We are sorry, we can't accept your request. What else do you need?",
                matched_patterns=exfiltration,
            )

        unsafe = self._find_matches(combined, self._unsafe_patterns)
        if unsafe:
            return GuardrailDecision(
                blocked=True,
                code="unsafe-request",
                message="We are sorry, we can't accept your request. What else do you need?",
                matched_patterns=unsafe,
            )

        scope = self._find_matches(combined, self._out_of_scope_species)
        if scope:
            return GuardrailDecision(
                blocked=True,
                code="out-of-scope-species",
                message="We are sorry, we can't accept your request. What else do you need?",
                matched_patterns=scope,
            )

        if self._is_non_commerce_advice(combined):
            return GuardrailDecision(
                blocked=True,
                code="non-commerce-advice",
                message="We are sorry, we can't accept your request. What else do you need?",
                matched_patterns=[],
            )

        return GuardrailDecision(blocked=False)

    @staticmethod
    def suggested_enhancements() -> List[Dict[str, str]]:
        return [
            {
                "name": "Bedrock ApplyGuardrail integration",
                "description": "Apply managed policy checks for toxic content, prompt attacks, and topic restrictions before orchestration.",
            },
            {
                "name": "Risk scoring",
                "description": "Score each request and route high-risk requests to stricter policies or human review.",
            },
            {
                "name": "Session memory guardrails",
                "description": "Track repeated policy-evading behavior across turns and progressively tighten allowed actions.",
            },
            {
                "name": "Structured policy telemetry",
                "description": "Emit guardrail decision events to CloudWatch Metrics for alerting and trend analysis.",
            },
            {
                "name": "Output redaction",
                "description": "Post-process generated responses to mask accidental sensitive references before returning to callers.",
            },
        ]
