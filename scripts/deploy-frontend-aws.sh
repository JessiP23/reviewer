#!/usr/bin/env sh
set -eu

TERRAFORM_DIR="${TERRAFORM_DIR:-infra/terraform/aws/environments/dev}"
API_URL="${API_URL:-$(terraform -chdir="$TERRAFORM_DIR" output -raw api_url)}"
FRONTEND_BUCKET="${FRONTEND_BUCKET:-$(terraform -chdir="$TERRAFORM_DIR" output -raw frontend_bucket)}"
DISTRIBUTION_ID="${DISTRIBUTION_ID:-$(terraform -chdir="$TERRAFORM_DIR" output -raw cloudfront_distribution_id)}"
FRONTEND_DIR="${FRONTEND_DIR:-frontend}"

NEXT_PUBLIC_API_URL="$API_URL" npm --prefix "$FRONTEND_DIR" run build
aws s3 sync "$FRONTEND_DIR/out" "s3://$FRONTEND_BUCKET" --delete
aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths '/*'
