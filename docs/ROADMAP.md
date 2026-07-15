# Delivery roadmap

## Implemented vertical slice

- PDF, XLSX, CSV, DOCX, Markdown, JSON, and text ingestion
- evidence-aware extraction
- balance-sheet and gross-profit reconciliation
- profitability, liquidity, leverage, going-concern, control, and PII signals
- PostgreSQL persistence
- REST upload, local SSE, cloud-safe GraphQL polling
- Next.js + Relay dashboard
- local containers, AWS S3/SQS/Lambda/Aurora adapters, and Terraform baselines

## Next: production pilot

- OIDC-derived tenant identity and authorization on every API operation
- presigned multipart upload flow for larger source documents
- OCR worker with Tesseract/PaddleOCR fallback and page-image provenance
- malware scanning and password-protected-file workflow
- Alembic migrations and PostgreSQL row-level security
- OpenTelemetry traces, CloudWatch SLO dashboards, budgets, and audit events

## Next: measured intelligence

- labeled evaluation corpus and regression harness
- policy-pack SDK with tenant-specific thresholds
- table and layout extraction benchmark (Docling/PyMuPDF comparison)
- optional schema-constrained LLM adapter (local Ollama first)
- reviewer feedback loop with immutable before/after decisions
- model and rule version registry, drift reports, and canary rollout
