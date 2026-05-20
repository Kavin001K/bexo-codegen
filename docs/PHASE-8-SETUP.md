# Phase 8 — Wire BEXO app (step by step)

**Goal:** User taps Generate in the app → n8n Workflow A → Cloud Run → Workflow B → **https://{handle}.mybexo.com**

**Prerequisites:** Phase 7 complete ([PHASE-7-PRODUCTION-CHECKLIST.md](PHASE-7-PRODUCTION-CHECKLIST.md)).

---

## Step 1 — Get webhook secret from n8n VM

On `bexo-n8n` (do not paste secret in tickets):

```bash
grep '^N8N_WEBHOOK_SECRET=' ~/bexo-n8n/.env
```

Copy the value (no quotes in file unless quoted).

---

## Step 2 — Configure BEXO api-server

In your **BEXO backend** repo (api-server / Supabase edge / wherever builds are triggered), add:

```env
N8N_WEBHOOK_URL=https://n8n.mybexo.com/webhook/bexo-portfolio-generate
N8N_WEBHOOK_SECRET=<same value as ~/bexo-n8n/.env N8N_WEBHOOK_SECRET>
```

The server must `POST` JSON:

```json
{
  "profileId": "<uuid>",
  "buildId": "<uuid>",
  "triggered_by": "app"
}
```

Headers:

```http
Content-Type: application/json
X-BEXO-Secret: <N8N_WEBHOOK_SECRET>
```

Match whatever your Workflow A **Verify X-BEXO-Secret** node expects.

---

## Step 3 — Redeploy Cloud Run (if not done since public bucket)

On your Mac:

```bash
cd ~/Documents/GitHub/bexo-codegen
gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod
```

Ensures new builds write HTML to **`bexo-sites-public`** automatically.

---

## Step 4 — Confirm callback secret on Cloud Run

```bash
gcloud secrets versions access latest --secret=n8n-callback-url --project=bexo-prod
# Must be: https://n8n.mybexo.com/webhook/bexo-build-done

bash infra/gcp/setup-phase5-callback.sh   # if wrong or empty
```

After a build, Cloud Run logs should show callback **200**.

---

## Step 5 — In-app test

1. Create or use a profile with a **unique handle** (not only `kavink`).
2. Start generation from the app.
3. Watch:
   - Supabase `site_builds.status`: `queued` → `building` → `done`
   - n8n: Workflow A then Workflow B executions green
   - Browser: `https://{handle}.mybexo.com`

---

## Step 6 — Update HTML build guide baseline

On Mac after Phase 8 passes:

```bash
cd ~/Documents/GitHub/bexo-codegen
# Edit scripts/generate_build_guide.py — add p8-1..p8-5 to DEFAULT_COMPLETED
python3 scripts/generate_build_guide.py
```

Open `docs/bexo-unified-build-guide.html` in browser → Phase 08 checkboxes.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| App gets 401/403 from n8n | `N8N_WEBHOOK_SECRET` mismatch |
| Build stuck on `building` | n8n Workflow A execution error |
| `done` but 404 on URL | Workflow B KV node; handle typo |
| `done` but old HTML | KV points to wrong profileId; rerun build |
| Callback never runs | Cloud Run `N8N_CALLBACK_URL` / internal secret |

---

## Done when

- [ ] App trigger (no manual `curl`)
- [ ] `site_builds.portfolio_url` = `https://{handle}.mybexo.com`
- [ ] Live site loads on phone + desktop
- [ ] Phase 8 boxes checked in unified build guide
