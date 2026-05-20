#!/usr/bin/env bash
# BEXO GCP foundation — run once with billing linked
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-bexo-prod}"
REGION="${REGION:-us-central1}"
BUCKET="${GCS_BUCKET:-bexo-portfolios}"

echo "==> Project: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

echo "==> Enabling APIs..."
gcloud services enable \
  compute.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  cloudtasks.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

echo "==> Artifact Registry..."
gcloud artifacts repositories describe bexo --location="$REGION" 2>/dev/null || \
  gcloud artifacts repositories create bexo \
    --repository-format=docker \
    --location="$REGION" \
    --description="BEXO container images"

echo "==> GCS bucket..."
if ! gsutil ls -b "gs://${BUCKET}" &>/dev/null; then
  gsutil mb -l "$REGION" "gs://${BUCKET}"
  gsutil uniformbucketlevelaccess set on "gs://${BUCKET}"
fi

echo "==> Service accounts..."
gcloud iam service-accounts describe "bexo-codegen@${PROJECT_ID}.iam.gserviceaccount.com" 2>/dev/null || \
  gcloud iam service-accounts create bexo-codegen --display-name="BEXO Codegen Cloud Run"

gcloud iam service-accounts describe "n8n-invoker@${PROJECT_ID}.iam.gserviceaccount.com" 2>/dev/null || \
  gcloud iam service-accounts create n8n-invoker --display-name="n8n Cloud Run invoker"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:bexo-codegen@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin" --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:bexo-codegen@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" --quiet

gcloud run services add-iam-policy-binding bexo-codegen \
  --region="$REGION" \
  --member="serviceAccount:n8n-invoker@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker" 2>/dev/null || echo "(Deploy Cloud Run first, then re-run for invoker binding)"

echo "==> Done. Create secrets manually:"
echo "  deepseek-api-key, kimi-api-key, openrouter-api-key (optional)"
echo "  github-token, cloudflare-token, cloudflare-zone-id"
echo "  supabase-service-key, supabase-url, n8n-callback-url, bexo-internal-secret"
