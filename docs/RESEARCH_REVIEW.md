# Review of the supplied technical research

The supplied report has the right north stars: rich document parsing,
evidence-linked outputs, deterministic financial checks, retrieval evaluation,
human review, observability, and a staged rollout. This repository keeps those
ideas while changing the starting topology.

## Decisions retained

- Docling is the leading high-fidelity parser candidate because it provides a
  unified representation across PDFs, Office files, images, CSV, and XBRL and
  has OCR/table pipeline controls.
- Financial answers must preserve source geometry/provenance and validate
  numeric claims.
- Dense retrieval alone is insufficient for amounts, dates, tickers, and exact
  accounting language; the search plan is hybrid lexical plus vector retrieval.
- Deterministic accounting rules, anomaly detection, and LLM analysis serve
  different purposes and should be evaluated separately.
- The system needs versioned evaluation sets, audit records, feedback, latency,
  and cost metrics before it can make product accuracy claims.

## Decisions changed for the MVP

| Supplied option | MVP decision | Reason |
| --- | --- | --- |
| Parser microservices | Extractor plug-ins in one Python service | Isolation without deployment overhead |
| Kafka / Kubernetes | In-process locally; S3/SQS/Lambda on AWS | Durable scale without an always-on cluster |
| Weaviate / Milvus / Qdrant / Chroma | PostgreSQL full-text + pgvector | One tenant model, backup, and query layer |
| TrOCR as a default | Docling OCR profile benchmarked against Tesseract | Accuracy must be measured by document class |
| LLM as core reasoning engine | Deterministic rules first; optional evidence-gated LLM | Critical financial checks must not be probabilistic |
| Provider “free tier” as architecture | Provider-independent OpenAI-compatible adapter | Prices, quotas, models, and data terms change |
| Universal microservice state machine | Explicit domain statuses and an SQS job boundary | Easier to audit without premature orchestration |

## Extraction ladder

1. Use native structure first: CSV/XLSX cells, DOCX paragraphs/tables, PDF text.
2. Detect empty/low-coverage pages and route them to the Docling OCR profile.
3. Compare totals and cross-foot tables; flag mismatches instead of guessing.
4. For low-confidence documents, run an alternative parser and compare results.
5. Require human confirmation for critical fields and unresolved disagreement.

This ladder can approach very high accuracy on supported document classes, but
it does not misrepresent arbitrary-document extraction as universally perfect.

## What “real time” means here

The user receives a review ID immediately. Local mode exposes server-sent
events; the static AWS client polls a narrow GraphQL status query. Parsing
remains asynchronous. The first meaningful metric is time to first grounded
finding, followed by full-review p50/p95; token streaming is not a substitute
for pipeline latency measurement.
