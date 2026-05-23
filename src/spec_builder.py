"""
Deterministic portfolio.md from Supabase — no LLM-authored user facts.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from supabase_client import SUPABASE_URL, read_headers

TECH_STACK_TABLE = """| Layer | Technology |
|-------|------------|
| Frontend | Next.js |
| Language | TypeScript |
| UI | React |
| Styling | Tailwind CSS |
| Components | shadcn/ui |
| Animation | Framer Motion |
| Backend (platform) | Node.js + Fastify |
| Database (platform) | PostgreSQL |
| Cache/Queue (platform) | Redis |
| Testing | Playwright |
| Deployment | Docker + GCS + Cloudflare Worker |
| Version Control | GitHub |"""

AGENT_SKILLS = """- frontend-design (mandatory on every build)
- impeccable
- web-design-guidelines
- taste-skill / ui-ux-pro-max / design-motion-principles / emil-design-eng (orchestrator picks from profile)"""

ASSET_SOURCING = """- Use URLs listed under ## Assets first (avatar, project images, resume).
- If a project has no image_url, use a tasteful Unsplash/Pexels placeholder and add attribution in the site footer.
- Never invent employers, schools, or projects not present in this spec."""


def fetch_profile_graph(profile_id: str) -> dict[str, Any]:
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL is required for spec_builder")
    url = (
        f"{SUPABASE_URL}/rest/v1/profiles"
        f"?id=eq.{profile_id}"
        f"&select=*,projects(*),skills(*),experiences(*),education(*)"
    )
    resp = requests.get(url, headers=read_headers(), timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"Supabase fetch failed: {resp.status_code} {resp.text[:400]}")
    rows = resp.json()
    if not rows:
        raise ValueError(f"Profile not found: {profile_id}")
    return rows[0]


def _s(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def build_portfolio_markdown(graph: dict[str, Any]) -> str:
    p = graph
    projects = p.get("projects") or []
    skills = p.get("skills") or []
    experiences = p.get("experiences") or []
    education = p.get("education") or []

    lines: list[str] = [
        "# Identity",
        f"- Name: {_s(p.get('full_name'))}",
        f"- Headline: {_s(p.get('headline'))}",
        f"- Handle: {_s(p.get('handle'))}",
        f"- Location: {_s(p.get('location'))}",
        "",
        "## Personality",
        f"- Tone: professional, approachable",
        f"- Audience: hiring managers and founders",
        f"- Visual mood: {_s(p.get('portfolio_theme') or 'default')}",
        "",
        "## Style",
        f"- Theme: {_s(p.get('portfolio_theme'))}",
        f"- Font: {_s(p.get('portfolio_font'))}",
        f"- Card palette: {_s(p.get('identity_card_palette'))}",
        "",
        "## Tech Stack",
        TECH_STACK_TABLE,
        "",
        "## Agent Skills",
        AGENT_SKILLS,
        "",
        "## Assets",
        f"- Avatar: {_s(p.get('avatar_url')) or '(none)'}",
        f"- Resume: {_s(p.get('resume_url')) or '(none)'}",
        f"- Website: {_s(p.get('website')) or '(none)'}",
        f"- LinkedIn: {_s(p.get('linkedin_url')) or '(none)'}",
        f"- GitHub: {_s(p.get('github_url')) or '(none)'}",
    ]
    for proj in projects:
        img = _s(proj.get("image_url"))
        if img:
            lines.append(f"- Project image ({_s(proj.get('title'))}): {img}")

    lines.extend(["", "## Asset Sourcing", ASSET_SOURCING, "", "## About", _s(p.get("bio")) or "(none)", ""])

    lines.append("## Skills")
    if skills:
        for sk in skills:
            lines.append(f"- {_s(sk.get('name'))} ({_s(sk.get('level') or 'intermediate')})")
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("## Experience")
    if experiences:
        for ex in experiences:
            end = _s(ex.get("end_date")) or ("Present" if ex.get("is_current") else "")
            lines.append(f"### {_s(ex.get('role'))} — {_s(ex.get('company'))}")
            lines.append(f"{_s(ex.get('start_date'))}–{end}")
            if _s(ex.get("description")):
                lines.append(_s(ex.get("description")))
            lines.append("")
    else:
        lines.append("(none)")

    lines.append("## Projects")
    if projects:
        for proj in projects:
            lines.append(f"### {_s(proj.get('title'))}")
            if _s(proj.get("description")):
                lines.append(_s(proj.get("description")))
            tech = proj.get("tech_stack") or []
            if tech:
                lines.append(f"Tech: {', '.join(str(t) for t in tech)}")
            if _s(proj.get("live_url")):
                lines.append(f"Live: {_s(proj.get('live_url'))}")
            if _s(proj.get("github_url")):
                lines.append(f"GitHub: {_s(proj.get('github_url'))}")
            if _s(proj.get("image_url")):
                lines.append(f"Image: {_s(proj.get('image_url'))}")
            lines.append("")
    else:
        lines.append("(none)")

    lines.append("## Education")
    if education:
        for ed in education:
            yr = _s(ed.get("end_year")) or "Present"
            lines.append(f"### {_s(ed.get('degree'))} — {_s(ed.get('institution'))}")
            lines.append(f"{_s(ed.get('field'))} · {_s(ed.get('start_year'))}–{yr}")
            lines.append("")
    else:
        lines.append("(none)")

    lines.extend(
        [
            "## Contact",
            f"- Email: {_s(p.get('email')) or '(obfuscate in UI)'}",
            f"- Phone: {_s(p.get('phone')) or '(none)'}",
            "- CTA: Get in touch",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def build_spec_for_profile(profile_id: str) -> str:
    graph = fetch_profile_graph(profile_id)
    return build_portfolio_markdown(graph)


def upload_spec_to_gcs(profile_id: str, markdown: str) -> None:
    from google.cloud import storage

    bucket_name = os.environ.get("GCS_BUCKET", "bexo-portfolios")
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(f"{profile_id}/portfolio.md")
    blob.upload_from_string(markdown, content_type="text/markdown")
    print(f"[GCS] Spec audit copy → gs://{bucket_name}/{profile_id}/portfolio.md")
