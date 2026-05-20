# Phase 7 — production checklist (no loopholes)

Use this after **https://{handle}.mybexo.com** loads (verified: `kavink.mybexo.com`).

**Reference:** [PORTFOLIO-HOSTING-PLAN.md](PORTFOLIO-HOSTING-PLAN.md) · [BUILD_PROGRESS.md](BUILD_PROGRESS.md)

---

## Verified working (2026-05-20)

| Item | Evidence |
|------|----------|
| Workflow B E2E | n8n execution #17 all green (KV + Supabase done) |
| Public HTML | `curl -sI` → 200 on `bexo-sites-public/.../site/index.html` |
| Live URL | `curl -sI https://kavink.mybexo.com` → HTTP/2 200 |
| Worker + KV | Route `*.mybexo.com/*`, KV `kavink` → profileId |
| Secrets in container | `verify-cloudflare-env.sh` KV PUT success |

---

## Security (do not skip)

| Risk | Mitigation | Status |
|------|------------|--------|
| Webhook A open without secret | `N8N_WEBHOOK_SECRET` + Verify node in Workflow A | Confirm secret is long & not in git |
| Build-done callback spoofing | `BEXO_INTERNAL_SECRET` on Cloud Run + Workflow B | Match GCP `bexo-internal-secret` |
| Cloud Run `/build` abuse | `X-BEXO-Internal-Secret` required | Keep; no public invoker on `/build` |
| Public GCS bucket | Only `bexo-sites-public` is `allUsers` read; **never** put `portfolio.md` there | Private bucket `bexo-portfolios` only |
| Token leaked in chat/terminal | Rotate **Cloudflare API token**, review n8n basic auth password | **Do this** if tokens were pasted anywhere |
| `.env` `#` truncation | Quote values: `CLOUDFLARE_TOKEN="..."` | Fixed on VM |
| Compose overriding `.env` | Do **not** put `CLOUDFLARE_*` under `environment:` in compose | Fixed in repo `docker-compose.micro.yml` |
| n8n behind orange `*` wildcard | Keep **`n8n` DNS record grey cloud (DNS only)** so SSL to VM still works | Verify in Cloudflare DNS |

---

## Infrastructure gaps (fix before Phase 8 scale)

| Gap | Why it matters | Action |
|-----|----------------|--------|
| Cloud Run not redeployed with `GCS_PUBLIC_BUCKET` | New builds only in private bucket until redeploy | `gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod` |
| Full E2E only tested via manual `curl` | App path untested | Phase 8: wire BEXO api-server webhooks |
| Cloud Run → n8n callback | Workflow B must run after **every** real build | Cloud Run logs: `[CALLBACK] n8n 200`; secret `n8n-callback-url` |
| Broken avatar on live site | HTML references images not in public bucket | Future: upload assets to `bexo-sites-public` or use absolute HTTPS URLs |
| GitHub Phase 5 | Optional | Skip unless you need per-repo backups |
| KV test key `_bexo_env_test` | Harmless | Optional delete in Cloudflare KV UI |

---

## DNS / Worker sanity

```bash
# Public HTML
curl -sI "https://storage.googleapis.com/bexo-sites-public/PROFILE_ID/site/index.html" | head -3

# Live subdomain
curl -sI "https://HANDLE.mybexo.com" | head -3

# n8n still up (should NOT be 502 from Worker)
curl -sI "https://n8n.mybexo.com/healthz" | head -3
```

---

## Optional hardening (Phase 9)

- Rate-limit n8n webhooks (nginx or Cloudflare WAF)
- Export n8n workflows weekly to repo
- OpenRouter spend cap / alerts
- Cloud Tasks queue instead of sync webhook chain

---

## Phase 8 entry

See **[PHASE-8-SETUP.md](PHASE-8-SETUP.md)** — wire BEXO app → Workflow A → automatic Workflow B → live URL.
