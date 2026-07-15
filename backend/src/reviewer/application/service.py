from __future__ import annotations

import asyncio
import hashlib

from reviewer.analysis import RULE_VERSION, analyze
from reviewer.analysis.llm import FindingAnalyzer
from reviewer.application.ports import ReviewRepository
from reviewer.domain.models import ExtractionDiagnostic, Review, ReviewStatus, Severity
from reviewer.extraction import ExtractorRegistry


class ReviewService:
    def __init__(
        self,
        repository: ReviewRepository,
        extractors: ExtractorRegistry | None = None,
        model_analyzer: FindingAnalyzer | None = None,
    ) -> None:
        self._repository = repository
        self._extractors = extractors or ExtractorRegistry()
        self._model_analyzer = model_analyzer

    @property
    def supported_extensions(self) -> set[str]:
        return self._extractors.supported_extensions

    async def enqueue(self, filename: str, content_type: str, content: bytes) -> Review:
        review = Review(
            filename=filename,
            content_type=content_type,
            sha256=hashlib.sha256(content).hexdigest(),
            rule_version=RULE_VERSION,
        )
        return await self._repository.create(review)

    async def process(self, review_id: str, content: bytes) -> None:
        review = await self._repository.get(review_id)
        if review is None:
            return
        try:
            review.status = ReviewStatus.EXTRACTING
            review.touch()
            await self._repository.save(review)

            document = await asyncio.to_thread(self._extractors.extract, review.filename, content)
            character_count = sum(len(block.text) for block in document.blocks)
            review.diagnostics = ExtractionDiagnostic(
                parser=document.parser,
                blocks=len(document.blocks),
                characters=character_count,
                warnings=document.warnings,
                coverage=0 if not document.blocks else (0.8 if document.warnings else 1),
            )
            if not document.blocks:
                raise ValueError(
                    "No machine-readable content was extracted; OCR or a source export is required."
                )

            review.status = ReviewStatus.ANALYZING
            review.touch()
            await self._repository.save(review)

            review.metrics, review.findings = await asyncio.to_thread(analyze, document)
            if self._model_analyzer is not None:
                review.findings.extend(await self._model_analyzer.analyze(document))
            requires_review = bool(document.warnings) or any(
                finding.requires_human_review
                or finding.severity in {Severity.CRITICAL, Severity.HIGH}
                for finding in review.findings
            )
            review.status = (
                ReviewStatus.NEEDS_REVIEW if requires_review else ReviewStatus.COMPLETED
            )
            review.touch()
            await self._repository.save(review)
        except Exception as exc:
            review.status = ReviewStatus.FAILED
            review.error = str(exc)[:500]
            review.touch()
            await self._repository.save(review)

    async def get(self, review_id: str, tenant_id: str = "demo") -> Review | None:
        return await self._repository.get(review_id, tenant_id)

    async def fail(self, review_id: str, message: str) -> None:
        review = await self._repository.get(review_id)
        if review is None:
            return
        review.status = ReviewStatus.FAILED
        review.error = message[:500]
        review.touch()
        await self._repository.save(review)

    async def list(self, tenant_id: str = "demo", limit: int = 50) -> list[Review]:
        return await self._repository.list(tenant_id, limit)
