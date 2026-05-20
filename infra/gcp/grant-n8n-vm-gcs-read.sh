#!/usr/bin/env bash
# Let the n8n VM default compute SA read portfolio files (debug with gsutil on VM).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-bexo-prod}"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting storage.objectViewer on gs://bexo-portfolios to $COMPUTE_SA"
gcloud storage buckets add-iam-policy-binding gs://bexo-portfolios \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/storage.objectViewer" \
  --project="$PROJECT_ID"

echo "Done. On VM: gsutil cat gs://bexo-portfolios/PROFILE_ID/portfolio.md | head"
