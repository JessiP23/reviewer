FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv sync --no-dev

FROM base AS development
RUN uv sync
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "reviewer.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "reviewer.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]

