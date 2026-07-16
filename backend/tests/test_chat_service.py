import pytest

from reviewer.application.chat_service import ReviewChatService
from reviewer.domain.models import (
    Evidence,
    Finding,
    Metric,
    Review,
    ReviewStatus,
    Severity,
)


def _sample_review() -> Review:
    return Review(
        id="r1",
        filename="financials.csv",
        content_type="text/csv",
        sha256="abc123",
        status=ReviewStatus.COMPLETED,
        metrics=[
            Metric(
                key="revenue",
                label="Revenue",
                value=100000.0,
                unit="currency",
                confidence=1.0,
                status="verified",
                raw="Revenue,100000",
                evidence=[
                    Evidence(
                        text="Revenue,100000",
                        source="financials.csv",
                        cell_range="A2",
                    )
                ],
            ),
            Metric(
                key="current_ratio",
                label="Current ratio",
                value=2.5,
                unit="ratio",
                confidence=0.98,
                status="verified",
            ),
            Metric(
                key="debt_to_equity",
                label="Debt-to-equity ratio",
                value=0.5,
                unit="ratio",
                confidence=0.92,
                status="inferred",
            ),
        ],
        findings=[
            Finding(
                code="LOW_CURRENT_RATIO",
                title="Current ratio is below threshold",
                category="liquidity",
                severity=Severity.HIGH,
                explanation="Current ratio of 0.8 is below the 1.0 threshold.",
                recommendation="Improve working capital.",
                confidence=0.95,
                requires_human_review=True,
                evidence=[Evidence(text="Current assets 80000", source="financials.csv")],
            ),
        ],
    )


@pytest.fixture
def chat() -> ReviewChatService:
    return ReviewChatService()


@pytest.mark.asyncio
async def test_summary_answer(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "Give me a summary")
    assert "financials.csv" in reply
    assert "3 metrics" in reply
    assert "1 finding" in reply


@pytest.mark.asyncio
async def test_flags_answer(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "What is flagged?")
    assert "Current ratio" in reply or "LOW_CURRENT_RATIO" in reply


@pytest.mark.asyncio
async def test_metrics_list(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "Show all metrics")
    assert "Revenue" in reply
    assert "Current ratio" in reply


@pytest.mark.asyncio
async def test_specific_metric(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "What is revenue?")
    assert "$100,000.00" in reply
    assert "confidence 100%" in reply


@pytest.mark.asyncio
async def test_metric_evidence(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "Evidence for revenue")
    assert "A2" in reply
    assert "100000" in reply


@pytest.mark.asyncio
async def test_confidence(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "What is low confidence?")
    assert "Debt-to-equity" in reply


@pytest.mark.asyncio
async def test_finding_by_title(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "current ratio finding")
    assert "below threshold" in reply


@pytest.mark.asyncio
async def test_unknown_question(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "What is the weather?")
    assert "review context" in reply


@pytest.mark.asyncio
async def test_health_liquidity(chat: ReviewChatService) -> None:
    review = _sample_review()
    reply = await chat.answer(review, "How is liquidity?")
    assert "Current ratio" in reply
