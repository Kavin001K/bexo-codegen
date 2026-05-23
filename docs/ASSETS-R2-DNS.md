# Avatar / file URLs (`assect.mybexo.com` or `assets.mybexo.com`)

## Problem

`https://assect.mybexo.com/kavin/avatar.jpg` shows **Portfolio not found for handle: assect** because the wildcard Worker treated `assect` as a portfolio handle.

## Fix (two parts)

### 1. Redeploy portfolio Worker (skip asset hosts)

```bash
cd bexo-codegen/infra/cloudflare/worker
npx wrangler deploy
```

`assect` and `assets` are in `SKIP_HOSTS` so traffic passes to **origin** (not GCS portfolios).

### 2. Point subdomain at R2 (Cloudflare dashboard)

1. **R2** → your BEXO bucket → **Settings** → **Public access** / **Custom domains**
2. Attach **`assect.mybexo.com`** (or rename to **`assets.mybexo.com`** and update env)
3. Ensure DNS record exists (often auto-created when you connect custom domain)

### 3. Render api-server env

Set **`R2_PUBLIC_URL`** to the same public base URL R2 gives you, e.g.:

- `https://pub-xxxxxxxx.r2.dev` (simplest — no custom subdomain), or
- `https://assect.mybexo.com` after R2 custom domain is live

Wrong: leaving `R2_PUBLIC_URL` unset while using a random `*.mybexo.com` host that still routes through the portfolio Worker.

Re-upload avatar in the app after changing `R2_PUBLIC_URL` so Supabase gets the new URL.
