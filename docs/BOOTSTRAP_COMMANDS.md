# Reviewer Agent setup commands

The repository is intentionally rooted at `/Users/jessipavia/reviewer` and
uses the existing `backend/` and `frontend/` directories. These are the commands
to run after the project files are merged; they do not regenerate or overwrite
the existing Next.js application.

## Toolchain

```bash
brew install node@22 uv terraform

node --version
npm --version
uv --version
docker --version
terraform version
aws --version
aws configure list
aws sts get-caller-identity
```

Python 3.12 is the Lambda deployment baseline. Local Python 3.13 is supported
by the package metadata. Node 22 is the web and build baseline.

## Install and verify dependencies

```bash
cd /Users/jessipavia/reviewer

uv sync --project backend --group dev
npm --prefix frontend install

make schema
make lint
make test
```

The frontend install adds Relay without replacing the pinned Next.js 16.2.10
version. Commit `backend/uv.lock`, the updated `frontend/package-lock.json`, and
generated Relay artifacts so builds remain reproducible.

## Run locally at zero cloud cost

```bash
cd /Users/jessipavia/reviewer
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. The GraphQL endpoint is
`http://localhost:8000/graphql`, health is `http://localhost:8000/health`, and
PostgreSQL is available on port `5432`.

For optional local model analysis, configure an OpenAI-compatible Ollama server
with `LLM_BASE_URL` and `LLM_MODEL`. Deterministic review remains functional
when all LLM variables are blank.

## Prepare AWS safely

```bash
cd /Users/jessipavia/reviewer/infra/terraform/aws/environments/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out foundation.tfplan
```

The default plan does not create Aurora or Lambda. Inspect the plan before
applying it, then follow `docs/AWS_DEPLOYMENT.md` for the two-stage deployment.
Do not store long-lived AWS keys in the repository or `.env` file.

The retained `infra/terraform/environments/dev` directory is a non-primary
Google Cloud baseline included to demonstrate direct alignment with the target
company stack.
