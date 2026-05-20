#!/usr/bin/env bash
# Public read bucket for generated portfolio HTML only (Worker fetches from here).
# GCP does not allow IAM conditions on allUsers — see docs/PORTFOLIO-HOSTING-PLAN.md.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-bexo-prod}"
REGION="${REGION:-US}"
PUBLIC_BUCKET="${GCS_PUBLIC_BUCKET:-bexo-sites-public}"

gcloud config set project "$PROJECT_ID"

if ! gcloud storage buckets describe "gs://${PUBLIC_BUCKET}" &>/dev/null; then
  echo "==> Creating gs://${PUBLIC_BUCKET}..."
  gcloud storage buckets create "gs://${PUBLIC_BUCKET}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
else
  echo "==> Bucket gs://${PUBLIC_BUCKET} already exists"
fi

echo "==> Granting public read (entire bucket — only portfolio HTML is written here)..."
gcloud storage buckets add-iam-policy-binding "gs://${PUBLIC_BUCKET}" \
  --member=allUsers \
  --role=roles/storage.objectViewer

echo "==> Done."
echo "    Worker / codegen use: gs://${PUBLIC_BUCKET}/{profileId}/site/index.html"
echo "    portfolio.md stays private in gs://bexo-portfolios/"
