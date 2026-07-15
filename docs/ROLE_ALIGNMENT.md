# Brillian role alignment

This project is intentionally a concise demonstration of the responsibilities
in the supplied Senior Software Engineer (AI Products) description.

| Role expectation | Evidence in this repository |
| --- | --- |
| Python production systems | Typed domain/application/adapter boundaries, tests, Ruff, mypy |
| Agentic financial workflows | Explicit review state machine and safe, versioned analysis tools |
| Data retrieval/transformation | Multi-format evidence model and normalized financial metrics |
| LLM/RAG readiness | Evidence schema, confidence, pgvector path, provider-independent boundary |
| Evaluation | Deterministic fixtures, accuracy policy, planned labeled regression corpus |
| APIs and data pipelines | REST upload, GraphQL reads/polling, S3/SQS asynchronous processing |
| SQL/data modeling | Tenant-scoped PostgreSQL record model and JSON evidence payload |
| Full product surface | Next.js/TypeScript dashboard with Relay code generation |
| Terraform/cloud systems | Deployable AWS serverless path plus retained Google Cloud baseline |
| Written technical strategy | Architecture, safety, roadmap, and bootstrap docs |

## Interview narrative

The project starts with a customer problem: an SMB owner or advisor needs to
know whether uploaded statements are internally consistent and what deserves
attention. The system returns results quickly, but treats financial data as an
accuracy-sensitive probabilistic domain. Every risk is source-linked; critical
numeric checks are deterministic; ambiguous cases are escalated.

The architecture resists two common early-stage mistakes: an expensive fleet of
microservices before product fit, and an LLM-only reviewer whose claims cannot
be audited. One Python service and PostgreSQL are enough for the first users,
while the extractor, job-runner, policy-pack, search, and model boundaries can
scale independently when measurements justify it.

## Scope that should be discussed honestly

- The current rule set is a demonstration, not accounting or investment advice.
- Industry benchmarking needs licensed/verified comparison data and NAICS-aware
  thresholds; generic thresholds are screening signals only.
- OCR and complex table accuracy require a labeled corpus and a Docling/OCR
  evaluation before production claims.
- “100% accuracy” is replaced with measured recall/precision, numeric
  reconciliation, evidence coverage, and mandatory human review gates.
