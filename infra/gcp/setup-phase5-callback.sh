#!/usr/bin/env bash
# Set n8n build-done callback URL in Secret Manager (Cloud Run reads this).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-bexo-prod}"
CALLBACK_URL="${1:-https://n8n.mybexo.com/webhook/bexo-build-done}"

gcloud config set project "$PROJECT_ID"

if gcloud secrets describe n8n-callback-url --project="$PROJECT_ID" &>/dev/null; then
  echo -n "$CALLBACK_URL" | gcloud secrets versions add n8n-callback-url --data-file=-
else
  echo -n "$CALLBACK_URL" | gcloud secrets create n8n-callback-url --data-file=-
fi

echo "Set n8n-callback-url → $CALLBACK_URL"
echo "Redeploy Cloud Run so the new secret version is picked up:"
echo "  gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID ."
