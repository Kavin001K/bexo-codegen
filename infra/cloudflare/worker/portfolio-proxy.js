/**
 * BEXO portfolio proxy — serve GCS static Next export by handle subdomain.
 * Route: *.mybexo.com/*
 * KV binding: HANDLE_MAP (handle → profileId)
 */
const BUCKET = "bexo-sites-public";
const SKIP_HOSTS = new Set([
  "www",
  "n8n",
  "origin",
  "api",
  "app",
  "backend",
  "assets",
  "assect", // legacy typo — must bypass portfolio router; point DNS to R2 custom domain
]);

function hasFileExtension(pathname) {
  return /\.[a-zA-Z0-9]+$/.test(pathname);
}

function isNextAsset(pathname) {
  return pathname.startsWith("/_next/") || pathname.startsWith("/static/");
}

function resolveObjectPath(profileId, pathname) {
  const base = `${profileId}/site`;
  let path = pathname || "/";
  if (path.endsWith("/")) path += "index.html";
  if (path === "/") path = "/index.html";
  if (path.startsWith("/")) path = path.slice(1);
  return `${base}/${path}`;
}

function contentTypeForPath(pathname) {
  const ext = pathname.split(".").pop()?.toLowerCase() ?? "";
  const types = {
    html: "text/html; charset=utf-8",
    css: "text/css; charset=utf-8",
    js: "application/javascript; charset=utf-8",
    json: "application/json; charset=utf-8",
    txt: "text/plain; charset=utf-8",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    webp: "image/webp",
    svg: "image/svg+xml",
    woff2: "font/woff2",
    ico: "image/x-icon",
  };
  return types[ext] || null;
}

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

    let objectPath = resolveObjectPath(profileId, url.pathname);
    let gcsUrl = `https://storage.googleapis.com/${BUCKET}/${objectPath}`;

    let res = await fetch(gcsUrl, { headers: { "Cache-Control": "no-cache" } });

    // SPA fallback only for extensionless page routes — never for /_next/* or .css/.js/etc.
    const allowSpaFallback =
      !isNextAsset(url.pathname) && !hasFileExtension(url.pathname);
    if (res.status === 404 && allowSpaFallback) {
      objectPath = resolveObjectPath(profileId, "/index.html");
      gcsUrl = `https://storage.googleapis.com/${BUCKET}/${objectPath}`;
      res = await fetch(gcsUrl, { headers: { "Cache-Control": "no-cache" } });
    }

    if (!res.ok) {
      const hint =
        res.status === 404
          ? " Site not built yet — trigger portfolio generate in the app and wait for build to finish."
          : "";
      return new Response(
        `Upstream GCS ${res.status} for ${handle} (${objectPath}).${hint}`,
        { status: res.status === 404 ? 404 : 502 },
      );
    }

    const headers = new Headers(res.headers);
    const typed = contentTypeForPath(url.pathname);
    if (typed) headers.set("Content-Type", typed);
    headers.set(
      "Cache-Control",
      url.pathname.endsWith("data.json")
        ? "public, max-age=60"
        : "public, max-age=300"
    );

    return new Response(res.body, { status: 200, headers });
  },
};
