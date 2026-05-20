# Portfolio hosting — `CDN_ORIGIN_HOST`

Workflow B creates:

```text
{handle}.mybexo.com  CNAME →  CDN_ORIGIN_HOST  (proxied)
```

Codegen writes HTML to:

```text
gs://bexo-portfolios/{profileId}/site/index.html
```

You need an **origin** at `CDN_ORIGIN_HOST` that serves the right file per hostname (or per path).

## Option A — Cloudflare Worker (recommended for MVP)

1. Create Worker route: `*.{zone}/*` or `*.mybexo.com/*`
2. Worker reads `Host` header (`handle.mybexo.com`), maps handle → GCS path
3. Fetch `https://storage.googleapis.com/bexo-portfolios/{profileId}/site/index.html`

Mapping handle → profileId:

- Supabase lookup, or
- KV store updated on build complete, or
- Use profileId in subdomain: `{profileId}.mybexo.com` (less pretty)

Set `CDN_ORIGIN_HOST` to a dummy target if Worker handles all traffic on proxied orange-cloud records — for CNAME-only automation, point to your Worker custom domain or LB hostname documented in Cloudflare.

## Option B — HTTPS load balancer + backend bucket

1. Backend bucket → `bexo-portfolios` with URL map by host
2. Global external HTTPS LB IP
3. `CDN_ORIGIN_HOST` = `origin.mybexo.com` A record → LB IP

More setup; best for production scale.

## Option C — GitHub Pages / Actions only

If using GitHub deploy workflow per repo, origin may be `github.io` — not aligned with current GCS-first pipeline unless Actions upload runs.

## Current pipeline default

Codegen saves to **GCS**; Workflow B only creates DNS. Until origin serves GCS objects, `https://{handle}.mybexo.com` may 404 even when Supabase shows `done`.

**Minimum test without full CDN:** confirm `gsutil cat gs://bexo-portfolios/{profileId}/site/index.html` and Supabase `portfolio_url`.
