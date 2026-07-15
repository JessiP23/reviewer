from typing import Protocol

from reviewer.domain.models import Review


class ReviewRepository(Protocol):
    async def create(self, review: Review) -> Review: ...

    async def get(self, review_id: str, tenant_id: str = "demo") -> Review | None: ...

    async def list(self, tenant_id: str = "demo", limit: int = 50) -> list[Review]: ...

    async def save(self, review: Review) -> Review: ...

