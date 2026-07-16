from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class ReviewStatus(StrEnum):
    QUEUED = "queued"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    FAILED = "failed"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(BaseModel):
    text: str
    source: str
    page: int | None = None
    sheet: str | None = None
    cell_range: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


class Finding(BaseModel):
    code: str
    title: str
    category: str
    severity: Severity
    explanation: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)
    requires_human_review: bool = False


class Metric(BaseModel):
    key: str
    label: str
    value: float
    unit: str = "number"
    period: str | None = None
    confidence: float = Field(default=1, ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)
    raw: str | None = None
    status: str | None = None


class ExtractionDiagnostic(BaseModel):
    parser: str
    blocks: int
    characters: int
    warnings: list[str] = Field(default_factory=list)
    coverage: float = Field(default=1, ge=0, le=1)


class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "demo"
    filename: str
    content_type: str
    sha256: str
    status: ReviewStatus = ReviewStatus.QUEUED
    findings: list[Finding] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    diagnostics: ExtractionDiagnostic | None = None
    error: str | None = None
    human_feedback: str | None = None
    human_decision: str | None = None
    rule_version: str = "financial-core/1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)

