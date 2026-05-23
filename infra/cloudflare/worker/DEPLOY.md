# Deploy portfolio proxy worker

After changing `portfolio-proxy.js`, deploy so `/_next/*` assets are not served as HTML:

```bash
cd infra/cloudflare/worker
npx wrangler deploy
```

Route in Cloudflare dashboard: `*.mybexo.com/*` → `bexo-portfolio-proxy`.

Purge cache after deploy: Cloudflare → Caching → Purge Everything.
