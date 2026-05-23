# Build Claude Code portfolios — step-by-step (start here)

You said **secrets, webhooks, and n8n already work**. This guide only covers switching the **build engine** from Python HTML to **Claude Code + Next.js**, then verifying end-to-end.

**Time:** ~2–4 hours first time (includes one full build wait of 5–8 min).

---

## Before you start

Have these ready:

| Item | Where to get it |
|------|-----------------|
| `gcloud` logged in | `gcloud auth login` |
| Project ID | e.g. `bexo-prod` |
| A real **profile UUID** + **handle** from Supabase | Table `profiles` |
| A **build UUID** | Insert row in `site_builds` or trigger from app |
| `bexo-internal-secret` | GCP Secret Manager |
| DeepSeek API key | Already in `deepseek-api-key` secret (assumed) |

---

## Step 0 — Confirm what is deployed today (5 min)

```bash
export PROJECT_ID=bexo-prod
gcloud config set project $PROJECT_ID

# Service exists?
gcloud run services describe bexo-codegen --region=us-central1 --format="yaml(status.url,spec.template.spec.containers[0].env)"

# Current engine?
curl -s "$(gcloud run services describe bexo-codegen --region=us-central1 --format='value(status.url)')" | python3 -m json.tool
```

Look for `"engine": "claude"` or `"engine": "python"`.

**If the service is still on old Python-only image** (no `build_engine.py`), you **must** redeploy (Step 1).

---

## Step 1 — Deploy the new codegen image (20–40 min)

From your Mac, in the repo:

```bash
cd "/Users/kavin/Documents/GitHub/Bexo Production/bexo-codegen"
gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID
```

This image includes:

- Node 20 + `@anthropic-ai/claude-code`
- Next.js template under `templates/portfolio-next/`
- `build_engine.py` (Claude path)
- 4Gi RAM, 300s timeout

Wait until Cloud Build shows **SUCCESS**.

---

## Step 2 — Set Claude / DeepSeek proxy env vars (5 min) — REQUIRED

`cloudbuild.yaml` sets `CODEGEN_ENGINE=claude` but **not** `ANTHROPIC_BASE_URL`. Add it now:

```bash
gcloud run services update bexo-codegen \
  --region=us-central1 \
  --project=$PROJECT_ID \
  --update-env-vars="ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic,ANTHROPIC_MODEL=deepseek-chat,ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-chat,CLAUDE_CODE_SUBAGENT_MODEL=deepseek-chat,CODEGEN_ENGINE=claude,SKIP_CLAUDE=false"
```

Secrets already mapped by deploy:

- `DEEPSEEK_API_KEY` → used as Claude auth token inside the container
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` → `spec_builder` reads DB

Verify:

```bash
gcloud run services describe bexo-codegen --region=us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

You should see `ANTHROPIC_BASE_URL` and `CODEGEN_ENGINE=claude`.

---

## Step 3 — Safe first test: template only, no Claude CLI (10 min)

Proves Docker + npm + GCS path works **before** spending on Claude.

```bash
gcloud run services update bexo-codegen --region=us-central1 \
  --update-env-vars="SKIP_CLAUDE=true"
```

Run manual build (replace UUIDs):

```bash
export INTERNAL=$(gcloud secrets versions access latest --secret=bexo-internal-secret --project=$PROJECT_ID)
export URL=$(gcloud run services describe bexo-codegen --region=us-central1 --format='value(status.url)')

curl -X POST "${URL}/build" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Internal-Secret: ${INTERNAL}" \
  -d '{
    "profileId": "YOUR_PROFILE_UUID",
    "buildId": "YOUR_BUILD_UUID",
    "handle": "yourhandle"
  }'
```

**Expect:** JSON `"status": "success"` after 3–6 minutes.

Check GCS:

```bash
export PID=YOUR_PROFILE_UUID
gsutil ls "gs://bexo-sites-public/${PID}/site/"
gsutil ls "gs://bexo-sites-public/${PID}/site/_next/static/" | head
```

You need at least:

- `index.html`
- `_next/static/...`
- `data.json`

If this fails, read logs (Step 8) before enabling Claude.

---

## Step 4 — Enable Claude Code for real builds (5 min)

```bash
gcloud run services update bexo-codegen --region=us-central1 \
  --update-env-vars="SKIP_CLAUDE=false"
```

Optional: raise timeout if builds fail at 300s (Cloud Run max 3600 for HTTP):

```bash
gcloud run services update bexo-codegen --region=us-central1 --timeout=600
```

Also ensure n8n Workflow A HTTP node timeout is **300000 ms** (5 min) or higher.

---

## Step 5 — One full Claude build (10–15 min wait)

Use a **new** `build_id` in Supabase (`site_builds` status `queued`) or trigger from the BEXO app (profile must be **≥90%** complete).

Manual curl (same as Step 3 with new `buildId`).

Watch logs live:

```bash
gcloud run services logs tail bexo-codegen --region=us-central1
```

**Success log lines to look for:**

- `Spec from DB`
- `Workspace prepared from template`
- `Claude Code build pass complete` (or `SKIP_CLAUDE` if still testing)
- `npm run build succeeded`
- `All tests passed`
- `GCS site uploaded`

---

## Step 6 — n8n (only if still on old workflow) (10 min)

If Workflow A still has **OpenRouter personality** or **portfolio.md AI** nodes, replace it.

1. In n8n: **Import** `bexo-codegen/infra/n8n/workflows/bexo-portfolio-generate.json` (v2)
2. **Publish** the workflow
3. On n8n VM `~/bexo-n8n/.env` confirm:

```env
CLOUD_RUN_BUILD_URL=https://YOUR-CLOUD-RUN-URL   # no /build suffix
BEXO_INTERNAL_SECRET=same as GCP
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

4. Restart n8n: `docker compose -f docker-compose.micro.yml up -d --force-recreate n8n`

Trigger from app or webhook. n8n should call Cloud Run with only `{ profileId, buildId, handle }`.

---

## Step 7 — Live URL + Cloudflare (10 min)

After Workflow B runs (`bexo-build-done`):

1. KV has `handle` → `profileId`
2. Open `https://yourhandle.mybexo.com`
3. Hard refresh — site should be Next.js (not old single HTML)
4. DevTools → Network → confirm `data.json` and `_next/static/*` return 200

---

## Step 8 — Profile edit without rebuild (5 min)

On api-server (`.env`):

```env
GCS_PUBLIC_BUCKET=bexo-sites-public
GCS_SA_KEY_JSON={"type":"service_account",...}
```

1. Edit a project title in the BEXO app (site must be `done`)
2. Wait ~3 seconds (debounced sync)
3. Refresh `https://handle.mybexo.com` — title should update **without** a new Cloud Run build

---

## Step 9 — Switch production default off Python (2 min)

When Steps 3–7 pass:

```bash
# Confirm engine is claude (not python)
gcloud run services update bexo-codegen --region=us-central1 \
  --update-env-vars="CODEGEN_ENGINE=claude"
```

Keep rollback ready:

```bash
# Emergency only:
gcloud run services update bexo-codegen --region=us-central1 \
  --update-env-vars="CODEGEN_ENGINE=python"
```

---

## Step 10 — What to build next for scale (later)

Not required for launch. See `SCALING-CLAUDE-ORCHESTRATOR.md`:

- Per-build workspace folders (concurrency)
- Cloud Tasks queue (don’t block n8n HTTP forever)
- Pre-baked `node_modules` in Docker
- Rebuild rate limits

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `engine: python` after deploy | Redeploy Step 1; check `cloudbuild.yaml` |
| Claude CLI not found | Redeploy; Dockerfile installs `@anthropic-ai/claude-code` |
| 401 unauthorized | `X-BEXO-Internal-Secret` mismatch |
| 403 profile_incomplete | Fill profile to 90% in app |
| Timeout at 300s | `SKIP_CLAUDE=true` test first; increase timeout; check npm logs |
| Empty site / no `_next` | Build failed mid-way; read Cloud Run logs |
| Claude auth error | Set `ANTHROPIC_BASE_URL`; verify `deepseek-api-key` secret |
| n8n 502 | Cloud Run URL wrong or build crashed — check logs |

### Read last build log

```bash
gcloud run services logs read bexo-codegen --region=us-central1 --limit=100
```

---

## Quick reference — what runs where

| Step | Runs in Cloud Run container |
|------|----------------------------|
| Read user data | `spec_builder.py` → Supabase |
| Instruct Claude | `claude -p` + `prompts/build.txt` + `.claude/CLAUDE.md` |
| Compile site | `npm run build` in workspace |
| QA | `tester.py` Playwright |
| Publish | Upload `out/` + `data.json` to GCS |
| Notify | Flask → n8n `bexo-build-done` |

---

## Checklist (print this)

- [ ] Step 1: Image deployed
- [ ] Step 2: `ANTHROPIC_BASE_URL` set on Cloud Run
- [ ] Step 3: `SKIP_CLAUDE=true` build success + GCS has `_next/`
- [ ] Step 4: `SKIP_CLAUDE=false`
- [ ] Step 5: Full Claude build success
- [ ] Step 6: n8n v2 workflow published
- [ ] Step 7: Live URL works
- [ ] Step 8: Edit in app updates site
- [ ] Step 9: `CODEGEN_ENGINE=claude` locked in prod

When all checked, you have properly built the Claude Code portfolio system on your existing infra.
