# BEXO pipeline — build progress log

Living document for the GCP + n8n + Cloud Run portfolio pipeline. Update this file as phases complete.

**Project:** `bexo-prod`  
**Last updated:** 2026-05-20

---

## Architecture

```text
BEXO app (api-server)
  → POST n8n webhook (X-BEXO-Secret = N8N_WEBHOOK_SECRET)
  → Supabase site_builds + profile data
  → OpenRouter free (portfolio.md spec)
  → GCS upload portfolio.md
  → Cloud Run bexo-codegen /build (X-BEXO-Internal-Secret) ✓ E2E
  → GCS + GitHub + callback n8n build-done
  → Workflow B: Cloudflare KV + Supabase done
  → https://{handle}.mybexo.com (Worker → KV → bexo-sites-public)
```

---

## Secret map (do not confuse)

| Secret | Where |
|--------|--------|
| `N8N_WEBHOOK_SECRET` | BEXO `.env` + n8n VM `.env` — header `X-BEXO-Secret` |
| `BEXO_INTERNAL_SECRET` | GCP `bexo-internal-secret` + n8n VM + Cloud Run — header `X-BEXO-Internal-Secret` |
| `N8N_ENCRYPTION_KEY` | n8n VM only — encrypts n8n DB (never share with BEXO app) |

---

## Phase status

| Phase | Status | Notes |
|-------|--------|--------|
| 1 — GCP foundation | Done | `bexo-prod`, bucket `bexo-portfolios`, SAs, Secret Manager |
| 2 — n8n VM | Done | `bexo-n8n` e2-micro, `https://n8n.mybexo.com`, Postgres in Docker |
| 3 — n8n workflows | Done | Workflow A E2E green — OpenRouter free, GCS, Cloud Run 200 |
| 4 — Cloud Run codegen | Done | Revision 00005+; `POST /build` 200; `site/index.html` in GCS |
| 5 — GitHub | Pending | Optional org/repos |
| 6 — Hosting | **Done** | `bexo-sites-public` + Cloudflare Worker `bexo-portfolio-proxy` |
| 7 — DNS + build-done | **Done** | Workflow B green; `https://kavink.mybexo.com` verified 2026-05-20 |
| 8 — BEXO app E2E | **Next** | `docs/PHASE-8-SETUP.md` |

---

## Phase 1 — GCP (done)

- Project: `bexo-prod`
- Bucket: `gs://bexo-portfolios`
- Service accounts: `bexo-codegen@`, `n8n-invoker@`
- Secrets in Secret Manager (10): see `gcloud secrets list --project=bexo-prod`

IAM: `bexo-codegen@` has `secretAccessor` on all pipeline secrets.

---

## Phase 2 — n8n VM (done)

- VM: `bexo-n8n` / `us-central1-a` / e2-micro
- URL: `https://n8n.mybexo.com` (nginx + Let's Encrypt)
- Compose: `~/bexo-n8n/docker-compose.micro.yml`
- Cloudflare: **grey cloud (DNS only)** on `n8n` A record (proxied breaks cert)

---

## Phase 3 — n8n workflows (done)

### Critical n8n 2.x settings (VM `~/bexo-n8n/.env` + compose)

```env
N8N_BLOCK_ENV_ACCESS_IN_NODE=false
```

```yaml
# docker-compose.micro.yml — image MUST be 2.x if DB was created on 2.x
image: docker.n8n.io/n8nio/n8n:2.20.9
```

**Do not** pin `1.97.1` after using 2.x — login error: `column User.role does not exist`.

### Workflows imported

- `BEXO — Portfolio Generate` — webhook `/webhook/bexo-portfolio-generate`
- `BEXO — Build Done` — inactive until Phase 5
- Delete duplicate imports (Webhook1, etc.) — keep one active copy

### Workflow fix (repo)

`Supabase — fetch profile` must use:

```text
$('Webhook').item.json.body.profileId
```

not `$json.body.profileId` (breaks after Supabase PATCH node).

### OpenRouter — personality “Bad request” (2026-05-19)

**Cause:** Supabase GET returns a JSON **array**; the old body used `content: {{ JSON.stringify($json) }}` without a string wrapper, so OpenRouter received invalid `messages[].content` (object/array, not string). Default model `deepseek/deepseek-chat` is **not** free on OpenRouter.

**Fix (repo):** Re-import `infra/n8n/workflows/bexo-portfolio-generate.json`. Both AI nodes use `OPENROUTER_MODEL_SPEC` default `openrouter/free` and build the request body via `={{ ... }}` object expressions.

**VM `~/bexo-n8n/.env`:**

```env
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL_SPEC=openrouter/free
```

Then: `docker compose -f docker-compose.micro.yml up -d --force-recreate n8n`

### Cloud Run — /build “Bad request” (2026-05-19)

**Cause:** GCS node output replaces `$json`. Cloud Run was sending `{{ $json.profileId }}` from GCS metadata → empty body → codegen `400 profileId required`.

**Fix:** Re-import workflow; Cloud Run body reads `$('Extract portfolio.md').first().json`. Ensure VM has `CLOUD_RUN_BUILD_URL` (no trailing slash) and `BEXO_INTERNAL_SECRET` matching GCP `bexo-internal-secret`.

### Cloud Run — “service was not able to process your request” (2026-05-19)

**Cause (from logs):** Cloud Run returned **HTTP 500**. Codegen fell back to paid OpenRouter model `moonshotai/kimi-k2` → **402 insufficient credits** with `max_tokens=8000`.

**Fix:** Redeploy codegen with `OPENROUTER_FREE_ONLY=true` and `openrouter/free` models (`cloudbuild.yaml` updated). Re-import n8n workflow (Cloud Run node timeout **300s**).

**Verify logs:**

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="bexo-codegen"' \
  --project=bexo-prod --limit=10 --format='value(textPayload)'
```

Look for `[LLM] task=generate provider=openrouter (free-only) model=openrouter/free` — not `moonshotai/kimi-k2`.

### Cloud Run — build failed after 3 attempts (mobile QA, not credits)

**Log:** `RuntimeError: Build failed after 3 attempts: ['Horizontal overflow on 375px mobile viewport', '7 interactive elements below 44px touch target']`

**Cause:** AI ran successfully (3 generate/fix cycles). **Playwright quality gates** rejected the HTML. Not an API credit/balance issue.

**Fix (deployed):** Auto-inject `mobile_safety.css` before tests; stronger prompts; touch-target threshold tuned. Redeploy codegen then re-run webhook.

**gsutil 403 on Mac/VM:** Your Google account / default compute SA lacks `storage.objects.get` on `bexo-portfolios`. Cloud Run `bexo-codegen@` can read — use n8n execution output or grant yourself `roles/storage.objectViewer` on the bucket to debug.

### Cloud Run — GitHub org 404 (2026-05-19, actual latest failure)

**Log:** `github.GithubException.UnknownObjectException: 404` on `GET /orgs/bexo-sites` — org does not exist.

**Not credits.** Mobile QA passed; HTML saved to GCS; push failed on GitHub only.

**Fix (deployed):** `GITHUB_ORG=auto` → create repo under GitHub token user if org missing; GitHub errors are non-fatal (build still returns 200). n8n Cloud Run URL hardcoded (no `$env` for URL). Re-import workflow + redeploy codegen.

**Create org later (optional):** https://github.com/organizations/plan → `bexo-sites`, then set `GITHUB_ORG=bexo-sites` on Cloud Run.

### Test webhook (Mac)

```bash
curl -X POST "https://n8n.mybexo.com/webhook/bexo-portfolio-generate" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Secret: YOUR_N8N_WEBHOOK_SECRET" \
  -d '{"profileId":"UUID","buildId":"UUID","triggered_by":"test"}'
```

---

## Phase 4 — Cloud Run (done)

### Fixes applied (2026-05-18)

1. **cloudbuild.yaml** — use `$BUILD_ID` not `$COMMIT_SHA` (empty on `gcloud builds submit`).
2. **Dockerfile** — remove `playwright install chromium --with-deps` (fails on Debian Trixie in Cloud Build). Use system `/usr/bin/chromium` via `CHROME_PATH`.
3. **tester.py** — `chromium.launch(executable_path=CHROME_PATH)`.

### Service URL

```text
https://bexo-codegen-901109516440.us-central1.run.app
```

Revision: `bexo-codegen-00005-q4b` (2026-05-20). E2E: `POST /build` **200**, HTML at `gs://bexo-portfolios/{profileId}/site/index.html`.

`--allow-unauthenticated`: browser can open `/` and `/health`. **POST /build** still requires header `X-BEXO-Internal-Secret` (app-level auth). n8n may use OIDC (`n8n-invoker@`) or the same secret header.

### Deploy commands

```bash
cd /Users/kavin/Documents/GitHub/bexo-codegen
gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod .
```

Health check (with your user identity token):

```bash
CODEGEN_URL=$(gcloud run services describe bexo-codegen \
  --region=us-central1 --project=bexo-prod --format='value(status.url)')
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$CODEGEN_URL/health"
```

Invoker binding (done):

```bash
gcloud run services add-iam-policy-binding bexo-codegen \
  --region=us-central1 --project=bexo-prod \
  --member="serviceAccount:n8n-invoker@bexo-prod.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

### VM after deploy

Add to `~/bexo-n8n/.env`:

```env
CLOUD_RUN_BUILD_URL=https://bexo-codegen-XXXX.run.app
```

```bash
docker compose -f docker-compose.micro.yml up -d --force-recreate n8n
```

Activate **Cloud Run — /build** in Workflow A (was deactivated for Phase 3).

### Manual /build test

```bash
echo "# Test" | gsutil cp - gs://bexo-portfolios/PROFILE_UUID/portfolio.md

INTERNAL=$(gcloud secrets versions access latest --secret=bexo-internal-secret --project=bexo-prod)

curl -X POST "$CODEGEN_URL/build" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Internal-Secret: $INTERNAL" \
  -d '{"profileId":"PROFILE_UUID","buildId":"BUILD_UUID","handle":"testuser"}'
```

---

## Phase 6–7 — Hosting + live URLs (done 2026-05-20)

**Guides:** [PORTFOLIO-HOSTING-PLAN.md](PORTFOLIO-HOSTING-PLAN.md) · [PHASE-7-PRODUCTION-CHECKLIST.md](PHASE-7-PRODUCTION-CHECKLIST.md)

| Component | Detail |
|-----------|--------|
| Private spec | `gs://bexo-portfolios/{profileId}/portfolio.md` |
| Public HTML | `gs://bexo-sites-public/{profileId}/site/index.html` |
| KV | `bexo-handles` namespace — handle → profileId |
| Worker | `bexo-portfolio-proxy` route `*.mybexo.com/*` |
| Verified | `curl -sI https://kavink.mybexo.com` → 200 |

**VM fixes applied:** `CLOUDFLARE_*` via `env_file` only (not compose `environment:` override); quoted tokens in `.env`.

**Known cosmetic issue:** profile image 404 on generated HTML (asset URLs not in public bucket).

## Phase 8 — Next

**Guide:** [PHASE-8-SETUP.md](PHASE-8-SETUP.md)

1. `N8N_WEBHOOK_URL` + `N8N_WEBHOOK_SECRET` on BEXO api-server
2. Redeploy Cloud Run (`GCS_PUBLIC_BUCKET=bexo-sites-public`)
3. In-app generate → full chain → live URL

HTML guide: **Phase 08** in `docs/bexo-unified-build-guide.html`.

---

## Useful commands

```bash
# List secrets
gcloud secrets list --project=bexo-prod

# Cloud Build logs
gcloud builds list --project=bexo-prod --limit=5

# SSH n8n VM
gcloud compute ssh bexo-n8n --zone=us-central1-a

# Verify n8n env in container
docker exec bexo-n8n printenv N8N_BLOCK_ENV_ACCESS_IN_NODE
docker exec bexo-n8n n8n --version
```

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-17 | GCP foundation, n8n VM, secrets |
| 2026-05-18 | n8n `$env` fix (`N8N_BLOCK_ENV_ACCESS_IN_NODE=false`, stay on 2.20.9) |
| 2026-05-18 | Workflow webhook body fix; cloudbuild `$BUILD_ID` |
| 2026-05-18 | Dockerfile: system Chromium, drop Playwright browser download |
| 2026-05-18 | Cloud Build SUCCESS; Cloud Run live; `n8n-invoker` run.invoker granted |
| 2026-05-19 | Public `allUsers` invoker for browser `/health`; `/` info route; `/build` still secret-gated |
| 2026-05-20 | Workflow A E2E success; Phases 1–4 complete; HTML guide baseline 32/56 checks |
| 2026-05-20 | Phases 6–7 complete: bexo-sites-public, Worker+KV, kavink.mybexo.com live; Phase 8 guide added |
