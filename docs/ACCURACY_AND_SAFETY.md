# Accuracy, safety, and review policy

## The honest guarantee

“100% accurate extraction” is not a defensible promise for arbitrary customer
documents. Scans, damaged PDFs, handwriting, unusual encodings, nested tables,
and ambiguous language all create irreducible uncertainty. The product instead
guarantees that it never silently presents an uncertain result as certain.

## Assurance pipeline

1. Validate file type, size, and parser limits.
2. Extract blocks with page/paragraph provenance and stable character offsets.
3. Record extraction diagnostics and coverage.
4. Run deterministic, versioned rules that return exact evidence spans.
5. Deduplicate findings and calculate confidence.
6. Mark low-confidence, high-severity, and parse-warning cases for human review.
7. Keep rule version, timestamps, and evidence with every result.

An optional local or hosted language model may summarize or propose findings,
but it must emit a validated schema, cite retrieved evidence, and never be the
only detector for critical controls.

## Quality metrics

- extraction character/word error rate on a labeled corpus
- field-level precision, recall, and F1 by document type
- risk-rule false-positive and false-negative rates
- evidence-span correctness
- percentage routed to human review
- p50/p95 upload-to-result latency
- drift by parser, rule version, tenant, and document template

Claims about accuracy should be made only against a versioned evaluation set
with confidence intervals. A useful launch gate is policy-specific, for example
`>= 0.98 recall for critical clauses on the approved contract corpus`, rather
than a universal 100% claim.

## Threat controls

- enforce allowlisted MIME types and byte limits
- parse in resource-limited workers; add malware scanning before production
- treat document text as untrusted data, never as instructions
- escape evidence in the UI and use parameterized database access
- redact secrets and document text from logs
- encrypt transport and storage; use short retention by default
- require explicit user confirmation before external actions

