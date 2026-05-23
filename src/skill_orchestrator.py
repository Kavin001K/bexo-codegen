"""
Select design/UX skills for Claude Code from profile + portfolio.md.
Every production build uses the premium pipeline (image direction → code) on
Next.js + React + Tailwind + TypeScript static export.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".claude" / "skills"
FALLBACK_SKILLS_DIR = ROOT / "skills"

MANDATORY_SKILLS = ("frontend-design",)

# Ordered pipeline — Claude must invoke Skill tool in this order on every build
BUILD_PIPELINE = (
    "stitch-design-taste",
    "imagegen-frontend-web",
    "frontend-design",
    "image-to-code",
)

# Always-on supporting skills (after pipeline)
DEFAULT_OPTIONAL = ("impeccable", "web-design-guidelines")

# Optional skills the orchestrator may add (never replaces mandatory set)
OPTIONAL_SKILL_CATALOG = {
    "brandkit": {
        "triggers": (
            "brand",
            "logo",
            "identity",
            "luxury",
            "premium",
            "creative",
            "distinctive",
        ),
        "reason": "Brand board and visual identity before section comps",
    },
    "high-end-visual-design": {
        "triggers": (
            "agency",
            "expensive",
            "polish",
            "shadow",
            "editorial",
            "premium",
        ),
        "reason": "Agency-level spacing, shadows, and typography",
    },
    "design-taste-frontend": {
        "triggers": (
            "editorial",
            "asymmetric",
            "bento",
            "bold",
            "distinctive",
        ),
        "reason": "Editorial / anti-generic layout direction",
    },
    "taste-skill": {
        "triggers": (
            "editorial",
            "asymmetric",
            "luxury",
            "minimal",
            "bold",
            "creative",
            "distinctive",
        ),
        "reason": "Editorial / anti-generic layout direction in spec",
    },
    "minimalist-ui": {
        "triggers": ("minimal", "clean", "editorial", "monochrome", "calm"),
        "reason": "Warm monochrome editorial sections",
    },
    "industrial-brutalist-ui": {
        "triggers": (
            "brutalist",
            "industrial",
            "terminal",
            "data",
            "dashboard",
            "mechanical",
        ),
        "reason": "Swiss grid / terminal accents for data-heavy profiles",
    },
    "redesign-existing-projects": {
        "triggers": ("redesign", "upgrade", "refresh", "modernize"),
        "reason": "Upgrade template away from generic AI patterns",
    },
    "impeccable": {
        "triggers": ("polish", "accessibility", "a11y", "refine", "professional"),
        "reason": "Polish spacing, contrast, and accessibility",
    },
    "ui-ux-pro-max": {
        "triggers": (
            "startup",
            "saas",
            "product",
            "developer",
            "engineer",
            "tech",
            "data",
        ),
        "reason": "Industry-appropriate palette and component patterns",
    },
    "design-motion-principles": {
        "triggers": (
            "motion",
            "animation",
            "playful",
            "dynamic",
            "framer",
            "interactive",
        ),
        "reason": "Spring-based motion and entrance choreography",
    },
    "web-design-guidelines": {
        "triggers": tuple(),
        "reason": "Baseline keyboard nav, focus, and viewport compliance",
        "always_after_qa": False,
    },
    "emil-design-eng": {
        "triggers": ("delight", "micro", "premium", "craft", "detail"),
        "reason": "Micro-interactions and tactile UI polish",
    },
}


def _skill_md_path(name: str) -> Path | None:
    for base in (SKILLS_DIR, FALLBACK_SKILLS_DIR):
        path = base / name / "SKILL.md"
        if path.is_file():
            return path
    return None


def _spec_blob(spec: str, snapshot: dict[str, Any]) -> str:
    profile = snapshot.get("profile") or {}
    parts = [
        spec.lower(),
        (profile.get("headline") or "").lower(),
        (profile.get("bio") or "").lower(),
    ]
    style = re.search(r"##\s*style[^\n]*\n([\s\S]*?)(?=\n##|\Z)", spec, re.I)
    if style:
        parts.append(style.group(1).lower())
    return " ".join(parts)


def select_skills(spec: str, snapshot: dict[str, Any]) -> list[str]:
    """Return ordered skill ids: pipeline first, then profile-triggered extras."""
    blob = _spec_blob(spec, snapshot)
    chosen: list[str] = []

    for name in BUILD_PIPELINE:
        if name not in chosen and _skill_md_path(name):
            chosen.append(name)
        elif name in MANDATORY_SKILLS and name not in chosen:
            chosen.append(name)

    for name in MANDATORY_SKILLS:
        if name not in chosen:
            chosen.append(name)

    for name in DEFAULT_OPTIONAL:
        if name not in chosen and _skill_md_path(name):
            chosen.append(name)

    for name, meta in OPTIONAL_SKILL_CATALOG.items():
        if name in chosen:
            continue
        if not _skill_md_path(name):
            continue
        triggers = meta.get("triggers") or ()
        if any(t in blob for t in triggers):
            chosen.append(name)

    project_count = len(snapshot.get("projects") or [])
    if project_count >= 3 and "design-taste-frontend" not in chosen:
        if _skill_md_path("design-taste-frontend"):
            chosen.append("design-taste-frontend")
    if project_count >= 2 and "design-motion-principles" not in chosen:
        if any(w in blob for w in ("motion", "animation", "framer", "dynamic")):
            if _skill_md_path("design-motion-principles"):
                chosen.append("design-motion-principles")

    return chosen


def load_skill_excerpt(name: str, max_chars: int = 1200) -> str:
    path = _skill_md_path(name)
    if not path:
        return f"- **{name}**: (skill file missing — use project conventions)\n"
    limit = 2400 if name in BUILD_PIPELINE else max_chars
    text = path.read_text(encoding="utf-8")
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return f"### Skill: {name}\n{text}\n"


def build_claude_system_append(
    spec: str,
    snapshot: dict[str, Any],
    *,
    phase: str = "build",
    qa_issues: list[str] | None = None,
) -> str:
    skills = select_skills(spec, snapshot)
    if phase == "fix" and "impeccable" not in skills:
        skills.append("impeccable")

    lines = [
        "## BEXO orchestrator (Cloud Run + Claude Code)",
        "",
        "### Tech stack (non-negotiable)",
        "- **Next.js** App Router, **React 18**, **TypeScript**, **Tailwind CSS**",
        "- **Framer Motion** for motion (already in template)",
        "- **Static export only** (`output: 'export'`) — no API routes, no SSR data fetching",
        "- User content only via `getPortfolioData()` reading `public/data.json`",
        "",
        "### Planning (do this before editing files)",
        "1. Read `portfolio.md` and `workspace/public/data.json` — facts only from these sources.",
        "2. Invoke the **Skill** tool for each skill below **in listed order**. Do not skip steps.",
        "3. **imagegen-frontend-web**: one horizontal comp per section from `portfolio.md` when image tools exist; if unavailable, derive layout from spec + stitch tokens and state that in one line.",
        "4. **image-to-code**: implement `./workspace` to match comps or spec; no generic three-column card grids.",
        "5. Map sections to `portfolio.md` order; keep static export and `getPortfolioData()` pattern.",
        "6. Do not run `npm install` or `npm run build` — the Python orchestrator compiles after you finish.",
        "",
        f"### Active skills ({phase} phase) — invoke in order",
        ", ".join(f"`{s}`" for s in skills),
        "",
    ]
    for skill in skills:
        lines.append(load_skill_excerpt(skill))

    if qa_issues:
        lines.extend(
            [
                "### QA failures to fix",
                *[f"- {i}" for i in qa_issues[:12]],
                "",
            ]
        )

    lines.extend(
        [
            "### Quality bar (unique, professional, optimized)",
            "- Distinct layout metaphor from **Style and Personality** — not a template clone.",
            "- Prefer server components + static HTML; client islands only for motion.",
            "- Minimize DOM depth; no nested card-in-card grids without hierarchy.",
            "- 8px spacing rhythm; touch targets ≥44px; `overflow-x: hidden` on body.",
            "- Semantic `<h1>`, `<nav>` with matching section `id`s; Lighthouse-friendly static assets.",
            "",
        ]
    )
    return "\n".join(lines)


def skills_for_health() -> dict:
    """Health/debug: which skills are on disk."""
    all_names = set(MANDATORY_SKILLS) | set(BUILD_PIPELINE) | set(DEFAULT_OPTIONAL)
    all_names |= set(OPTIONAL_SKILL_CATALOG)
    found = []
    missing = []
    for name in sorted(all_names):
        if _skill_md_path(name):
            found.append(name)
        else:
            missing.append(name)
    return {
        "mandatory": list(MANDATORY_SKILLS),
        "pipeline": list(BUILD_PIPELINE),
        "found": found,
        "missing": missing,
    }
