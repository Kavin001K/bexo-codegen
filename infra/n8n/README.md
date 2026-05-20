# n8n orchestration for BEXO

**Hosting options:**

| Option | Guide | Cost |
|--------|--------|------|
| **GCE e2-micro** (recommended, under $10) | [GCP-UNDER-10.md](./GCP-UNDER-10.md) + [docker-compose.micro.yml](./docker-compose.micro.yml) | ~$6–9/mo |
| **GCE e2-small** (queue + worker) | [docker-compose.yml](./docker-compose.yml) | ~$13/mo |
| **Render.com** | [RENDER.md](./RENDER.md) | ~$14/mo |

Import workflows from `workflows/` in the n8n UI (Settings → Import).

## `$env` blocked in workflows (n8n 1.98+)

If **Verify X-BEXO-Secret** fails with `access to env vars denied`, n8n is blocking `$env` (default since v1.98). On the VM:

```bash
cd ~/bexo-n8n
echo 'N8N_BLOCK_ENV_ACCESS_IN_NODE=false' >> .env   # or fix existing line
# Ensure docker-compose.micro.yml has N8N_BLOCK_ENV_ACCESS_IN_NODE=false under n8n environment:
docker compose -f docker-compose.micro.yml up -d --force-recreate n8n
docker exec bexo-n8n printenv N8N_BLOCK_ENV_ACCESS_IN_NODE   # must print: false
```

Or run `bash fix-n8n-env-access.sh` after copying the latest `docker-compose.micro.yml` from this repo.

**Do not pin n8n to 1.97.x** if Postgres was ever run on 2.x — login fails with `column User.role does not exist`. Stay on **2.20.9** (or newer) and use `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`.

## Workflows

| File | Webhook path | Purpose |
|------|----------------|---------|
| `bexo-portfolio-generate.json` | `/webhook/bexo-portfolio-generate` | Fetch Supabase → AI spec → GCS → trigger Cloud Run |
| `bexo-build-done.json` | `/webhook/bexo-build-done` | DNS + mark `site_builds` done |
| `bexo-rebuild.json` | `/webhook/bexo-rebuild` | Same as generate (manual rebuild) |

## Credentials to configure in n8n

- **Supabase** — URL + service role key
- **OpenRouter** — Header auth `Authorization: Bearer …` (routes DeepSeek + Kimi models)
- Set n8n env: `OPENROUTER_MODEL_SPEC=openrouter/free` (free tier only; see `docs/AI_MODELS.md`)

## Phase 7 — Done

Hosting live via Worker + KV. See **[PHASE-5-7-SETUP.md](PHASE-5-7-SETUP.md)** (complete) and **[docs/PHASE-8-SETUP.md](../../docs/PHASE-8-SETUP.md)** (next).

**VM tip:** Cloudflare vars must come from `env_file` only — see `docker-compose.micro.yml` and `verify-cloudflare-env.sh`.

## n8n down / `Database is not ready` (503)

On the VM:

```bash
cd ~/bexo-n8n
# Copy updated compose + recover script from repo, then:
bash recover-n8n.sh
```

Common causes:

1. **n8n started before Postgres finished** — recover script starts Postgres first, waits, then n8n.
2. **`DB_PASSWORD` changed in `.env`** but Postgres volume still has the old password — restore the original `DB_PASSWORD` (do not run `down -v` unless you accept losing workflows).
3. **e2-micro OOM** — recover script adds 1GB swap.
4. **Old workflow URL** — after re-import, open `https://n8n.mybexo.com/home/workflows` (bookmarks like `/workflow/Qn860060KlTx7LSZ` break).

Wait **2–3 minutes** after `Started` before opening the UI.

Per-task models: see [docs/AI_MODELS.md](../../docs/AI_MODELS.md)
- **Google Cloud Storage** — Service account JSON → [GCS-UPLOAD-SETUP.md](./GCS-UPLOAD-SETUP.md)
- **Google Cloud** — OAuth2 for Cloud Run OIDC (or use HTTP Request with SA token node)

## BEXO api-server

```env
N8N_WEBHOOK_URL=https://n8n.mybexo.com/webhook/bexo-portfolio-generate
N8N_WEBHOOK_SECRET=<same as webhook node expects>
```
