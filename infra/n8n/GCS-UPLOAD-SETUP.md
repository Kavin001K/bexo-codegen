# GCS upload in Workflow A (Step-by-step)

Codegen needs this file **before** Cloud Run runs:

`gs://bexo-portfolios/{profileId}/portfolio.md`

OpenRouter writes the markdown in n8n memory only — you must **upload it to GCS** in the workflow.

---

## Overview (3 parts)

| Part | Where | Time |
|------|--------|------|
| A | Mac — create GCP service account + JSON key | ~5 min |
| B | n8n UI — credential + 2 nodes | ~10 min |
| C | Test — one webhook run | ~5 min |

---

## Part A — GCP service account (on your Mac)

### A1. Create account

```bash
gcloud config set project bexo-prod

gcloud iam service-accounts create n8n-gcs \
  --display-name="n8n GCS portfolio uploads" 2>/dev/null || echo "SA already exists"

gcloud projects add-iam-policy-binding bexo-prod \
  --member="serviceAccount:n8n-gcs@bexo-prod.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin" \
  --quiet
```

### A2. Download key (keep private)

```bash
gcloud iam service-accounts keys create ~/bexo-n8n-gcs-key.json \
  --iam-account=n8n-gcs@bexo-prod.iam.gserviceaccount.com

chmod 600 ~/bexo-n8n-gcs-key.json
echo "Key saved: ~/bexo-n8n-gcs-key.json"
```

Do **not** commit this file to git.

---

## Part B — n8n workflow (browser)

Open https://n8n.mybexo.com → workflow **BEXO — Portfolio Generate (Workflow A)**.

### B1. Add credential (NOT “Google Cloud Storage OAuth2”)

**Close** any screen that shows **Client ID**, **Client Secret**, and **Sign in with Google** — that is the wrong type.

1. Left sidebar → **Credentials** → **Add credential**.
2. Search **`Google Service Account`** (not “Google Cloud Storage”).
3. Pick **Google Service Account API**.
4. Open `~/bexo-n8n-gcs-key.json` on your Mac (`open ~/bexo-n8n-gcs-key.json`).
5. Fill n8n:
   - **Service Account Email** → copy `client_email` from JSON  
   - **Private Key** → copy the full `private_key` value (from `-----BEGIN` through `-----END-----`)  
   - Turn **ON**: **Set up for use in HTTP Request node**  
   - **Scope(s)** → add: `https://www.googleapis.com/auth/devstorage.read_write`
6. Name: `BEXO GCS n8n` → **Save** / **Test** if available.

Enable API once on Mac (if upload fails with 403):

```bash
gcloud services enable storage.googleapis.com --project=bexo-prod
```

### B2. Add node: **Extract portfolio.md** (Set)

1. Click **+** between **OpenRouter — portfolio.md** and **Cloud Run — /build**.
2. Search **Edit Fields (Set)** → add it.
3. Rename to: `Extract portfolio.md`
4. Mode: **Manual Mapping**
5. Add fields:

| Name | Value (expression) |
|------|-------------------|
| `portfolio_md` | `{{ $json.choices[0].message.content }}` |
| `profileId` | `{{ $('Webhook').item.json.body.profileId }}` |
| `buildId` | `{{ $('Webhook').item.json.body.buildId }}` |
| `handle` | `{{ $('Supabase — fetch profile').item.json[0].handle }}` |

6. **Save** node.

### B3. Add node: **GCS — upload portfolio.md** (HTTP Request — works with Service Account)

The **Google Cloud Storage** node often only accepts OAuth2. Use **HTTP Request** instead:

1. Add node after **Extract portfolio.md**.
2. Search **HTTP Request**.
3. Rename: `GCS — upload portfolio.md`
4. Settings:
   - **Method:** `POST`
   - **URL:**  
     `https://storage.googleapis.com/upload/storage/v1/b/bexo-portfolios/o?uploadType=media&name={{ encodeURIComponent($json.profileId + '/portfolio.md') }}`
   - **Authentication:** Predefined Credential Type  
   - **Credential Type:** `Google Service Account API` (or `Google Service Account`)  
   - **Credential:** `BEXO GCS n8n`
   - **Send Body:** ON  
   - **Body Content Type:** Raw / Text  
   - **Body:** `{{ $json.portfolio_md }}`
   - **Headers** → add: `Content-Type` = `text/markdown`
5. **Save**.

**Alternative:** If your n8n GCS node lets you pick `BEXO GCS n8n` (Service Account), use **Google Cloud Storage** → Create object instead of HTTP Request.

### B4. Rewire connections

Order must be:

```text
OpenRouter — portfolio.md
  → Extract portfolio.md
  → GCS — upload portfolio.md
  → Cloud Run — /build
```

1. Disconnect **OpenRouter — portfolio.md** from **Cloud Run** (delete the arrow).
2. Connect: OpenRouter → Extract → GCS → Cloud Run.
3. **Save workflow** (top right).
4. Workflow toggle **Active** = ON.

### B5. Cloud Run node body (required)

After **GCS — upload**, `$json` is the **GCS API response**, not your profile fields. The Cloud Run node must read from **Extract portfolio.md**:

```javascript
={{ (() => {
  const e = $('Extract portfolio.md').first().json;
  return { profileId: e.profileId, buildId: e.buildId, handle: e.handle };
})() }}
```

URL (no double slash):

```text
={{ ($env.CLOUD_RUN_BUILD_URL || '').replace(/\/$/, '') }}/build
```

---

## Part C — Test

### C1. Use real IDs from Supabase

You need a real row in `profiles` (with `handle`) and `site_builds`.

From Supabase SQL editor or table view, copy:

- `profiles.id` → `PROFILE_UUID`
- `site_builds.id` → `BUILD_UUID`

### C2. Fire webhook (Mac)

```bash
curl -X POST "https://n8n.mybexo.com/webhook/bexo-portfolio-generate" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Secret: YOUR_N8N_WEBHOOK_SECRET" \
  -d '{
    "profileId": "PROFILE_UUID",
    "buildId": "BUILD_UUID",
    "triggered_by": "gcs-test"
  }'
```

### C3. Check in n8n

**Executions** → latest run → every node green, especially:

- Extract portfolio.md  
- GCS — upload portfolio.md  
- Cloud Run — /build  

### C4. Check GCS (Mac)

```bash
gsutil cat gs://bexo-portfolios/PROFILE_UUID/portfolio.md | head -20
```

You should see markdown starting with `# Identity` or similar.

### C5. Check Cloud Run logs (optional)

```bash
gcloud run services logs read bexo-codegen \
  --region=us-central1 --project=bexo-prod --limit=30
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| GCS node “Forbidden” | SA needs `storage.objectAdmin`; bucket name `bexo-portfolios` |
| `choices[0].message.content` empty | OpenRouter failed — open that node’s output in execution |
| Cloud Run “portfolio.md not found” | GCS node failed or wrong `profileId` in object path |
| `access to env vars denied` | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` + recreate n8n container |
| Extract node can’t find Webhook | Use exact node name `Webhook` (capital W) |

---

## HTML guide checklist

When C4 works, tick in **Phase 03**:

- **GCS upload node writes portfolio.md**

When Cloud Run succeeds:

- **Manual /build with sample portfolio.md** (Phase 04)
