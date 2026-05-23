# Fix: n8n "Cloud Run — /build" → Method not allowed (405)

## Cause

On the n8n VM, `CLOUD_RUN_BUILD_URL` is set to the **service root** only:

`https://bexo-codegen-901109516440.us-central1.run.app`

The workflow used that URL **without** appending `/build`, so n8n sent **POST /** → Flask returns **405** (only GET is allowed on `/`).

## Fix (pick one)

### A. Re-import workflow (recommended)

1. In n8n: **Workflows** → **BEXO — Portfolio Generate** → **⋯** → **Import from file**
2. File: `bexo-codegen/infra/n8n/workflows/bexo-portfolio-generate.json`
3. **Publish** the workflow

The Cloud Run node URL now always ends with `/build`, even when `CLOUD_RUN_BUILD_URL` has no path.

### B. Edit the node manually

**Cloud Run — /build** node:

- **Method:** `POST` (not GET)
- **URL:**

```text
https://bexo-codegen-901109516440.us-central1.run.app/build
```

Or expression:

```javascript
={{ (() => {
  const raw = $env.CLOUD_RUN_BUILD_URL || 'https://bexo-codegen-901109516440.us-central1.run.app';
  const base = String(raw).replace(/\/build\/?$/i, '').replace(/\/$/, '');
  return base + '/build';
})() }}
```

- **Header:** `X-BEXO-Internal-Secret` = `{{ $env.BEXO_INTERNAL_SECRET }}`
- **Timeout:** `660000` ms

### C. Match secrets

`BEXO_INTERNAL_SECRET` on the n8n VM must equal GCP secret `bexo-internal-secret` (same value Cloud Run uses).

```bash
gcloud secrets versions access latest --secret=bexo-internal-secret --project=bexo-prod
```

Update `~/bexo-n8n/.env` (or your n8n env file), then restart n8n:

```bash
docker compose -f docker-compose.micro.yml up -d
```

## Verify

```bash
# Wrong (405):
curl -sI -X POST "https://bexo-codegen-901109516440.us-central1.run.app/" | head -1

# Right path (401 without secret, 400/200 with secret + body):
curl -sI -X POST "https://bexo-codegen-901109516440.us-central1.run.app/build" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Internal-Secret: YOUR_SECRET" \
  -d '{"profileId":"82070c0b-204b-4063-ba2d-15b245c27106","buildId":"test","handle":"kavin"}' | head -1
```

After a successful n8n run, GCS must return **200**:

```bash
curl -sI "https://storage.googleapis.com/bexo-sites-public/82070c0b-204b-4063-ba2d-15b245c27106/site/index.html" | head -1
```

Then:

```bash
curl -sI "https://kavin.mybexo.com" | head -1
```
