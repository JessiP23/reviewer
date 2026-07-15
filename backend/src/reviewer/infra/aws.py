from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import boto3

from reviewer.domain.models import Review


class RdsDataReviewRepository:
    """PostgreSQL repository over the Aurora RDS Data API."""

    def __init__(
        self,
        cluster_arn: str,
        secret_arn: str,
        database: str,
        region: str,
    ) -> None:
        self._cluster_arn = cluster_arn
        self._secret_arn = secret_arn
        self._database = database
        self._client: Any = boto3.client("rds-data", region_name=region)

    def _execute(
        self,
        sql: str,
        parameters: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._client.execute_statement(
                resourceArn=self._cluster_arn,
                secretArn=self._secret_arn,
                database=self._database,
                sql=sql,
                parameters=parameters or [],
            ),
        )

    async def initialize(self) -> None:
        await asyncio.to_thread(
            self._execute,
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id uuid PRIMARY KEY,
                tenant_id text NOT NULL,
                status text NOT NULL,
                filename text NOT NULL,
                payload jsonb NOT NULL,
                created_at timestamptz NOT NULL,
                updated_at timestamptz NOT NULL
            )
            """,
        )
        await asyncio.to_thread(
            self._execute,
            """
            CREATE INDEX IF NOT EXISTS reviews_tenant_created_idx
                ON reviews (tenant_id, created_at DESC)
            """,
        )

    @staticmethod
    def _string(name: str, value: str) -> dict[str, Any]:
        return {"name": name, "value": {"stringValue": value}}

    @staticmethod
    def _long(name: str, value: int) -> dict[str, Any]:
        return {"name": name, "value": {"longValue": value}}

    @classmethod
    def _review_parameters(cls, review: Review) -> list[dict[str, Any]]:
        return [
            cls._string("id", review.id),
            cls._string("tenant_id", review.tenant_id),
            cls._string("status", review.status.value),
            cls._string("filename", review.filename),
            cls._string("payload", json.dumps(review.model_dump(mode="json"))),
            cls._string("created_at", review.created_at.isoformat()),
            cls._string("updated_at", review.updated_at.isoformat()),
        ]

    async def create(self, review: Review) -> Review:
        await asyncio.to_thread(
            self._execute,
            """
            INSERT INTO reviews
                (id, tenant_id, status, filename, payload, created_at, updated_at)
            VALUES
                (CAST(:id AS uuid), :tenant_id, :status, :filename,
                 CAST(:payload AS jsonb), CAST(:created_at AS timestamptz),
                 CAST(:updated_at AS timestamptz))
            """,
            self._review_parameters(review),
        )
        return review

    async def get(self, review_id: str, tenant_id: str = "demo") -> Review | None:
        result = await asyncio.to_thread(
            self._execute,
            """
            SELECT payload::text AS payload
            FROM reviews
            WHERE id = CAST(:id AS uuid) AND tenant_id = :tenant_id
            LIMIT 1
            """,
            [self._string("id", review_id), self._string("tenant_id", tenant_id)],
        )
        records = result.get("records", [])
        if not records:
            return None
        return Review.model_validate_json(records[0][0]["stringValue"])

    async def list(self, tenant_id: str = "demo", limit: int = 50) -> list[Review]:
        result = await asyncio.to_thread(
            self._execute,
            """
            SELECT payload::text AS payload
            FROM reviews
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC
            LIMIT :result_limit
            """,
            [self._string("tenant_id", tenant_id), self._long("result_limit", limit)],
        )
        records = result.get("records", [])
        return [Review.model_validate_json(record[0]["stringValue"]) for record in records]

    async def save(self, review: Review) -> Review:
        parameters = [
            self._string("id", review.id),
            self._string("tenant_id", review.tenant_id),
            self._string("status", review.status.value),
            self._string("filename", review.filename),
            self._string("payload", json.dumps(review.model_dump(mode="json"))),
            self._string("updated_at", review.updated_at.isoformat()),
        ]
        await asyncio.to_thread(
            self._execute,
            """
            UPDATE reviews
            SET status = :status,
                filename = :filename,
                payload = CAST(:payload AS jsonb),
                updated_at = CAST(:updated_at AS timestamptz)
            WHERE id = CAST(:id AS uuid) AND tenant_id = :tenant_id
            """,
            parameters,
        )
        return review


class AwsReviewDispatcher:
    def __init__(self, bucket: str, queue_url: str, region: str) -> None:
        self._bucket = bucket
        self._queue_url = queue_url
        self._s3: Any = boto3.client("s3", region_name=region)
        self._sqs: Any = boto3.client("sqs", region_name=region)

    def _key(self, review: Review) -> str:
        safe_name = Path(review.filename).name.replace(" ", "_")
        return f"{review.tenant_id}/{review.id}/{safe_name}"

    async def dispatch(self, review: Review, content: bytes) -> None:
        key = self._key(review)
        await asyncio.to_thread(
            self._s3.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=content,
            ContentType=review.content_type,
            ServerSideEncryption="AES256",
            Metadata={"review-id": review.id, "sha256": review.sha256},
        )
        message = json.dumps(
            {
                "review_id": review.id,
                "tenant_id": review.tenant_id,
                "bucket": self._bucket,
                "key": key,
            }
        )
        await asyncio.to_thread(
            self._sqs.send_message,
            QueueUrl=self._queue_url,
            MessageBody=message,
            MessageGroupId=review.tenant_id,
            MessageDeduplicationId=review.id,
        )

    async def read(self, bucket: str, key: str) -> bytes:
        response = await asyncio.to_thread(
            self._s3.get_object,
            Bucket=bucket,
            Key=key,
        )
        return cast(bytes, response["Body"].read())
