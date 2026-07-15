from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from reviewer.application import ReviewService
from reviewer.application.jobs import ReviewDispatcher
from reviewer.config import Settings
from reviewer.domain.models import ReviewStatus

router = APIRouter(prefix="/v1")


class ReviewAccepted(BaseModel):
    id: str
    status: ReviewStatus


class HumanReviewRequest(BaseModel):
    feedback: str | None = None


@router.post("/reviews", response_model=ReviewAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_review(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile,
) -> ReviewAccepted:
    settings: Settings = request.app.state.settings
    service: ReviewService = request.app.state.review_service
    filename = Path(file.filename or "upload").name
    extension = Path(filename).suffix.lower()
    if extension not in service.supported_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Use: {', '.join(sorted(service.supported_extensions))}",
        )
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the configured upload limit.")
    if not content:
        raise HTTPException(status_code=400, detail="File is empty.")
    review = await service.enqueue(
        filename, file.content_type or "application/octet-stream", content
    )
    dispatcher = cast(
        ReviewDispatcher | None,
        getattr(request.app.state, "review_dispatcher", None),
    )
    if dispatcher is None:
        background_tasks.add_task(service.process, review.id, content)
    else:
        try:
            await dispatcher.dispatch(review, content)
        except Exception as exc:
            await service.fail(review.id, "The review could not be queued.")
            raise HTTPException(status_code=503, detail="The review could not be queued.") from exc
    return ReviewAccepted(id=review.id, status=review.status)


@router.get("/reviews/{review_id}/events")
async def review_events(request: Request, review_id: str) -> StreamingResponse:
    service: ReviewService = request.app.state.review_service
    if await service.get(review_id) is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    async def stream() -> AsyncIterator[str]:
        previous: str | None = None
        while not await request.is_disconnected():
            review = await service.get(review_id)
            if review is None:
                return
            current = review.status.value
            if current != previous:
                payload = json.dumps({"id": review.id, "status": current})
                yield f"event: status\ndata: {payload}\n\n"
                previous = current
            if review.status in {
                ReviewStatus.COMPLETED,
                ReviewStatus.NEEDS_REVIEW,
                ReviewStatus.FAILED,
            }:
                return
            await asyncio.sleep(0.75)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/reviews/{review_id}/approve")
async def approve_review(
    request: Request,
    review_id: str,
    body: HumanReviewRequest | None = None,
) -> ReviewAccepted:
    service: ReviewService = request.app.state.review_service
    review = await service.approve(review_id, body.feedback if body else None)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return ReviewAccepted(id=review.id, status=review.status)


@router.post("/reviews/{review_id}/reject")
async def reject_review(
    request: Request,
    review_id: str,
    body: HumanReviewRequest | None = None,
) -> ReviewAccepted:
    service: ReviewService = request.app.state.review_service
    review = await service.reject(review_id, body.feedback if body else None)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return ReviewAccepted(id=review.id, status=review.status)
