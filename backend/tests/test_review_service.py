from reviewer.application import ReviewService
from reviewer.domain.models import ReviewStatus
from reviewer.infra import MemoryReviewRepository


async def test_processes_review_end_to_end() -> None:
    repository = MemoryReviewRepository()
    service = ReviewService(repository)
    content = b"Revenue,100000\nNet income,12000\n"

    queued = await service.enqueue("p-and-l.csv", "text/csv", content)
    await service.process(queued.id, content)
    completed = await service.get(queued.id)

    assert completed is not None
    assert completed.status == ReviewStatus.COMPLETED
    assert completed.diagnostics is not None
    assert completed.diagnostics.parser == "python-csv"
    assert {metric.key for metric in completed.metrics} >= {"revenue", "net_income", "net_margin"}
    assert completed.sha256


async def test_marks_unreadable_pdf_as_failed() -> None:
    repository = MemoryReviewRepository()
    service = ReviewService(repository)
    queued = await service.enqueue("broken.pdf", "application/pdf", b"not a pdf")
    await service.process(queued.id, b"not a pdf")
    failed = await service.get(queued.id)

    assert failed is not None
    assert failed.status == ReviewStatus.FAILED
    assert failed.error


async def test_approve_and_reject_review() -> None:
    repository = MemoryReviewRepository()
    service = ReviewService(repository)
    content = b"Revenue,100000\nNet income,12000\n"

    queued = await service.enqueue("p-and-l.csv", "text/csv", content)
    await service.process(queued.id, content)

    approved = await service.approve(queued.id, "looks good")
    assert approved is not None
    assert approved.status == ReviewStatus.COMPLETED
    assert approved.human_decision == "approved"
    assert approved.human_feedback == "looks good"

    rejected = await service.reject(queued.id, "missing cost of goods sold")
    assert rejected is not None
    assert rejected.status == ReviewStatus.REJECTED
    assert rejected.human_decision == "rejected"
    assert rejected.human_feedback == "missing cost of goods sold"

