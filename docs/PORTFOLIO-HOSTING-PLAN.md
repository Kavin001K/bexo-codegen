# BEXO portfolio hosting — one plan (do this)

**Status (2026-05-20):** MVP live — e.g. https://kavink.mybexo.com. Security review: [PHASE-7-PRODUCTION-CHECKLIST.md](PHASE-7-PRODUCTION-CHECKLIST.md). Next: [PHASE-8-SETUP.md](PHASE-8-SETUP.md).

**Chosen approach:** Cloudflare **Worker** + **KV** + public bucket `bexo-sites-public` (HTML only).

Why not `origin.mybexo.com` CNAME chains alone? They only point DNS; they do not serve files from GCS. The Worker serves HTML; KV maps `handle` → `profileId`.

```text
Student opens  https://kavin.mybexo.com
       ↓
Cloudflare Worker (reads handle from hostname)
       ↓
KV: kavin → d6b027d4-...-profileId
       ↓
Fetches  gs://bexo-sites-public/{profileId}/site/index.html  (public read)
```

You can **skip** per-student Cloudflare CNAME records if you use a wildcard (step 4).

---

## Order of work (do top to bottom)

| # | What | Time |
|---|------|------|
| 1 | Finish Phase 7 callback (n8n Workflow B + secrets) | ~15 min |
| 2 | Allow public read on portfolio HTML in GCS (one command) | ~5 min |
| 3 | Create Cloudflare KV namespace | ~5 min |
| 4 | Deploy Cloudflare Worker | ~20 min |
| 5 | Add wildcard DNS `*` | ~2 min |
| 6 | Add KV write to Workflow B + test one build | ~15 min |
| 7 | Wire BEXO app (Phase 8) | later |

---

## Step 1 — Finish Phase 7 (callback)

On n8n VM `~/bexo-n8n/.env` (you already have most of this):

```env
BEXO_INTERNAL_SECRET=<same as GCP bexo-internal-secret>
CLOUDFLARE_ZONE_ID=<zone id for mybexo.com>
CLOUDFLARE_TOKEN=<api token with DNS Edit + Workers KV Edit>
CLOUDFLARE_ACCOUNT_ID=<account id from Cloudflare dashboard>
CLOUDFLARE_KV_NAMESPACE_ID=<from step 3 — add after you create it>
PORTFOLIO_DOMAIN=mybexo.com
```

```bash
cd ~/bexo-n8n
docker compose -f docker-compose.micro.yml up -d --force-recreate n8n
```

n8n: import + publish **`bexo-build-done.json`** and **`bexo-portfolio-generate.json`**.

Test callback:

```bash
INTERNAL=$(gcloud secrets versions access latest --secret=bexo-internal-secret --project=bexo-prod)
curl -X POST "https://n8n.mybexo.com/webhook/bexo-build-done" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Internal-Secret: $INTERNAL" \
  -d '{"profileId":"UUID","buildId":"UUID","handle":"yourhandle","status":"success","siteUrl":"https://yourhandle.mybexo.com","buildLog":"test"}'
```

Success = Supabase `site_builds.status` → `done`.

**You do NOT need `CDN_ORIGIN_HOST` for the Worker plan.** (Leave it empty or remove it.)

---

## Step 2 — Public read for portfolio HTML (GCS)

GCP **does not allow** IAM conditions on `allUsers` (you will get `PublicResourceAllowConditionCheck`).  
Use a **separate bucket** that only holds published `index.html` files. `portfolio.md` stays private in `bexo-portfolios`.

Run once from your Mac:

```bash
cd ~/Documents/GitHub/bexo-codegen
chmod +x infra/gcp/setup-public-sites-bucket.sh
./infra/gcp/setup-public-sites-bucket.sh
```

Copy an existing build into the public bucket (one-time for tests before redeploying codegen):

```bash
gcloud storage cp \
  gs://bexo-portfolios/d6b027d4-4f14-43ef-8aee-38b9534176d8/site/index.html \
  gs://bexo-sites-public/d6b027d4-4f14-43ef-8aee-38b9534176d8/site/index.html
```

Verify:

```bash
curl -sI "https://storage.googleapis.com/bexo-sites-public/d6b027d4-4f14-43ef-8aee-38b9534176d8/site/index.html" | head -5
```

Expect `HTTP/2 200`.

Future builds: redeploy Cloud Run so codegen writes to both buckets (`GCS_PUBLIC_BUCKET=bexo-sites-public` in `cloudbuild.yaml`).

---

## Step 3 — Cloudflare KV namespace

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → **Workers & Pages** → **KV**
2. **Create namespace** → name: `bexo-handles`
3. Copy **Namespace ID** → `CLOUDFLARE_KV_NAMESPACE_ID` in VM `.env`
4. Copy **Account ID** (right sidebar on Workers overview) → `CLOUDFLARE_ACCOUNT_ID`

---

## Step 4 — Deploy the Worker

On your Mac:

```bash
cd /path/to/bexo-codegen/infra/cloudflare/worker
npm install -g wrangler   # if needed
wrangler login

# Edit wrangler.toml: set your KV namespace id
wrangler deploy
```

In Cloudflare → Worker → **Settings** → **Triggers** → **Routes**:

| Route | Worker |
|-------|--------|
| `*.mybexo.com/*` | `bexo-portfolio-proxy` |

---

## Step 5 — Wildcard DNS (one manual record)

Cloudflare → **DNS** → **Add record**:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| `CNAME` | `*` | `mybexo.com` | **Proxied** (orange) |

(Alternative: Workers custom domain wizard may add this for you.)

**Do not** create `origin.mybexo.com` unless you want a separate legacy path — not required for this plan.

---

## Step 6 — KV on every successful build

Workflow B must write KV when a site is built:

- **Key:** student `handle` (e.g. `kavin`)
- **Value:** `profileId` (UUID)

Re-import `infra/n8n/workflows/bexo-build-done.json` from this repo (includes **Cloudflare — KV put handle** node).

Full E2E test:

```bash
curl -X POST "https://n8n.mybexo.com/webhook/bexo-portfolio-generate" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Secret: YOUR_N8N_WEBHOOK_SECRET" \
  -d '{"profileId":"UUID","buildId":"UUID","triggered_by":"e2e"}'
```

Wait ~3–5 min, then open:

`https://YOUR_HANDLE.mybexo.com`

---

## Step 7 — Phase 8 (after sites load)

BEXO api-server `.env`:

```env
N8N_WEBHOOK_URL=https://n8n.mybexo.com/webhook/bexo-portfolio-generate
N8N_WEBHOOK_SECRET=<same as n8n VM>
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| 404 on student URL | KV missing handle → re-run build; check Workflow B KV node |
| 403 on storage.googleapis.com | Run `setup-public-sites-bucket.sh`; copy HTML to `bexo-sites-public` |
| Worker not running | Route `*.mybexo.com/*` attached |
| Build Done never runs | `N8N_CALLBACK_URL` on Cloud Run; check logs `[CALLBACK] n8n 200` |
| n8n vs www broken | Worker skips `n8n`, `www`, `origin` hostnames |

---

## What we stopped using

| Old idea | Why dropped |
|----------|-------------|
| `CDN_ORIGIN_HOST=origin.mybexo.com` only | DNS target without a server serving GCS |
| Per-handle CNAME → origin | Optional; wildcard + Worker is simpler |
| GitHub Pages as origin | Pipeline is GCS-first |

Track progress in `docs/bexo-unified-build-guide.html` (Phases 6–8).
