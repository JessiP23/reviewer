from __future__ import annotations

import io
from typing import Any

import pytest

from reviewer.domain.models import Review
from reviewer.infra.aws import AwsReviewDispatcher, RdsDataReviewRepository


class FakeRdsData:
    def __init__(self) -> None:
        self.payload: str | None = None
        self.statements: list[str] = []

    def execute_statement(self, **request: Any) -> dict[str, Any]:
        sql = str(request["sql"])
        self.statements.append(sql)
        parameters = {
            item["name"]: item["value"] for item in request.get("parameters", [])
        }
        if "INSERT INTO reviews" in sql:
            self.payload = parameters["payload"]["stringValue"]
        if "SELECT payload::text" in sql and self.payload is not None:
            return {"records": [[{"stringValue": self.payload}]]}
        return {}


@pytest.mark.asyncio
async def test_rds_data_repository_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeRdsData()
    monkeypatch.setattr("reviewer.infra.aws.boto3.client", lambda *args, **kwargs: client)
    repository = RdsDataReviewRepository("cluster", "secret", "reviewer", "us-east-2")
    review = Review(
        filename="financials.csv",
        content_type="text/csv",
        sha256="abc123",
    )

    await repository.initialize()
    await repository.create(review)
    restored = await repository.get(review.id)

    assert restored == review
    assert any("CREATE TABLE IF NOT EXISTS reviews" in sql for sql in client.statements)


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **request: Any) -> None:
        self.objects[(request["Bucket"], request["Key"])] = request["Body"]

    def get_object(self, **request: Any) -> dict[str, Any]:
        content = self.objects[(request["Bucket"], request["Key"])]
        return {"Body": io.BytesIO(content)}


class FakeSqs:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send_message(self, **request: Any) -> None:
        self.messages.append(request)


@pytest.mark.asyncio
async def test_aws_dispatcher_stores_then_queues(monkeypatch: pytest.MonkeyPatch) -> None:
    s3 = FakeS3()
    sqs = FakeSqs()

    def client(service: str, **kwargs: Any) -> Any:
        del kwargs
        return s3 if service == "s3" else sqs

    monkeypatch.setattr("reviewer.infra.aws.boto3.client", client)
    dispatcher = AwsReviewDispatcher("documents", "queue-url", "us-east-2")
    review = Review(
        filename="financial report.csv",
        content_type="text/csv",
        sha256="abc123",
    )

    await dispatcher.dispatch(review, b"Revenue,100")
    key = f"demo/{review.id}/financial_report.csv"

    assert await dispatcher.read("documents", key) == b"Revenue,100"
    assert sqs.messages[0]["MessageDeduplicationId"] == review.id
    assert sqs.messages[0]["MessageGroupId"] == "demo"
