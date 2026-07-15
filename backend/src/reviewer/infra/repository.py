from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from reviewer.domain.models import Review


class Base(DeclarativeBase):
    pass


class ReviewRecord(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    @classmethod
    def from_domain(cls, review: Review) -> ReviewRecord:
        return cls(
            id=review.id,
            tenant_id=review.tenant_id,
            status=review.status.value,
            filename=review.filename,
            payload=review.model_dump(mode="json"),
            created_at=review.created_at,
            updated_at=review.updated_at,
        )

    def update_from(self, review: Review) -> None:
        self.status = review.status.value
        self.filename = review.filename
        self.payload = review.model_dump(mode="json")
        self.updated_at = review.updated_at

    def to_domain(self) -> Review:
        return Review.model_validate(self.payload)


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url, pool_pre_ping=True)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialize(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()


class SqlReviewRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def create(self, review: Review) -> Review:
        async with self._database.sessions() as session:
            session.add(ReviewRecord.from_domain(review))
            await session.commit()
        return review

    async def get(self, review_id: str, tenant_id: str = "demo") -> Review | None:
        async with self._database.sessions() as session:
            record = await session.scalar(
                select(ReviewRecord).where(
                    ReviewRecord.id == review_id,
                    ReviewRecord.tenant_id == tenant_id,
                )
            )
            return None if record is None else record.to_domain()

    async def list(self, tenant_id: str = "demo", limit: int = 50) -> list[Review]:
        async with self._database.sessions() as session:
            records = (
                await session.scalars(
                    select(ReviewRecord)
                    .where(ReviewRecord.tenant_id == tenant_id)
                    .order_by(ReviewRecord.created_at.desc())
                    .limit(limit)
                )
            ).all()
            return [record.to_domain() for record in records]

    async def save(self, review: Review) -> Review:
        async with self._database.sessions() as session:
            record = await session.get(ReviewRecord, review.id)
            if record is None:
                session.add(ReviewRecord.from_domain(review))
            else:
                record.update_from(review)
            await session.commit()
        return review


class MemoryReviewRepository:
    def __init__(self) -> None:
        self._reviews: dict[str, Review] = {}

    async def create(self, review: Review) -> Review:
        self._reviews[review.id] = review.model_copy(deep=True)
        return review

    async def get(self, review_id: str, tenant_id: str = "demo") -> Review | None:
        review = self._reviews.get(review_id)
        if review is None or review.tenant_id != tenant_id:
            return None
        return review.model_copy(deep=True)

    async def list(self, tenant_id: str = "demo", limit: int = 50) -> list[Review]:
        reviews = [review for review in self._reviews.values() if review.tenant_id == tenant_id]
        return [review.model_copy(deep=True) for review in reviews[-limit:][::-1]]

    async def save(self, review: Review) -> Review:
        self._reviews[review.id] = review.model_copy(deep=True)
        return review
