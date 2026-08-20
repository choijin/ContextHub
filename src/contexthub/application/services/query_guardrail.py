"""Deterministic guardrails for user query safety."""

import re
from dataclasses import dataclass

PROMPT_INJECTION_REFUSAL = (
    "I cannot answer requests that try to override instructions, reveal secrets, "
    "or access hidden system information."
)


@dataclass(frozen=True)
class QueryGuardrailResult:
    blocked: bool
    reason: str | None = None
    matched_pattern: str | None = None


class QueryGuardrail:
    """Detect direct prompt-injection and secret-exfiltration attempts."""

    _blocked_patterns = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"\bignore\b.{0,80}\b(previous|prior|above|all|system|developer|evaluation)\b.{0,80}\binstructions?\b",
            r"\b(disregard|bypass|override)\b.{0,80}\b(previous|prior|above|system|developer|safety|instructions?)\b",
            (
                r"\breveal\b.{0,80}\b(system prompt|hidden instructions?|developer "
                r"message|secrets?|api key|token|password|environment variables?)\b"
            ),
            (
                r"\b(return|print|show|display|exfiltrate|leak)\b.{0,80}\b(secrets?|"
                r"api key|token|password|environment variables?|system prompt|"
                r"hidden instructions?)\b"
            ),
            r"\byou are now\b.{0,80}\b(developer mode|admin|root|unrestricted|jailbreak)\b",
            r"\bdeveloper mode\b",
            r"\bjailbreak\b",
        ]
    ]

    def inspect(self, question: str) -> QueryGuardrailResult:
        normalized = " ".join(question.split())
        for pattern in self._blocked_patterns:
            if pattern.search(normalized):
                return QueryGuardrailResult(
                    blocked=True,
                    reason="prompt_injection_or_secret_exfiltration_attempt",
                    matched_pattern=pattern.pattern,
                )
        return QueryGuardrailResult(blocked=False)
