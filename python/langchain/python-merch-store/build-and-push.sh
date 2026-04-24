#!/usr/bin/env bash
set -euo pipefail

ORG="salaboy"
IMAGE="python-merch-store"
TAG="${1:-langchain-otel}"

FULL_IMAGE="${ORG}/${IMAGE}:${TAG}"

echo "Building and pushing multi-arch image: ${FULL_IMAGE}"

# Create (or reuse) a buildx builder that supports multi-arch
BUILDER="multiarch-builder"
if ! docker buildx inspect "${BUILDER}" >/dev/null 2>&1; then
  echo "Creating buildx builder: ${BUILDER}"
  docker buildx create --name "${BUILDER}" --driver docker-container --use
else
  docker buildx use "${BUILDER}"
fi

# Build for linux/amd64 and linux/arm64, tag, and push in one step
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag "${FULL_IMAGE}" \
  --push \
  .

echo "Done. Pushed: ${FULL_IMAGE}"
