from __future__ import annotations

from dataclasses import dataclass

from reviewer.application.jobs import ReviewDispatcher
from reviewer.application.ports import ReviewRepository
from reviewer.config import Settings
from reviewer.infra.aws import AwsReviewDispatcher, RdsDataReviewRepository
from reviewer.infra.repository import Database, SqlReviewRepository


@dataclass
class Runtime:
    repository: ReviewRepository
    dispatcher: ReviewDispatcher | None = None
    database: Database | None = None

    async def close(self) -> None:
        if self.database is not None:
            await self.database.close()


def _require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"{name} is required for the selected AWS backend.")
    return value


async def create_runtime(settings: Settings) -> Runtime:
    if settings.repository_backend == "rds-data":
        repository = RdsDataReviewRepository(
            cluster_arn=_require(settings.rds_cluster_arn, "RDS_CLUSTER_ARN"),
            secret_arn=_require(settings.rds_secret_arn, "RDS_SECRET_ARN"),
            database=settings.rds_database,
            region=settings.aws_region,
        )
        await repository.initialize()
        runtime = Runtime(repository=repository)
    else:
        database = Database(settings.database_url)
        await database.initialize()
        runtime = Runtime(
            repository=SqlReviewRepository(database),
            database=database,
        )

    if settings.job_backend == "sqs":
        runtime.dispatcher = AwsReviewDispatcher(
            bucket=_require(settings.document_bucket, "DOCUMENT_BUCKET"),
            queue_url=_require(settings.review_queue_url, "REVIEW_QUEUE_URL"),
            region=settings.aws_region,
        )
    return runtime

