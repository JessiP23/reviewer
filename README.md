# Reviewer Agent

Reviewer Agent (product UI: **LedgerLens**) is a local-first financial document
review system for small and midsize businesses. It extracts evidence from PDF,
scanned PDFs, images, XLSX, CSV, DOCX, Markdown, JSON, and text files;
calculates business-health metrics; applies auditable accounting and risk rules;
surfaces findings in a Next.js + Relay dashboard; and exposes an agent
orchestration UI with human-in-the-loop approval.

The project deliberately matches the supplied target stack:

- Next.js, TypeScript, GraphQL, and Relay for the frontend
- Python, FastAPI, Strawberry, SQLAlchemy, and Pydantic for review services
- PostgreSQL for durable records
- containers locally; AWS Lambda, S3, SQS, CloudFront, Aurora, and Terraform for the primary scale path
- a retained Google Cloud baseline to demonstrate direct alignment with Brillian's current platform

Elixir/Phoenix is documented as a future high-concurrency event-gateway option,
not included as resume-padding. INTERCAL is intentionally excluded from the
production path.

## Start

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:3000. Upload a supported document and watch its findings
arrive. API health is at http://localhost:8000/health and GraphiQL is at
http://localhost:8000/graphql. The agent orchestration UI is at
http://localhost:3000/agent.

The dashboard requires the API; do not run `npm --prefix frontend run dev` by
itself unless the Python API is already running and `NEXT_PUBLIC_API_URL` points
to it. To start services in the background, use `docker compose up --build -d`;
confirm both services with `curl --fail http://localhost:8000/health` and stop
them with `docker compose down`.

For setup without containers, architecture decisions, accuracy guarantees, and
the delivery plan, see [docs/BOOTSTRAP_COMMANDS.md](docs/BOOTSTRAP_COMMANDS.md),
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md),
[docs/ACCURACY_AND_SAFETY.md](docs/ACCURACY_AND_SAFETY.md), and
[docs/END_TO_END_ORCHESTRATION.md](docs/END_TO_END_ORCHESTRATION.md). The supplied
technology report is assessed in [docs/RESEARCH_REVIEW.md](docs/RESEARCH_REVIEW.md),
and the interview mapping is in [docs/ROLE_ALIGNMENT.md](docs/ROLE_ALIGNMENT.md).
See [docs/VERIFICATION.md](docs/VERIFICATION.md) for the exact checks completed
in this workspace and the commands that require an unrestricted machine.
The AWS architecture and two-stage deployment are documented in
[docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md).

## Common commands

```bash
make lint
make test
make schema
make build
```

## Current scope

The first vertical slice covers document ingestion, evidence-preserving
extraction, deterministic financial checks, persisted review results, GraphQL
reads, and near-real-time status. The AWS path includes durable SQS jobs, a
dead-letter queue, private source storage, and independently scaling workers.
Authentication, tenant billing, OCR/Docling, embeddings/RAG, and a production
evaluation corpus remain explicit follow-on modules rather than hidden
assumptions.
