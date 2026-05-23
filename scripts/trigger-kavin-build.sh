#!/usr/bin/env bash
# Trigger portfolio build for handle kavin (profile 82070c0b-...).
# Requires: gcloud auth + access to bexo-internal-secret, or set BEXO_INTERNAL_SECRET.

set -euo pipefail

PROFILE_ID="${PROFILE_ID:-82070c0b-204b-4063-ba2d-15b245c27106}"
HANDLE="${HANDLE:-kavin}"
BUILD_ID="${BUILD_ID:-$(uuidgen | tr '[:upper:]' '[:lower:]')}"
CODEGEN_URL="${CODEGEN_URL:-https://bexo-codegen-901109516440.us-central1.run.app}"

if [[ -z "${BEXO_INTERNAL_SECRET:-}" ]]; then
  BEXO_INTERNAL_SECRET="$(gcloud secrets versions access latest --secret=bexo-internal-secret --project=bexo-prod)"
fi

BASE="${CODEGEN_URL%/}"
BASE="${BASE%/build}"
URL="${BASE}/build"

echo "POST ${URL}"
echo "profileId=${PROFILE_ID} buildId=${BUILD_ID} handle=${HANDLE}"
echo "(Build may take 5–10 minutes; watch Cloud Run logs)"

curl -sS -X POST "${URL}" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Internal-Secret: ${BEXO_INTERNAL_SECRET}" \
  -d "{\"profileId\":\"${PROFILE_ID}\",\"buildId\":\"${BUILD_ID}\",\"handle\":\"${HANDLE}\"}" \
  --max-time 660

echo ""
echo "Verify GCS:"
echo "curl -sI \"https://storage.googleapis.com/bexo-sites-public/${PROFILE_ID}/site/index.html\" | head -1"
echo "curl -sI \"https://${HANDLE}.mybexo.com\" | head -1"
