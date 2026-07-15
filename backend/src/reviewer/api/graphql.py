from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from reviewer.application import ReviewService
from reviewer.domain.models import Evidence, ExtractionDiagnostic, Finding, Metric, Review


@strawberry.type
class EvidenceType:
    text: str
    source: str
    page: int | None
    sheet: str | None
    cell_range: str | None

    @classmethod
    def from_domain(cls, evidence: Evidence) -> EvidenceType:
        return cls(
            text=evidence.text,
            source=evidence.source,
            page=evidence.page,
            sheet=evidence.sheet,
            cell_range=evidence.cell_range,
        )


@strawberry.type
class FindingType:
    code: str
    title: str
    category: str
    severity: str
    explanation: str
    recommendation: str
    confidence: float
    evidence: list[EvidenceType]
    requires_human_review: bool

    @classmethod
    def from_domain(cls, finding: Finding) -> FindingType:
        return cls(
            code=finding.code,
            title=finding.title,
            category=finding.category,
            severity=finding.severity.value,
            explanation=finding.explanation,
            recommendation=finding.recommendation,
            confidence=finding.confidence,
            evidence=[EvidenceType.from_domain(item) for item in finding.evidence],
            requires_human_review=finding.requires_human_review,
        )


@strawberry.type
class MetricType:
    key: str
    label: str
    value: float
    unit: str
    confidence: float
    evidence: list[EvidenceType]

    @classmethod
    def from_domain(cls, metric: Metric) -> MetricType:
        return cls(
            key=metric.key,
            label=metric.label,
            value=metric.value,
            unit=metric.unit,
            confidence=metric.confidence,
            evidence=[EvidenceType.from_domain(item) for item in metric.evidence],
        )


@strawberry.type
class DiagnosticType:
    parser: str
    blocks: int
    characters: int
    warnings: list[str]
    coverage: float

    @classmethod
    def from_domain(cls, diagnostic: ExtractionDiagnostic) -> DiagnosticType:
        return cls(
            parser=diagnostic.parser,
            blocks=diagnostic.blocks,
            characters=diagnostic.characters,
            warnings=diagnostic.warnings,
            coverage=diagnostic.coverage,
        )


@strawberry.type
class ReviewType:
    id: strawberry.ID
    filename: str
    status: str
    findings: list[FindingType]
    metrics: list[MetricType]
    diagnostics: DiagnosticType | None
    error: str | None
    rule_version: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, review: Review) -> ReviewType:
        return cls(
            id=strawberry.ID(review.id),
            filename=review.filename,
            status=review.status.value,
            findings=[FindingType.from_domain(finding) for finding in review.findings],
            metrics=[MetricType.from_domain(metric) for metric in review.metrics],
            diagnostics=(
                None
                if review.diagnostics is None
                else DiagnosticType.from_domain(review.diagnostics)
            ),
            error=review.error,
            rule_version=review.rule_version,
            created_at=review.created_at,
            updated_at=review.updated_at,
        )


def _service(info: Info[Any, Any]) -> ReviewService:
    return cast(ReviewService, info.context["request"].app.state.review_service)


@strawberry.type
class Query:
    @strawberry.field
    async def review(self, info: Info[Any, Any], id: strawberry.ID) -> ReviewType | None:
        review = await _service(info).get(str(id))
        return None if review is None else ReviewType.from_domain(review)

    @strawberry.field
    async def reviews(self, info: Info[Any, Any], first: int = 20) -> list[ReviewType]:
        reviews = await _service(info).list(limit=min(max(first, 1), 100))
        return [ReviewType.from_domain(review) for review in reviews]


schema = strawberry.Schema(query=Query)
graphql_router = GraphQLRouter(schema)
