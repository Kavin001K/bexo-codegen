"""
PortfolioSnapshot v1 — JSON for live site data.json sync.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from spec_builder import fetch_profile_graph


def build_portfolio_snapshot(profile_id: str, graph: dict[str, Any] | None = None) -> dict[str, Any]:
    g = graph or fetch_profile_graph(profile_id)
    return {
        "version": 1,
        "syncedAt": datetime.now(timezone.utc).isoformat(),
        "handle": (g.get("handle") or "").strip().lower(),
        "profile": {
            "full_name": g.get("full_name"),
            "headline": g.get("headline"),
            "bio": g.get("bio"),
            "avatar_url": g.get("avatar_url"),
            "location": g.get("location"),
            "email": g.get("email"),
            "phone": g.get("phone"),
            "website": g.get("website"),
            "linkedin_url": g.get("linkedin_url"),
            "github_url": g.get("github_url"),
            "resume_url": g.get("resume_url"),
        },
        "projects": g.get("projects") or [],
        "skills": g.get("skills") or [],
        "experiences": g.get("experiences") or [],
        "education": g.get("education") or [],
        "theme": {
            "portfolio_theme": g.get("portfolio_theme"),
            "portfolio_font": g.get("portfolio_font"),
            "identity_card_palette": g.get("identity_card_palette"),
            "identity_card_template": g.get("identity_card_template"),
        },
    }
