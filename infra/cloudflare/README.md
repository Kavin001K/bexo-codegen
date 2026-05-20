# Cloudflare Worker — portfolio sites

See **[docs/PORTFOLIO-HOSTING-PLAN.md](../../docs/PORTFOLIO-HOSTING-PLAN.md)** for the full simple checklist.

## Quick deploy

```bash
cd infra/cloudflare/worker
# Edit wrangler.toml — set KV namespace id
npx wrangler login
npx wrangler deploy
```

Add route in dashboard: `*.mybexo.com/*` → `bexo-portfolio-proxy`.
