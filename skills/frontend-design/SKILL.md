# frontend-design (MANDATORY — every BEXO build)

You must apply this skill on **every** portfolio build before writing UI code.

## Bans (generic AI look)

- No Inter, Roboto, Arial, or system-ui-only stacks as the hero voice
- No flat gray-on-white card grids with identical padding on every section
- No purple-gradient-on-white “SaaS template” heroes
- No symmetric three-column feature rows without a narrative reason

## Require

- One clear **visual concept** from `portfolio.md` Style and Personality (e.g. editorial mono, warm brutalist, soft glass, dark terminal)
- **Typographic hierarchy**: display size for name, restrained body, accent for section labels
- **Asymmetric layout** on at least one major section (offset grid, split hero, staggered projects)
- **Color**: tinted neutrals or one dominant accent — not `#666` on `#fff` only
- **Depth**: borders, subtle surface steps, or mesh/gradient background — not flat boxes only

## Implementation (Next.js + Tailwind)

- Edit `workspace/components/PortfolioSite.tsx` and related files
- All copy from `getPortfolioData()` / `data.json` — zero invented employers or projects
- Static export safe: no `next/image` remote patterns that break export unless `unoptimized` is set
- Framer Motion for section reveals — purposeful, not decorative spam

## Done when

- A designer would recognize this as **one person's** site, not a component library demo
- Mobile 375px readable; nav + h1 present; touch targets ≥44px
