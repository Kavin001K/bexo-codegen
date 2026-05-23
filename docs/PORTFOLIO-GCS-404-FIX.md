# Portfolio shows "Upstream GCS 404" (handle.mybexo.com)

## What it means

Cloudflare KV maps `kavin` → `profileId`, but **no site files** exist at:

`gs://bexo-sites-public/{profileId}/site/index.html`

The build never finished uploading, or KV was set before the site existed.

## Fix for one user (kavin)

### 1. Confirm GCS is empty

```bash
# Example: handle kavin (replace with your profile id from Supabase)
PROFILE_UUID=82070c0b-204b-4063-ba2d-15b245c27106
curl -sI "https://storage.googleapis.com/bexo-sites-public/${PROFILE_UUID}/site/index.html" | head -3
```

404 = need a new build.

### 2. Re-deploy Cloud Run (codegen)

Latest revision should include mobile touch-target CSS + relaxed QA (uploads site even if only touch-target warnings remain).

```bash
cd bexo-codegen
gcloud config set project bexo-prod
gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod
```

Check health:

```bash
curl -sS "https://bexo-codegen-901109516440.us-central1.run.app/health"
```

### 3. Re-import n8n workflows

- `infra/n8n/workflows/bexo-portfolio-generate.json` — Cloud Run timeout **660s**
- `infra/n8n/workflows/bexo-build-done.json` — verifies GCS before KV put

### 4. Trigger a new build

From the app (profile ≥ 90%) or:

```bash
curl -X POST "https://n8n.mybexo.com/webhook/bexo-portfolio-generate" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Secret: YOUR_N8N_WEBHOOK_SECRET" \
  -d '{"profileId":"PROFILE_UUID","buildId":"BUILD_UUID"}'
```

### 5. Verify after build

```bash
curl -sI "https://storage.googleapis.com/bexo-sites-public/PROFILE_UUID/site/index.html" | head -1
# HTTP/2 200

curl -sI "https://kavin.mybexo.com" | head -1
# HTTP/2 200
```

## n8n workflow with OpenRouter + GCS nodes

If your Workflow A still has **OpenRouter → GCS → Cloud Run**, the Cloud Run body **must** read from **Extract portfolio.md**, not from the GCS upload response:

```javascript
={{ (() => {
  const e = $('Extract portfolio.md').first().json;
  return { profileId: e.profileId, buildId: e.buildId, handle: e.handle };
})() }}
```

Or switch to Workflow A **v2** (repo JSON): Supabase → Cloud Run only (spec from DB).

## Optional: clear stale KV

If handle points to profile but site is missing, delete KV key `kavin` in Cloudflare → Workers → KV → HANDLE_MAP, then rebuild.
