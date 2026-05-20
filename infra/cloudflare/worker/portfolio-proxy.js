/**
 * BEXO portfolio proxy — serve GCS HTML by handle subdomain.
 * Route: *.mybexo.com/*
 * KV binding: HANDLE_MAP (handle → profileId)
 */
/** Public HTML only — see infra/gcp/setup-public-sites-bucket.sh */
const BUCKET = "bexo-sites-public";
const SKIP_HOSTS = new Set(["www", "n8n", "origin", "api", "app"]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const host = url.hostname.toLowerCase();
    const parts = host.split(".");
    if (parts.length < 3) {
      return new Response("Not found", { status: 404 });
    }
    const handle = parts[0];
    if (SKIP_HOSTS.has(handle)) {
      return fetch(request);
    }

    const profileId = await env.HANDLE_MAP.get(handle);
    if (!profileId) {
      return new Response(`Portfolio not found for handle: ${handle}`, { status: 404 });
    }

    const objectPath = `${profileId}/site/index.html`;
    const gcsUrl = `https://storage.googleapis.com/${BUCKET}/${objectPath}`;

    const res = await fetch(gcsUrl, {
      headers: { "Cache-Control": "no-cache" },
    });
    if (!res.ok) {
      return new Response(`Upstream GCS ${res.status} for ${handle}`, { status: 502 });
    }

    const headers = new Headers(res.headers);
    headers.set("Content-Type", "text/html; charset=utf-8");
    headers.set("Cache-Control", "public, max-age=300");
    return new Response(res.body, { status: 200, headers });
  },
};
