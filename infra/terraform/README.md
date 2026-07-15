# Google Cloud alignment baseline

The checked-in environment is a safe bootstrap, not an invitation to create
billable resources blindly. With defaults, Terraform enables required APIs,
creates an Artifact Registry repository and service identities; Cloud Run
services are disabled until immutable image URIs are supplied.

Before setting `deploy_services = true`, add the production data plane:

1. private-IP Cloud SQL for PostgreSQL with PITR/backups;
2. Secret Manager values for `DATABASE_URL`, auth, and model credentials;
3. a Cloud Storage bucket with lifecycle/retention policy for source documents;
4. Cloud Tasks or Pub/Sub plus an idempotent worker and dead-letter handling;
5. authenticated ingress and tenant identity propagation;
6. API CORS origin and web `NEXT_PUBLIC_API_URL` at image build time;
7. budgets, log redaction, audit sinks, traces, SLOs, and alerts.

These are intentionally gated because Cloud SQL and always-on/OCR resources are
not free. The local Compose topology is the zero-cost development environment.
