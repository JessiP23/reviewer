# Architecture

## Goals

The system is optimized for an SMB starting at zero infrastructure cost while
keeping boundaries that can scale independently. The initial release favors
explainability and operational simplicity over an oversized microservice fleet.

```text
Browser
  -> Next.js web (Relay) -> GraphQL query/poll + multipart upload
                            -> Python review API
                                 -> extractor registry
                                 -> financial metric normalization
                                 -> deterministic accounting rules
                                 -> optional evidence-gated LLM tool
                                 -> review orchestration
                                 -> PostgreSQL

Local: Docker Compose
AWS: CloudFront/S3 + API Gateway/Lambda + SQS + Aurora PostgreSQL Serverless v2
```

## Repository boundaries

```text
frontend/                    Next.js UI and Relay client
backend/                     Python API, extraction, analysis, persistence
packages/graphql/            versioned schema contract shared by UI and API
infra/terraform/aws/         primary AWS deployment
infra/terraform/environments retained Google Cloud role-alignment baseline
docs/                        decisions, accuracy model, bootstrap, roadmap
```

Inside the Python service, dependencies point inward:

- `domain`: review records and findings; no framework imports
- `extraction`: PDF, spreadsheet, CSV, DOCX, and text extraction behind a registry
- `analysis`: normalized financial metrics and versioned risk rules
- `application`: review workflow and ports
- `infra`: local SQLAlchemy and AWS Data API/S3/SQS implementations
- `api`: REST ingestion, SSE progress, and GraphQL adapters

## Why this stack fits Brillian's Senior Software Engineer (AI Products) role

| Supplied company technology | Project evidence |
| --- | --- |
| Next.js | App Router dashboard, upload workflow, and live progress UI |
| GraphQL / Relay | Strawberry schema, Relay compiler, typed queries |
| Python | Typed extraction, applied financial analysis, and agent-ready service |
| Node.js | Next.js runtime and frontend toolchain |
| PostgreSQL | Async SQLAlchemy repository and JSONB evidence |
| Google Cloud | Retained Cloud Run-oriented Terraform baseline for direct role alignment |
| Elixir / Phoenix | Sensible later option for a dedicated event gateway |
| INTERCAL | Acknowledged as cultural texture, not a production dependency |

The product surface mirrors Brillian's public focus on business valuation,
profitability, cash flow, KPI benchmarking, and ranked business-health risks.
The first release therefore emphasizes financial evidence and deterministic
checks before generalized chat.

## Technology selection

- **Lightweight default parser:** PyMuPDF, openpyxl, python-docx, and stdlib CSV.
  These start quickly and run on an ordinary laptop.
- **High-fidelity profile:** Docling is an optional dependency group for scanned
  pages, layout, reading order, and tables. Keeping it behind the extractor port
  prevents model downloads from slowing the API image or CI.
- **Search:** PostgreSQL full-text search plus pgvector when question-answering
  is added. A separate vector database is premature for an SMB MVP and would
  duplicate tenancy, backup, and operations.
- **Agent orchestration:** a typed state machine in the application layer;
  tool calls, policy, and evidence are explicit. A framework can be added only
  if it preserves these contracts.
- **LLM providers:** an OpenAI-compatible adapter can target a local Ollama
  model or a hosted provider. It is optional, never receives unredacted data by
  default, and cannot override critical deterministic findings.

The model adapter fails open: if the provider is unavailable or emits invalid
JSON, deterministic results still complete. Proposed model findings are capped
at 85% confidence, always require human review, must quote source evidence
verbatim, and cannot introduce a number absent from that quote.

## Local-to-cloud evolution

1. **Local/free:** Docker Compose, PostgreSQL/pgvector, in-process jobs, local disk only
   during an upload.
2. **First customers on AWS:** static UI through CloudFront, API Gateway/FastAPI
   Lambda, private S3, SQS FIFO, and Aurora Serverless v2 through the Data API.
3. **Growing load:** presigned multipart uploads, separate CPU/GPU OCR workers,
   tenant quotas, and measured Lambda concurrency controls.
4. **Regulated workloads:** private networking, customer-managed KMS keys, immutable audit export,
   regional residency, policy-specific evaluation suites.

The application layer exposes ports for persistence and execution, so local
in-process work and cloud SQS work share extraction and rule code.

## Real-time behavior

Uploads return a review ID immediately. Locally, the API exposes SSE; the
static AWS dashboard polls a small GraphQL status query every 1.5 seconds and
refetches Relay data on changes. Polling works consistently through API Gateway
and Lambda without an always-running socket service. If bidirectional,
high-fan-out events become necessary, a Phoenix gateway is a justified next
component.

## Data and tenancy

Every record has a tenant ID even though the demo uses `demo`. Production auth
must derive that ID from a verified identity token, never from a request body.
PostgreSQL row-level security is the recommended second enforcement layer.
Local mode does not persist original document bytes. AWS mode keeps encrypted
source objects in a private S3 bucket with lifecycle deletion; production
retention must be configurable per tenant.
