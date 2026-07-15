from __future__ import annotations

import asyncio
import json
from typing import Any

from reviewer.analysis.llm import OpenAICompatibleAnalyzer
from reviewer.application import ReviewService
from reviewer.config import get_settings
from reviewer.infra.aws import AwsReviewDispatcher
from reviewer.infra.runtime import create_runtime


async def _handle_batch(event: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    settings = get_settings()
    runtime = await create_runtime(settings)
    model_analyzer = (
        OpenAICompatibleAnalyzer(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
        )
        if settings.llm_base_url and settings.llm_model
        else None
    )
    service = ReviewService(runtime.repository, model_analyzer=model_analyzer)
    dispatcher = runtime.dispatcher
    if not isinstance(dispatcher, AwsReviewDispatcher):
        await runtime.close()
        raise RuntimeError("The Lambda worker requires JOB_BACKEND=sqs.")

    failures: list[dict[str, str]] = []
    try:
        for record in event.get("Records", []):
            message_id = str(record.get("messageId", "unknown"))
            try:
                message = json.loads(record["body"])
                content = await dispatcher.read(message["bucket"], message["key"])
                await service.process(message["review_id"], content)
            except Exception:
                failures.append({"itemIdentifier": message_id})
    finally:
        await runtime.close()
    return {"batchItemFailures": failures}


def handler(event: dict[str, Any], context: object) -> dict[str, list[dict[str, str]]]:
    del context
    return asyncio.run(_handle_batch(event))

