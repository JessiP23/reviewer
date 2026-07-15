# AWS deployment runbook

## Architecture

```text
Browser
  -> CloudFront -> private S3 static Next.js export
  -> API Gateway HTTP API -> FastAPI Lambda
                              -> RDS Data API -> Aurora PostgreSQL Serverless v2
                              -> S3 document object -> SQS FIFO
                                                       -> review worker Lambda
                                                       -> RDS Data API
```

This topology has no NAT gateway and no always-running application container.
Aurora can pause at 0 ACU after ten idle minutes. Storage, requests, CloudFront,
S3, SQS, Lambda, and Aurora storage still have usage charges; “scale to zero” is
not the same as “guaranteed free.”

The frontend is a static export because AWS Amplify's documented managed SSR
support currently stops at Next.js 15 while this project uses Next.js 16. The
dashboard does not require SSR and polls GraphQL for job state, so S3/CloudFront
is simpler and cheaper.

## Prerequisites

```bash
brew install terraform
aws --version
aws configure list
aws sts get-caller-identity
docker buildx version
```

Use short-lived AWS IAM Identity Center credentials when possible. Do not place
access keys in `.env`, Terraform variables, or GitHub secrets when OIDC is
available.

## 1. Create the low-cost foundation

```bash
cd infra/terraform/aws/environments/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out foundation.tfplan
terraform apply foundation.tfplan
cd ../../../..
```

The default flags leave Aurora and Lambda disabled. This first apply creates the
private frontend/document buckets, CloudFront distribution, SQS queues, and ECR
repository. Review the plan and AWS pricing before applying it.

## 2. Build and push the Lambda image

```bash
./scripts/build-and-push-lambda.sh
```

The last line is the image digest. Combine it with the ECR repository output:

```text
ACCOUNT.dkr.ecr.REGION.amazonaws.com/reviewer-dev@sha256:DIGEST
```

## 3. Enable the database and compute

Update `terraform.tfvars`:

```hcl
enable_database = true
deploy_compute  = true
lambda_image_uri = "ACCOUNT.dkr.ecr.REGION.amazonaws.com/reviewer-dev@sha256:DIGEST"
```

Then:

```bash
cd infra/terraform/aws/environments/dev
terraform plan -out application.tfplan
terraform apply application.tfplan
terraform output
cd ../../../..
```

This creates billable Aurora Serverless v2 capacity, although supported Aurora
PostgreSQL versions can pause to 0 ACU while idle. The first request after pause
has database resume latency. Keep `protect_database = false` only for disposable
development; enable protection and final snapshots before real customer data.

## 4. Publish the static frontend

```bash
./scripts/deploy-frontend-aws.sh
```

Open the `frontend_url` Terraform output, upload `examples/demo-financials.csv`,
and verify that status moves from `queued` to `completed` or `needs review`.

## 5. End-to-end smoke checks

```bash
API_URL="$(terraform -chdir=infra/terraform/aws/environments/dev output -raw api_url)"
curl --fail "$API_URL/health"
API_URL="$API_URL" ./scripts/smoke.sh
aws sqs get-queue-attributes \
  --queue-url "$(terraform -chdir=infra/terraform/aws/environments/dev output -raw review_queue_url)" \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

The browser should show evidence-linked findings after the worker finishes. In
CloudWatch, confirm the API and worker functions have no errors. Confirm that
the dead-letter queue is empty.

## Production gates

- Add OIDC authentication and derive tenant ID from verified claims.
- Replace direct API uploads with presigned multipart S3 uploads for files over
  the Lambda/API Gateway payload ceiling.
- Add AWS WAF, malware scanning, KMS customer-managed keys if required, and
  immutable audit export.
- Add Terraform remote state locking, GitHub Actions OIDC, budgets, alarms, and
  log redaction.
- Set database protection/final snapshots, backup retention, and restore drills.
- Load-test Aurora resume latency, Lambda memory, SQS visibility timeout, and
  parser throughput with representative statements.
- Use provisioned concurrency only when latency measurements justify its cost.

