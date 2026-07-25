from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityCategory(StrEnum):
    INSTRUCTION_OVERRIDE = "instruction_override"
    SYSTEM_PROMPT_EXFILTRATION = "system_prompt_exfiltration"
    DATA_EXFILTRATION = "data_exfiltration"
    TOOL_ABUSE = "tool_abuse"
    INDIRECT_INJECTION = "indirect_injection"
    OBFUSCATION = "obfuscation"
    ROLE_MANIPULATION = "role_manipulation"
    SOCIAL_ENGINEERING = "social_engineering"
    ENCODING_EVASION = "encoding_evasion"
    DELIMITER_ESCAPE = "delimiter_escape"


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    category: SecurityCategory
    severity: Severity
    title: str
    description: str
    evidence: str
    start: int | None = None
    end: int | None = None
    confidence: float = Field(ge=0, le=1)
    weight: int = Field(ge=0, le=100)
    remediation: str


class SecurityScanRequest(BaseModel):
    text: str = Field(min_length=1)
    context: str | None = None
    decode_obfuscation: bool = True
    include_hardened_prompt: bool = True


class SecurityScanResult(BaseModel):
    scan_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=utc_now)
    risk_score: int = Field(ge=0, le=100)
    risk_level: Severity
    summary: str
    findings: list[Finding]
    normalized_text: str
    decoded_candidates: list[str] = Field(default_factory=list)
    hardened_prompt: str | None = None
    recommended_controls: list[str] = Field(default_factory=list)
    metrics: dict[str, int | float | str] = Field(default_factory=dict)


class MutationRequest(BaseModel):
    text: str = Field(min_length=1)
    count: int = Field(default=8, ge=1, le=30)


class MutationVariant(BaseModel):
    technique: str
    payload: str
    purpose: str


class MutationResult(BaseModel):
    source: str
    variants: list[MutationVariant]


class SourceRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:10])
    title: str
    url: HttpUrl | str
    domain: str
    snippet: str = ""
    accessed_at: datetime = Field(default_factory=utc_now)
    trust_score: float = Field(default=0.5, ge=0, le=1)


class ResearchQuestion(BaseModel):
    question: str = Field(min_length=5)
    depth: str = Field(default="standard", pattern="^(quick|standard|deep)$")
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    max_sources: int = Field(default=10, ge=3, le=30)
    output_style: str = Field(default="analytical", pattern="^(analytical|executive|academic)$")
    require_recent_sources: bool = True

    @field_validator("allowed_domains", "blocked_domains")
    @classmethod
    def clean_domains(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            domain = item.strip().lower().removeprefix("https://").removeprefix("http://")
            domain = domain.split("/")[0]
            if domain and domain not in cleaned:
                cleaned.append(domain)
        return cleaned[:100]


class ResearchPlan(BaseModel):
    objective: str
    subquestions: list[str] = Field(min_length=2, max_length=8)
    search_queries: list[str] = Field(min_length=2, max_length=12)
    evaluation_criteria: list[str] = Field(min_length=2, max_length=8)
    risk_notes: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:10])
    statement: str
    source_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    status: str = Field(pattern="^(supported|mixed|unsupported|uncertain)$")
    notes: str = ""


class AgentTrace(BaseModel):
    agent: str
    status: str
    started_at: datetime
    finished_at: datetime
    input_summary: str
    output_summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchResult(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    created_at: datetime = Field(default_factory=utc_now)
    mode: str
    question: str
    plan: ResearchPlan
    executive_summary: str
    report_markdown: str
    sources: list[SourceRecord]
    claims: list[Claim]
    limitations: list[str]
    trace: list[AgentTrace]
    quality_score: int = Field(ge=0, le=100)
    metrics: dict[str, int | float | str] = Field(default_factory=dict)

