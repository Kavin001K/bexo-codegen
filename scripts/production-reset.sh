#!/usr/bin/env bash
# Wipe generated portfolio sites + build artifacts for a clean production launch.
# Keeps: user profiles/projects in Supabase, buckets, Cloud Run, n8n workflows.
#
# Usage:
#   ./scripts/production-reset.sh              # dry-run (default)
#   ./scripts/production-reset.sh --execute    # actually delete
#   ./scripts/production-reset.sh --execute --github --kv
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ID="${PROJECT_ID:-bexo-prod}"
PUBLIC_BUCKET="${GCS_PUBLIC_BUCKET:-bexo-sites-public}"
PRIVATE_BUCKET="${GCS_BUCKET:-bexo-portfolios}"
GITHUB_ORG="${GITHUB_ORG:-bexo-sites}"
CF_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-78466cfe7312b7a3121264e61d702129}"
CF_KV_NS="${CLOUDFLARE_KV_NAMESPACE_ID:-981034d3742e41dca6751cead23be616}"

EXECUTE=false
DO_GITHUB=false
DO_KV=false

for arg in "$@"; do
  case "$arg" in
    --execute) EXECUTE=true ;;
    --github) DO_GITHUB=true ;;
    --kv) DO_KV=true ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
  esac
done

run() {
  if $EXECUTE; then
    echo ">> $*"
    "$@"
  else
    echo "[dry-run] $*"
  fi
}

echo "=== BEXO production reset ==="
echo "Project: $PROJECT_ID"
echo "Mode: $($EXECUTE && echo EXECUTE || echo dry-run)"
echo ""

gcloud config set project "$PROJECT_ID" >/dev/null

gcs_delete_prefixes() {
  local bucket="$1"
  local prefixes
  prefixes="$(gcloud storage ls "gs://${bucket}/" 2>/dev/null | sed 's|/$||' || true)"
  if [[ -z "$prefixes" ]]; then
    echo "  (empty)"
    return
  fi
  while IFS= read -r p; do
    [[ -n "$p" ]] || continue
    run gcloud storage rm -r "${p}/**" 2>/dev/null || run gcloud storage rm -r "${p}/"
  done <<< "$prefixes"
}

echo "--- GCS: $PUBLIC_BUCKET (live sites) ---"
gcs_delete_prefixes "$PUBLIC_BUCKET"

echo "--- GCS: $PRIVATE_BUCKET (portfolio.md audit) ---"
gcs_delete_prefixes "$PRIVATE_BUCKET"

echo "--- Local codegen workspace ---"
if [[ -d "$ROOT/workspace" ]]; then
  for d in "$ROOT/workspace"/*; do
    [[ -e "$d" ]] || continue
    run rm -rf "$d"
  done
else
  echo "  (no workspace dir)"
fi

echo "--- Supabase: site_builds + site_analytics ---"
if command -v gcloud >/dev/null 2>&1; then
  SUPABASE_URL="$(gcloud secrets versions access latest --secret=supabase-url --project="$PROJECT_ID" 2>/dev/null || true)"
  SUPABASE_KEY="$(gcloud secrets versions access latest --secret=supabase-service-key --project="$PROJECT_ID" 2>/dev/null || true)"
  if [[ -n "$SUPABASE_URL" && -n "$SUPABASE_KEY" ]]; then
    if $EXECUTE; then
      curl -sf -X DELETE "${SUPABASE_URL}/rest/v1/site_builds?id=neq.00000000-0000-0000-0000-000000000000" \
        -H "apikey: ${SUPABASE_KEY}" -H "Authorization: Bearer ${SUPABASE_KEY}" \
        -H "Prefer: return=minimal" && echo "  site_builds cleared"
      curl -sf -X DELETE "${SUPABASE_URL}/rest/v1/site_analytics?id=neq.00000000-0000-0000-0000-000000000000" \
        -H "apikey: ${SUPABASE_KEY}" -H "Authorization: Bearer ${SUPABASE_KEY}" \
        -H "Prefer: return=minimal" 2>/dev/null && echo "  site_analytics cleared" || echo "  site_analytics skip (table may be empty)"
    else
      echo "[dry-run] DELETE all site_builds + site_analytics via Supabase REST"
    fi
  else
    echo "  skip: supabase secrets not available"
  fi
fi

if $DO_KV; then
  echo "--- Cloudflare KV (handle → profileId) ---"
  CF_TOKEN="$(gcloud secrets versions access latest --secret=cloudflare-token --project="$PROJECT_ID" 2>/dev/null || true)"
  if [[ -z "$CF_TOKEN" ]]; then
    echo "  skip: cloudflare-token secret missing"
  else
    KEYS_JSON=$(curl -sf \
      "https://api.cloudflare.com/client/v4/accounts/${CF_ACCOUNT_ID}/storage/kv/namespaces/${CF_KV_NS}/keys?limit=1000" \
      -H "Authorization: Bearer ${CF_TOKEN}" || echo '{"success":false}')
    if $EXECUTE; then
      python3 - <<'PY' "$KEYS_JSON" "$CF_ACCOUNT_ID" "$CF_KV_NS" "$CF_TOKEN"
import json, sys, urllib.request
data = json.loads(sys.argv[1])
account, ns, token = sys.argv[2], sys.argv[3], sys.argv[4]
if not data.get("success"):
    print("  KV list failed:", data)
    sys.exit(0)
keys = [k["name"] for k in data.get("result", [])]
for name in keys:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces/{ns}/values/{name}"
    req = urllib.request.Request(url, method="DELETE", headers={"Authorization": f"Bearer {token}"})
    try:
        urllib.request.urlopen(req)
        print(f"  deleted KV key: {name}")
    except Exception as e:
        print(f"  failed {name}: {e}")
if not keys:
    print("  (no KV keys)")
PY
    else
      echo "$KEYS_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print('  keys:', [k['name'] for k in d.get('result',[])])" 2>/dev/null || echo "  [dry-run] list KV keys"
    fi
  fi
else
  echo "--- Cloudflare KV: skipped (pass --kv with --execute) ---"
fi

if $DO_GITHUB; then
  echo "--- GitHub org: $GITHUB_ORG (portfolio-* repos) ---"
  if ! command -v gh >/dev/null 2>&1; then
    echo "  skip: gh CLI not installed"
  else
    REPOS="$(gh api "orgs/${GITHUB_ORG}/repos" --paginate -q '.[].name' 2>/dev/null | grep '^portfolio-' || true)"
    if [[ -z "$REPOS" ]]; then
      echo "  (no portfolio-* repos)"
    else
      while IFS= read -r repo; do
        [[ -n "$repo" ]] || continue
        if $EXECUTE; then
          run gh repo delete "${GITHUB_ORG}/${repo}" --yes
        else
          echo "[dry-run] gh repo delete ${GITHUB_ORG}/${repo} --yes"
        fi
      done <<< "$REPOS"
    fi
  fi
else
  echo "--- GitHub: skipped (pass --github with --execute) ---"
fi

echo ""
if ! $EXECUTE; then
  echo "Dry-run complete. Run:  ./scripts/production-reset.sh --execute --kv --github"
else
  echo "Reset complete. Verify:"
  echo "  gcloud storage ls gs://${PUBLIC_BUCKET}/"
  echo "  curl -s \$(gcloud run services describe bexo-codegen --region=us-central1 --format='value(status.url)')/health | jq .skills.missing"
fi
