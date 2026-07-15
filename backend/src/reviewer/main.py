from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from reviewer.analysis.llm import OpenAICompatibleAnalyzer
from reviewer.api.graphql import graphql_router
from reviewer.api.rest import router as rest_router
from reviewer.application import ReviewService
from reviewer.config import get_settings
from reviewer.infra.runtime import create_runtime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    runtime = await create_runtime(settings)
    app.state.settings = settings
    app.state.runtime = runtime
    app.state.review_dispatcher = runtime.dispatcher
    model_analyzer = (
        OpenAICompatibleAnalyzer(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
        )
        if settings.llm_base_url and settings.llm_model
        else None
    )
    app.state.review_service = ReviewService(
        runtime.repository, model_analyzer=model_analyzer
    )
    yield
    await runtime.close()


app = FastAPI(
    title="Reviewer Agent API",
    version="0.1.0",
    description="Evidence-first financial document analysis for SMB workflows.",
    lifespan=lifespan,
)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(rest_router)
app.include_router(graphql_router, prefix="/graphql")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "reviewer"}
