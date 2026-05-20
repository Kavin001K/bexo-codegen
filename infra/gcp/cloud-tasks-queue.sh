#!/usr/bin/env bash
# Optional: Cloud Tasks queue for retries between n8n and Cloud Run
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-bexo-prod}"
REGION="${REGION:-us-central1}"
QUEUE="${QUEUE:-bexo-build-queue}"

gcloud tasks queues create "$QUEUE" \
  --location="$REGION" \
  --max-attempts=5 \
  --min-backoff=10s \
  --max-backoff=300s \
  2>/dev/null || gcloud tasks queues update "$QUEUE" --location="$REGION"

echo "Queue $QUEUE ready in $REGION"
