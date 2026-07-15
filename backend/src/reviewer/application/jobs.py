from typing import Protocol

from reviewer.domain.models import Review


class ReviewDispatcher(Protocol):
    async def dispatch(self, review: Review, content: bytes) -> None: ...

