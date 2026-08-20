"""Deterministic guardrails for sensitive data leakage."""

import re
from dataclasses import dataclass

SENSITIVE_DATA_REFUSAL = (
    "I cannot provide sensitive personal information, credentials, or secrets from the documents."
)


@dataclass(frozen=True)
class SensitiveDataFinding:
    category: str
    matched_pattern: str


@dataclass(frozen=True)
class SensitiveDataGuardrailResult:
    blocked: bool
    findings: list[SensitiveDataFinding]


class SensitiveDataGuardrail:
    """Detect common PII and secret patterns in context or generated output."""

    _sensitive_patterns = [
        ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
        (
            "private_key",
            re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"),
        ),
        (
            "provider_token",
            re.compile(
                r"\b(?:sk-[A-Za-z0-9_-]{16,}|hf_[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9_]{20,})\b"
            ),
        ),
        (
            "secret_assignment",
            re.compile(
                r"\b(?:password|passwd|api[_-]?key|secret|token)\s*[:=]\s*"
                r"[\"']?[^\"'\s]{6,}",
                re.IGNORECASE,
            ),
        ),
        (
            "email",
            re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        ),
        (
            "phone_number",
            re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
        ),
    ]

    def inspect_text(self, text: str) -> SensitiveDataGuardrailResult:
        findings = [
            SensitiveDataFinding(category=category, matched_pattern=pattern.pattern)
            for category, pattern in self._sensitive_patterns
            if pattern.search(text)
        ]
        return SensitiveDataGuardrailResult(blocked=bool(findings), findings=findings)
