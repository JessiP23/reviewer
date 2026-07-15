# Verification record

## Completed in this workspace

- All Python source and tests pass Python bytecode compilation.
- The example CSV completed the extraction and deterministic analysis core:
  13 evidence rows, 14 base/derived metrics, and 6 expected findings.
- The numeric normalizer passed currency suffix, accounting-parentheses,
  thousands-suffix, and negative-number cases.
- The model-output gate accepted a verbatim 12% claim, rejected an invented 40%
  claim, required human review, and capped model confidence at 85%.
- PII evidence masks a detected SSN before it is persisted or displayed.
- The smoke shell script passes syntax validation.

## Environment-limited checks

This Codex sandbox could not reach npm (`ENOTFOUND registry.npmjs.org`), its
bundled `uv` build crashed while reading restricted macOS network configuration,
the Docker socket was inaccessible, and Terraform was not installed. Therefore
dependency lockfiles, Relay-generated artifacts, the full test suite, container
build, visual browser QA, and `terraform validate` could not be produced here.

Run these on a normal networked development machine before the first commit:

```bash
cd /Users/jessipavia/reviewer
npm --prefix frontend install
cd backend && uv sync && cd ..
make schema
make lint
make test
docker compose up --build
./scripts/smoke.sh
cd infra/terraform/aws/environments/dev
terraform init -backend=false
terraform fmt -check -recursive
terraform validate
```

Commit the generated `frontend/package-lock.json`, `backend/uv.lock`, and Relay
artifacts after those checks pass. Do not enable the Terraform data plane until
the security and cost gates in `infra/terraform/README.md` are complete.
