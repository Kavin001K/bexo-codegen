#!/usr/bin/env bash
# Purge Cloudflare KV handle → profileId mappings (portfolio URLs).
# Works on Mac (inline IDs + token) or via SSH to bexo-n8n VM.
#
# Usage:
#   export CLOUDFLARE_TOKEN='your_token'   # Workers KV Edit, or Account read
#   bash scripts/purge-kv-handles.sh
#   bash scripts/purge-kv-handles.sh kavink kavin
#   bash scripts/purge-kv-handles.sh --ssh   # run on bexo-n8n VM
#
set -euo pipefail

ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-78466cfe7312b7a3121264e61d702129}"
NAMESPACE_ID="${CLOUDFLARE_KV_NAMESPACE_ID:-981034d3742e41dca6751cead23be616}"
PROJECT_ID="${PROJECT_ID:-bexo-prod}"
HANDLES=(kavink kavin)

if [[ "${1:-}" == "--ssh" ]]; then
  echo "Running KV purge on bexo-n8n VM..."
  gcloud compute ssh bexo-n8n --zone=us-central1-a --project="$PROJECT_ID" --command='
    set -e
    cd ~/bexo-n8n && set -a && source .env && set +a
    for h in kavink kavin; do
      code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
        "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/${CLOUDFLARE_KV_NAMESPACE_ID}/values/${h}" \
        -H "Authorization: Bearer ${CLOUDFLARE_TOKEN}")
      echo "DELETE ${h} -> HTTP ${code}"
    done
    echo "Remaining keys:"
    curl -s "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/storage/kv/namespaces/${CLOUDFLARE_KV_NAMESPACE_ID}/keys" \
      -H "Authorization: Bearer ${CLOUDFLARE_TOKEN}" | python3 -c "import json,sys; d=json.load(sys.stdin); print([k[\"name\"] for k in d.get(\"result\") or []])"
  '
  exit 0
fi

shift_handles() {
  if [[ $# -gt 0 ]]; then
    HANDLES=("$@")
  fi
}
shift_handles "$@"

if [[ -z "${CLOUDFLARE_TOKEN:-}" ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    CLOUDFLARE_TOKEN="$(gcloud secrets versions access latest --secret=cloudflare-token --project="$PROJECT_ID" 2>/dev/null || true)"
  fi
fi

if [[ -z "${CLOUDFLARE_TOKEN:-}" ]]; then
  echo "ERROR: Set CLOUDFLARE_TOKEN or run: bash scripts/purge-kv-handles.sh --ssh"
  echo "  Token needs Workers KV Storage Edit (or edit from dashboard)."
  exit 1
fi

BASE="https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/storage/kv/namespaces/${NAMESPACE_ID}"

echo "Account: $ACCOUNT_ID"
echo "KV namespace: $NAMESPACE_ID"
echo ""

LIST=$(curl -sf "${BASE}/keys?limit=1000" -H "Authorization: Bearer ${CLOUDFLARE_TOKEN}" || echo '{"success":false}')
if ! echo "$LIST" | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin).get('success') else 1)" 2>/dev/null; then
  echo "KV list failed (token invalid or wrong permissions)."
  echo "Try: bash scripts/purge-kv-handles.sh --ssh"
  echo "$LIST" | python3 -m json.tool 2>/dev/null || echo "$LIST"
  exit 1
fi

echo "Keys before:"
echo "$LIST" | python3 -c "import json,sys; d=json.load(sys.stdin); print(' ', d.get('result') or [])"

for h in "${HANDLES[@]}"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${BASE}/values/${h}" \
    -H "Authorization: Bearer ${CLOUDFLARE_TOKEN}")
  echo "DELETE ${h} -> HTTP ${code}"
done

echo ""
echo "Keys after:"
curl -sf "${BASE}/keys?limit=1000" -H "Authorization: Bearer ${CLOUDFLARE_TOKEN}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(' ', [k['name'] for k in d.get('result') or []])"
