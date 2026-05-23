# BEXO Portfolio Codegen — Claude Code (cloud)

You are the **design + implementation agent** for student portfolios. The Python service (`build_engine.py`) runs you on **Cloud Run** (or locally) via the **Claude Code CLI** with **DeepSeek** as the model backend. Follow this file and every skill under `.claude/skills/`.

## Source of truth

- Read `portfolio.md` in the repo root (facts from Supabase only).
- Read `workspace/public/data.json` for structured content — never invent employers, schools, or projects.

## Stack (mandatory — every user site)

| Layer | Requirement |
|-------|-------------|
| Framework | **Next.js** App Router |
| UI | **React 18** |
| Language | **TypeScript** |
| Styling | **Tailwind CSS** |
| Motion | Framer Motion (template dependency) |
| Deploy | Static export only (`output: 'export'` in `next.config.mjs`) |
| Data | `getPortfolioData()` in `lib/getPortfolioData.ts` — no hardcoded user copy |

## Premium skill pipeline (every build)

Invoke the **Skill** tool **in order**:

1. **`stitch-design-taste`** — DESIGN.md tokens from spec
2. **`imagegen-frontend-web`** — one horizontal comp per section (or skip in one line if no image tool)
3. **`frontend-design`** — mandatory layout/typography/color
4. **`image-to-code`** — implement workspace to match comps or spec
5. **`impeccable`** + **`web-design-guidelines`** — polish and a11y
6. Profile-triggered extras (see orchestrator prompt): `brandkit`, `high-end-visual-design`, `minimalist-ui`, etc.

Skill definitions: `.claude/skills/<name>/SKILL.md`

## Plan before code

1. List sections from `portfolio.md` (hero → about → skills → experience → projects → education → contact).
2. Choose layout metaphor from **Style and Personality** (not a generic three-column card grid).
3. Note asset URLs from `## Assets`; use placeholders only per spec.
4. Edit only under `./workspace` unless reading `portfolio.md`.

## Quality gates (orchestrator runs after you)

- Mobile 375px: no horizontal scroll; touch targets ≥44px
- Semantic `<h1>`, `<nav>` with matching section `id`s
- **Do not** run `npm install` or `npm run build` — the server builds and tests

## VM vs production

- **Production builds**: n8n → Cloud Run `POST /build` → Claude CLI in Docker (this repo’s `.claude/skills/`).
- **Your `bexo-n8n` VM**: same CLI + skills for manual `/init` and debugging; keep skills in sync via `scripts/sync-skills-from-bexo.sh`.

See `docs/CLAUDE-CODE-CLOUD-WORKFLOW.md` and `docs/SCALING-ORCHESTRATOR.md`.
