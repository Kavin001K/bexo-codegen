#!/usr/bin/env bash
# One-time: service account for n8n → GCS portfolio.md uploads
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-bexo-prod}"
SA_NAME="n8n-gcs"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_PATH="${1:-$HOME/bexo-n8n-gcs-key.json}"

gcloud config set project "$PROJECT_ID"

gcloud iam service-accounts describe "$SA_EMAIL" 2>/dev/null || \
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="n8n GCS portfolio uploads"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --quiet

gcloud iam service-accounts keys create "$KEY_PATH" \
  --iam-account="$SA_EMAIL"

chmod 600 "$KEY_PATH"

echo ""
echo "Done."
echo "  Service account: $SA_EMAIL"
echo "  Key file:        $KEY_PATH"
echo ""
echo "Next: n8n → Credentials → Google Cloud Storage → use this JSON"
echo "      See infra/n8n/GCS-UPLOAD-SETUP.md"
