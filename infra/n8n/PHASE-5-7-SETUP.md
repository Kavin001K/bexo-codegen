# Phase 5–7 — Build done + live URLs

> **Status: COMPLETE (2026-05-20)** for MVP hosting.  
> **Security review:** [docs/PHASE-7-PRODUCTION-CHECKLIST.md](../../docs/PHASE-7-PRODUCTION-CHECKLIST.md)  
> **Next:** [docs/PHASE-8-SETUP.md](../../docs/PHASE-8-SETUP.md)

Master guide: [docs/PORTFOLIO-HOSTING-PLAN.md](../../docs/PORTFOLIO-HOSTING-PLAN.md) (Cloudflare Worker + KV — not `origin.mybexo.com` only).

---

## What was built

- Workflow B: callback secret → KV put handle → Supabase `done`
- `gs://bexo-sites-public` public read (HTML only)
- Worker `bexo-portfolio-proxy` + route `*.mybexo.com/*`
- Live test: https://kavink.mybexo.com

---

## VM `.env` (reference)

```env
BEXO_INTERNAL_SECRET=<matches GCP bexo-internal-secret>
CLOUDFLARE_ACCOUNT_ID=78466cfe7312b7a3121264e61d702129
CLOUDFLARE_KV_NAMESPACE_ID=981034d3742e41dca6751cead23be616
CLOUDFLARE_TOKEN="your_api_token"
CLOUDFLARE_ZONE_ID=your_zone_id
PORTFOLIO_DOMAIN=mybexo.com
```

Do **not** set `CDN_ORIGIN_HOST` for the Worker plan.

After editing `.env`:

```bash
cd ~/bexo-n8n
docker compose -f docker-compose.micro.yml up -d --force-recreate n8n
bash verify-cloudflare-env.sh
```

---

## Historical setup steps (archive)

<details>
<summary>Click to expand original checklist</summary>

### Callback URL (GCP)

```bash
bash infra/gcp/setup-phase5-callback.sh
gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod .
```

### Import workflows

Import + publish `bexo-portfolio-generate.json` and `bexo-build-done.json`.

### Test build-done

```bash
INTERNAL=$(gcloud secrets versions access latest --secret=bexo-internal-secret --project=bexo-prod)
curl -X POST "https://n8n.mybexo.com/webhook/bexo-build-done" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Internal-Secret: $INTERNAL" \
  -d '{"profileId":"UUID","buildId":"UUID","handle":"kavink","status":"success","siteUrl":"https://kavink.mybexo.com","buildLog":"test"}'
```

</details>
