# Deploy n8n on Render.com (instead of GCE VM)

## Does it work for BEXO?

**Yes** for MVP and early users. The pipeline stays the same:

`BEXO app → api-server → n8n webhook → Supabase + AI → GCS → Cloud Run → callback → Supabase + DNS`

## Tradeoffs vs GCE VM

| | Render | GCE VM |
|---|--------|--------|
| Cost | ~$14/mo (web $7 + Postgres $7) | ~$13/mo e2-small |
| Setup | Easier, no nginx/certbot | More control |
| Queue + worker | Skip (single instance) | Docker Compose worker |
| Cold starts | None on **Starter** plan | N/A |
| Webhook URL | `https://bexo-n8n.onrender.com` | `https://n8n.mybexo.com` |

**Skip Redis/queue mode on Render** — workflows run on the main instance. Fine until you have many simultaneous builds.

## Realistic Render pricing (2025)

- **Web Service (Starter):** ~$7/mo — always on, required for webhooks
- **PostgreSQL (Starter):** ~$7/mo — n8n workflow DB (not your Supabase app DB)
- **Total:** ~$14/mo (not $5 — free tier spins down and breaks webhooks)

---

## Step-by-step

### 1. Create Render account

https://render.com → sign up → connect GitHub (optional).

### 2. Create PostgreSQL first

1. **New +** → **PostgreSQL**
2. Name: `bexo-n8n-db`
3. Plan: **Starter**
4. Region: same as you'll use for web (e.g. Oregon / Ohio)
5. Create → copy **Internal Database URL** (starts with `postgresql://`)

### 3. Create n8n Web Service

1. **New +** → **Web Service**
2. **Deploy an existing image from a registry**
3. Image URL: `docker.n8n.io/n8nio/n8n:latest`
4. Name: `bexo-n8n`
5. Plan: **Starter** (must be always-on)
6. Health check path: `/healthz`

### 4. Environment variables

In the web service → **Environment**:

| Key | Value |
|-----|--------|
| `N8N_HOST` | `0.0.0.0` |
| `N8N_PORT` | `5678` |
| `N8N_PROTOCOL` | `https` |
| `N8N_BASIC_AUTH_ACTIVE` | `true` |
| `N8N_BASIC_AUTH_USER` | `admin` |
| `N8N_BASIC_AUTH_PASSWORD` | strong password you choose |
| `N8N_ENCRYPTION_KEY` | output of `openssl rand -hex 32` |
| `WEBHOOK_URL` | `https://bexo-n8n.onrender.com/` (your Render URL + **trailing slash**) |
| `DB_TYPE` | `postgresdb` |
| `DB_POSTGRESDB_HOST` | from Render Postgres dashboard |
| `DB_POSTGRESDB_PORT` | `5432` |
| `DB_POSTGRESDB_DATABASE` | `n8n` |
| `DB_POSTGRESDB_USER` | from dashboard |
| `DB_POSTGRESDB_PASSWORD` | from dashboard |
| `GENERIC_TIMEZONE` | `UTC` |

**Workflow secrets (add as env vars on Render):**

| Key | Value |
|-----|--------|
| `N8N_WEBHOOK_SECRET` | same as BEXO `N8N_WEBHOOK_SECRET` |
| `BEXO_INTERNAL_SECRET` | same hex as GCP secret |
| `OPENROUTER_API_KEY` | your OpenRouter key |
| `SUPABASE_URL` | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | service role key |
| `DEEPSEEK_MODEL_SPEC` | `deepseek/deepseek-chat` |
| `CLOUD_RUN_BUILD_URL` | add after Phase 4 deploy |

Do **not** set `EXECUTIONS_MODE=queue` (no Redis on Render).

### 5. Deploy

Click **Deploy**. Wait until status is **Live**.

Open: `https://bexo-n8n.onrender.com`  
Login: `admin` + your password.

### 6. Custom domain (optional)

Render → service → **Settings** → **Custom Domains** → add `n8n.mybexo.com`

Cloudflare DNS:

| Type | Name | Target |
|------|------|--------|
| CNAME | `n8n` | `bexo-n8n.onrender.com` |

Update `WEBHOOK_URL` to `https://n8n.mybexo.com/` and redeploy.

### 7. Import workflows

1. n8n UI → **⋯** → **Import from file**
2. Import from repo:
   - `infra/n8n/workflows/bexo-portfolio-generate.json`
   - `infra/n8n/workflows/bexo-build-done.json`
   - `infra/n8n/workflows/bexo-rebuild.json`
3. **Activate** each workflow
4. Open Webhook node → copy production URL, e.g.  
   `https://bexo-n8n.onrender.com/webhook/bexo-portfolio-generate`

### 8. Wire BEXO api-server

```env
N8N_WEBHOOK_URL=https://bexo-n8n.onrender.com/webhook/bexo-portfolio-generate
N8N_WEBHOOK_SECRET=<same as Render N8N_WEBHOOK_SECRET>
```

### 9. Update GCP secret (callback URL)

```bash
echo -n "https://bexo-n8n.onrender.com/webhook/bexo-build-done" | \
  gcloud secrets versions add n8n-callback-url --data-file=-
```

---

## Phase 2 checklist (Render version)

- [ ] Render Postgres `bexo-n8n-db` live
- [ ] Render Web Service `bexo-n8n` live (Starter plan)
- [ ] `https://YOUR-SERVICE.onrender.com` loads with basic auth
- [ ] `WEBHOOK_URL` set with trailing slash
- [ ] Workflows imported + activated
- [ ] BEXO `N8N_WEBHOOK_URL` + `N8N_WEBHOOK_SECRET` set

Skip GCE VM steps in the HTML guide for Phase 2.

---

## Test webhook

```bash
curl -X POST "https://bexo-n8n.onrender.com/webhook/bexo-portfolio-generate" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Secret: YOUR_SECRET" \
  -d '{"profileId":"test","buildId":"test","triggered_by":"manual"}'
```

Check n8n → **Executions** for a new run.
