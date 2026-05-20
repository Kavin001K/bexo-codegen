#!/usr/bin/env bash
# Run on bexo-n8n VM: cd ~/bexo-n8n && bash verify-cloudflare-env.sh
set -euo pipefail

ENV_FILE="${1:-.env}"
COMPOSE_FILE="${2:-docker-compose.micro.yml}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

echo "==> Token length in $ENV_FILE (file on disk):"
python3 - <<'PY' "$ENV_FILE"
import os, sys
from pathlib import Path
p = Path(sys.argv[1])
for line in p.read_text().splitlines():
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, _, v = s.partition("=")
    if k.strip() != "CLOUDFLARE_TOKEN":
        continue
    v = v.strip().strip('"').strip("'")
    print(f"  chars={len(v)}  prefix={v[:4]!r}  suffix={v[-4:]!r}" if v else "  EMPTY")
    break
else:
    print("  CLOUDFLARE_TOKEN not found in file")
PY

echo "==> Token length inside running container:"
docker exec bexo-n8n sh -c 't="$CLOUDFLARE_TOKEN"; echo "  chars=${#t}  prefix=${t%"${t#????}"}  (redacted)"' 2>/dev/null || echo "  container bexo-n8n not running"

echo "==> Cloudflare KV write test (same API n8n uses):"
TOKEN=$(docker exec bexo-n8n printenv CLOUDFLARE_TOKEN)
ACCOUNT=$(docker exec bexo-n8n printenv CLOUDFLARE_ACCOUNT_ID)
NS=$(docker exec bexo-n8n printenv CLOUDFLARE_KV_NAMESPACE_ID)
if [[ -z "$TOKEN" || -z "$ACCOUNT" || -z "$NS" ]]; then
  echo "  FAIL: CLOUDFLARE_TOKEN, CLOUDFLARE_ACCOUNT_ID, or CLOUDFLARE_KV_NAMESPACE_ID empty"
  exit 1
fi
KV_OUT=$(curl -sS -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT}/storage/kv/namespaces/${NS}/values/_bexo_env_test" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: text/plain" \
  --data "ok")
echo "$KV_OUT" | python3 -m json.tool
if ! echo "$KV_OUT" | grep -q '"success":true'; then
  echo "  FAIL: KV PUT did not succeed"
  exit 1
fi
echo "  OK: token can write KV (Workflow B will work)"
echo "==> Optional: /user/tokens/verify (often false-negative without API Tokens Read permission):"
curl -sS "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool || true

echo "==> Compose resolved CLOUDFLARE_TOKEN length (must match file after fix):"
docker compose -f "$COMPOSE_FILE" config 2>/dev/null | python3 - <<'PY' || true
import sys, re
text = sys.stdin.read()
m = re.search(r"CLOUDFLARE_TOKEN:\s*(\S*)", text)
print(f"  chars={len(m.group(1))}" if m and m.group(1) else "  (not in compose environment — OK if using env_file only)")
PY
