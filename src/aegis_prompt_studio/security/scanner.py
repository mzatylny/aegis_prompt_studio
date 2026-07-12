from __future__ import annotations

import re
from dataclasses import dataclass
from time import perf_counter

from aegis_prompt_studio.models import (
    Finding,
    SecurityCategory,
    SecurityScanRequest,
    SecurityScanResult,
    Severity,
)
from aegis_prompt_studio.security.hardening import build_hardened_prompt, recommended_controls
from aegis_prompt_studio.security.normalization import decode_candidates, normalize_text


@dataclass(frozen=True)
class Rule:
    category: SecurityCategory
    severity: Severity
    title: str
    description: str
    pattern: re.Pattern[str]
    weight: int
    remediation: str


def _rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)


RULES: tuple[Rule, ...] = (
    Rule(
        SecurityCategory.INSTRUCTION_OVERRIDE,
        Severity.CRITICAL,
        "Instruction hierarchy override",
        "The content attempts to replace or ignore higher-priority instructions.",
        _rx(r"\b(ignore|disregard|forget|override|bypass)\b.{0,80}\b(previous|prior|above|system|developer|instructions?|rules?|policy)\b"),
        34,
        "Keep instruction hierarchy outside user content and reject override language.",
    ),
    Rule(
        SecurityCategory.SYSTEM_PROMPT_EXFILTRATION,
        Severity.CRITICAL,
        "System prompt extraction",
        "The content asks for hidden instructions, policies, or internal configuration.",
        _rx(r"\b(reveal|show|print|repeat|dump|expose|leak|return)\b.{0,90}\b(system prompt|developer message|hidden instructions?|internal policy|initial prompt|chain of thought)\b"),
        38,
        "Never place secrets in prompts and block requests for hidden instruction content.",
    ),
    Rule(
        SecurityCategory.DATA_EXFILTRATION,
        Severity.CRITICAL,
        "Sensitive data exfiltration",
        "The content requests credentials, secrets, private data, or environment values.",
        _rx(r"\b(api[_ -]?key|password|secret|token|credential|private key|environment variables?|\.env|customer data)\b.{0,100}\b(send|show|print|upload|post|email|exfiltrate|return|reveal)\b|\b(send|show|print|upload|post|email|exfiltrate|return|reveal)\b.{0,100}\b(api[_ -]?key|password|secret|token|credential|private key|\.env)\b"),
        40,
        "Redact secrets before model input and prohibit outbound transmission of sensitive data.",
    ),
    Rule(
        SecurityCategory.TOOL_ABUSE,
        Severity.HIGH,
        "Unauthorized tool or command use",
        "The content attempts to trigger commands, tools, browsing, file access, or external side effects.",
        _rx(r"\b(run|execute|call|invoke|open|download|browse|visit|curl|wget|shell|terminal|delete|transfer)\b.{0,80}\b(tool|command|script|file|url|website|endpoint|database|email|payment|rm\s+-rf)\b"),
        27,
        "Use tool allowlists, validate arguments, and require confirmation for side effects.",
    ),
    Rule(
        SecurityCategory.INDIRECT_INJECTION,
        Severity.HIGH,
        "Indirect prompt injection",
        "The content frames embedded or retrieved text as instructions to follow.",
        _rx(r"\b(document|webpage|website|email|attachment|retrieved text|search result|file)\b.{0,100}\b(says|contains|instructs|tells you)\b.{0,100}\b(follow|obey|execute|prioritize|must)\b"),
        29,
        "Treat retrieved content as untrusted evidence and strip embedded instructions.",
    ),
    Rule(
        SecurityCategory.ROLE_MANIPULATION,
        Severity.HIGH,
        "Role manipulation",
        "The content attempts to assign a privileged or unrestricted persona.",
        _rx(r"\b(you are now|act as|pretend to be|switch to|enter)\b.{0,70}\b(developer|system|administrator|root|unrestricted|jailbreak|dan|security auditor)\b"),
        25,
        "Do not allow user content to redefine the model's authority or role.",
    ),
    Rule(
        SecurityCategory.SOCIAL_ENGINEERING,
        Severity.MEDIUM,
        "Authority or urgency pressure",
        "The content uses claimed authority, urgency, or consequences to bypass controls.",
        _rx(r"\b(authorized by|approved by|administrator says|urgent|immediately|required for compliance|do not question|failure to comply)\b"),
        15,
        "Verify authorization outside the model and ignore urgency-based policy changes.",
    ),
    Rule(
        SecurityCategory.DELIMITER_ESCAPE,
        Severity.HIGH,
        "Delimiter or markup breakout",
        "The content attempts to close trusted-data boundaries or hide instructions in markup.",
        _rx(r"</?(system|developer|trusted_context|instructions?|prompt|tool)>|```\s*(system|developer)|<!--.{0,500}(ignore|instruction|system)"),
        24,
        "Escape user-controlled delimiters and use structured message boundaries.",
    ),
    Rule(
        SecurityCategory.ENCODING_EVASION,
        Severity.MEDIUM,
        "Encoded payload",
        "The content contains a long encoded sequence that may conceal instructions.",
        _rx(r"\b(?:[A-Za-z0-9+/]{24,}={0,2}|(?:[0-9A-Fa-f]{2}){12,}|(?:%[0-9A-Fa-f]{2}){6,})\b"),
        18,
        "Decode and inspect plausible encoded content before model processing.",
    ),
    Rule(
        SecurityCategory.OBFUSCATION,
        Severity.MEDIUM,
        "Obfuscated instruction text",
        "The content uses invisible characters or spaced lettering to evade matching.",
        _rx(r"[\u200B-\u200D\u2060\uFEFF]|\b(?:i\W*g\W*n\W*o\W*r\W*e|s\W*y\W*s\W*t\W*e\W*m)\b"),
        20,
        "Normalize Unicode, remove zero-width characters, and rescan normalized content.",
    ),
)


SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class PromptSecurityScanner:
    def __init__(self, max_chars: int = 50_000) -> None:
        self.max_chars = max_chars

    def scan(self, request: SecurityScanRequest | str) -> SecurityScanResult:
        started = perf_counter()
        if isinstance(request, str):
            request = SecurityScanRequest(text=request)
        original = request.text[: self.max_chars]
        normalized = normalize_text(original)
        decoded = decode_candidates(normalized) if request.decode_obfuscation else []

        findings: list[Finding] = []
        findings.extend(self._scan_text(original, label="original"))
        if normalized != original:
            findings.extend(self._scan_text(normalized, label="normalized"))
        for index, candidate in enumerate(decoded, start=1):
            findings.extend(self._scan_text(candidate, label=f"decoded-{index}"))

        findings = self._deduplicate(findings)
        risk_score = self._score(findings)
        risk_level = self._risk_level(risk_score)
        summary = self._summary(risk_score, risk_level, findings)
        hardened = build_hardened_prompt(original, findings) if request.include_hardened_prompt else None

        elapsed_ms = round((perf_counter() - started) * 1000, 2)
        return SecurityScanResult(
            risk_score=risk_score,
            risk_level=risk_level,
            summary=summary,
            findings=findings,
            normalized_text=normalized,
            decoded_candidates=decoded,
            hardened_prompt=hardened,
            recommended_controls=recommended_controls(findings),
            metrics={
                "input_characters": len(original),
                "normalized_characters": len(normalized),
                "decoded_candidates": len(decoded),
                "finding_count": len(findings),
                "scan_time_ms": elapsed_ms,
            },
        )

    def _scan_text(self, text: str, label: str) -> list[Finding]:
        findings: list[Finding] = []
        for rule in RULES:
            for match in rule.pattern.finditer(text):
                evidence = match.group(0).strip().replace("\n", " ")[:220]
                findings.append(
                    Finding(
                        category=rule.category,
                        severity=rule.severity,
                        title=rule.title,
                        description=f"{rule.description} Detection source: {label}.",
                        evidence=evidence,
                        start=match.start() if label == "original" else None,
                        end=match.end() if label == "original" else None,
                        confidence=0.92 if label == "original" else 0.84,
                        weight=rule.weight,
                        remediation=rule.remediation,
                    )
                )
                # One finding per rule/source prevents repeated tokens from dominating the score.
                break
        return findings

    @staticmethod
    def _deduplicate(findings: list[Finding]) -> list[Finding]:
        best: dict[tuple[str, str], Finding] = {}
        for finding in findings:
            key = (finding.category.value, finding.evidence.lower())
            existing = best.get(key)
            if existing is None or SEVERITY_RANK[finding.severity] > SEVERITY_RANK[existing.severity]:
                best[key] = finding
        return sorted(
            best.values(),
            key=lambda item: (SEVERITY_RANK[item.severity], item.weight, item.confidence),
            reverse=True,
        )

    @staticmethod
    def _score(findings: list[Finding]) -> int:
        if not findings:
            return 0
        # Saturating aggregation: multiple independent signals increase risk without simple overflow.
        survival = 1.0
        for finding in findings:
            contribution = min(0.72, (finding.weight / 100) * finding.confidence)
            survival *= 1 - contribution
        score = 100 * (1 - survival)
        critical_bonus = 8 if any(f.severity == Severity.CRITICAL for f in findings) else 0
        diversity_bonus = min(10, max(0, len({f.category for f in findings}) - 1) * 2)
        return min(100, int(round(score + critical_bonus + diversity_bonus)))

    @staticmethod
    def _risk_level(score: int) -> Severity:
        if score >= 85:
            return Severity.CRITICAL
        if score >= 65:
            return Severity.HIGH
        if score >= 35:
            return Severity.MEDIUM
        if score >= 12:
            return Severity.LOW
        return Severity.INFO

    @staticmethod
    def _summary(score: int, level: Severity, findings: list[Finding]) -> str:
        if not findings:
            return "No known prompt-injection indicators were detected by the local scanner."
        categories = ", ".join(sorted({f.category.value.replace("_", " ") for f in findings}))
        return f"Risk {score}/100 ({level.value}). Detected: {categories}."
