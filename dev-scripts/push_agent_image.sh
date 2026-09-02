#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-us-east-1}"
REPO_URL=$(cd infra/environments/dev && terraform output -raw agentcore_ecr_repository_url)
TAG="${1:-latest}"

echo "Repository: $REPO_URL"
echo "Tag: $TAG"

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${REPO_URL%%/*}"

docker buildx build \
  --platform linux/arm64 \
  -t "${REPO_URL}:${TAG}" \
  --push \
  .

echo "Pushed ${REPO_URL}:${TAG}"
