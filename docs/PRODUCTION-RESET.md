# Production reset (clean slate for live launch)

Clears **generated** portfolio artifacts. Does **not** delete Supabase user profiles, projects, skills, or infra (Cloud Run, n8n, buckets).

## What gets cleared

| Layer | Cleared |
|-------|---------|
| **GCS** `bexo-sites-public/{profileId}/site/` | Live HTML, `_next/`, `data.json` |
| **GCS** `bexo-portfolios/{profileId}/` | Audit `portfolio.md` copies |
| **Supabase** `site_builds` | All build rows |
| **Supabase** `site_analytics` | View/event rows |
| **Cloudflare KV** | `handle` → `profileId` mappings |
| **GitHub** `bexo-sites/portfolio-*` | Optional codegen mirror repos |
| **Local** `bexo-codegen/workspace/` | Per-build workspaces |

## One-command reset (Mac)

Use the **full repo path** (do not `cd bexo-codegen` if you are already inside it):

```bash
cd "/Users/kavin/Documents/GitHub/Bexo Production/bexo-codegen"
bash scripts/production-reset.sh              # dry-run
bash scripts/production-reset.sh --execute --kv --github
bash scripts/purge-kv-handles.sh --ssh        # KV only, via VM token
```

## Manual steps if script partial-fails

### Cloudflare KV

`~/bexo-n8n/.env` exists **only on the GCP VM**, not on your Mac. Empty env vars caused the bad URL (`/accounts/storage/kv/...`).

**Option A — SSH (recommended):**

```bash
cd "/Users/kavin/Documents/GitHub/Bexo Production/bexo-codegen"
bash scripts/purge-kv-handles.sh --ssh
```

**Option B — Mac with a valid API token:**

```bash
export CLOUDFLARE_ACCOUNT_ID=78466cfe7312b7a3121264e61d702129
export CLOUDFLARE_KV_NAMESPACE_ID=981034d3742e41dca6751cead23be616
export CLOUDFLARE_TOKEN='paste_from_cloudflare_dashboard_or_VM_env'
bash scripts/purge-kv-handles.sh kavink kavin
```

**Option C — Dashboard:** Workers → KV → namespace `981034d3742e41dca6751cead23be616` → delete keys `kavink`, `kavin`.

Update GCP Secret Manager `cloudflare-token` if the Mac/gcloud token keeps returning `Authentication error`.

After purge, `https://{handle}.mybexo.com` returns 404 until the next successful build.

### GitHub repos (if `gh` lacks `delete_repo` or wrong account)

Device login must use the GitHub user that is **admin on `bexo-sites`** (not `BEXO-DEV` if that account lacks org access).

```bash
gh auth logout
gh auth login   # choose GitHub.com, HTTPS, login as org owner
gh auth refresh -h github.com -s delete_repo
gh repo delete bexo-sites/portfolio-kavink --yes
gh repo delete bexo-sites/portfolio-kavin --yes
```

Or delete in browser: https://github.com/bexo-sites/portfolio-kavink → Settings → Delete repository.

## Verify clean state

```bash
gcloud storage ls gs://bexo-sites-public/
gcloud storage ls gs://bexo-portfolios/

# Supabase (should be empty)
# site_builds count = 0

curl -sI https://kavink.mybexo.com | head -3   # expect 404 after KV cleared

# Production codegen still healthy
CODEGEN_URL=$(gcloud run services describe bexo-codegen --region=us-central1 --project=bexo-prod --format='value(status.url)')
curl -s "$CODEGEN_URL/health" | jq '{engine, llm, skills: .skills.missing}'
```

## After reset — first real user build

1. User completes profile ≥90% in BEXO app.
2. App → n8n → Cloud Run Claude build.
3. Workflow B writes KV + `site_builds` = `done`.
4. Site live at `https://{handle}.mybexo.com`.

No VM `claude` session required for production traffic.
