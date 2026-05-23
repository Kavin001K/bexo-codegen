import os
from typing import Any

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _headers(*, prefer: str = "return=minimal") -> dict[str, str]:
    if not SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for site_builds updates")
    h = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def read_headers() -> dict[str, str]:
    """Headers for Supabase REST reads (full row representation)."""
    if not SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")
    return {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }


def update_build(
    build_id: str,
    *,
    status: str | None = None,
    portfolio_url: str | None = None,
    build_log: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    if not SUPABASE_URL or not build_id:
        return
    payload: dict[str, Any] = {}
    if status:
        payload["status"] = status
    if portfolio_url:
        payload["portfolio_url"] = portfolio_url
    if build_log is not None:
        payload["build_log"] = build_log
    if extra:
        payload.update(extra)
    if not payload:
        return
    url = f"{SUPABASE_URL}/rest/v1/site_builds?id=eq.{build_id}"
    resp = requests.patch(url, headers=_headers(), json=payload, timeout=15)
    if resp.status_code >= 400:
        print(f"[Supabase] update_build failed: {resp.status_code} {resp.text[:300]}")
