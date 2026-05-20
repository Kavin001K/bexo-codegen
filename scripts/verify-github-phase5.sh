#!/usr/bin/env bash
# Verify GitHub PAT + org before updating github-token in GCP.
# Usage:
#   export GITHUB_TOKEN=github_pat_xxxx
#   ./scripts/verify-github-phase5.sh
#   ./scripts/verify-github-phase5.sh bexo-sites

set -euo pipefail

ORG="${1:-bexo-sites}"
TOKEN="${GITHUB_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "Set GITHUB_TOKEN to your PAT, then re-run."
  exit 1
fi

api() {
  curl -sS -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

echo "== Token owner =="
api https://api.github.com/user | python3 -c "import json,sys; u=json.load(sys.stdin); print(u.get('login','?'), u.get('message',''))"

echo ""
echo "== Org: ${ORG} =="
STATUS=$(api -o /tmp/gh-org.json -w "%{http_code}" "https://api.github.com/orgs/${ORG}")
if [[ "$STATUS" == "200" ]]; then
  python3 -c "import json; o=json.load(open('/tmp/gh-org.json')); print('OK —', o['login'])"
elif [[ "$STATUS" == "404" ]]; then
  echo "NOT FOUND — create org at https://github.com/organizations/plan"
  echo "  (Or use GITHUB_ORG=auto until the org exists.)"
  exit 1
else
  cat /tmp/gh-org.json
  echo "HTTP ${STATUS}"
  exit 1
fi

echo ""
echo "== Can list org repos? =="
STATUS=$(api -o /tmp/gh-repos.json -w "%{http_code}" "https://api.github.com/orgs/${ORG}/repos?per_page=1")
if [[ "$STATUS" == "200" ]]; then
  echo "OK — token can read org repos"
else
  echo "FAIL HTTP ${STATUS} — token needs org repo access"
  cat /tmp/gh-repos.json | head -c 500
  exit 1
fi

echo ""
echo "== Fine-grained check: create repo permission =="
echo "If using classic PAT with 'repo' scope, you are likely fine."
echo "If using fine-grained PAT, ensure Administration + Contents on org ${ORG}."
echo ""
echo "All checks passed for org ${ORG}. Next:"
echo "  gcloud secrets versions add github-token --data-file=- --project=bexo-prod  # paste PAT"
echo "  # set GITHUB_ORG=bexo-sites in cloudbuild.yaml and redeploy"
