#!/usr/bin/env sh
set -eu

AWS_REGION="${AWS_REGION:-us-east-2}"
IMAGE_TAG="${IMAGE_TAG:-$(date -u +%Y%m%d%H%M%S)}"
TERRAFORM_DIR="${TERRAFORM_DIR:-infra/terraform/aws/environments/dev}"
REPOSITORY_URL="${REPOSITORY_URL:-$(terraform -chdir="$TERRAFORM_DIR" output -raw ecr_repository_url)}"
BACKEND_DIR="${BACKEND_DIR:-backend}"

aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin "${REPOSITORY_URL%%/*}"

docker buildx build \
  --platform linux/arm64 \
  --file "$BACKEND_DIR/Dockerfile.lambda" \
  --tag "$REPOSITORY_URL:$IMAGE_TAG" \
  --push \
  "$BACKEND_DIR"

aws ecr describe-images \
  --region "$AWS_REGION" \
  --repository-name "${REPOSITORY_URL#*/}" \
  --image-ids "imageTag=$IMAGE_TAG" \
  --query 'imageDetails[0].imageDigest' \
  --output text
