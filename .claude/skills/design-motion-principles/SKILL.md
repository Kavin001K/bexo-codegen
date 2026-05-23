# design-motion-principles

Use when the portfolio should feel alive (Framer Motion already in template).

## Physics

- Prefer **spring** transitions (`type: "spring", stiffness ~ 120, damping ~ 20`) over linear >300ms
- Stagger children in project grids (`staggerChildren: 0.08`)
- `viewport={{ once: true }}` on scroll reveals — no infinite re-triggers

## Patterns

- Hero: opacity + y (12–16px), not scale bounces
- Section enter: use existing `Section` wrapper pattern in `PortfolioSite.tsx`
- Hover: subtle `y: -4` on project cards max — no 3D flips

## Avoid

- Parallax on mobile
- Animating layout properties that cause reflow (width, height) on every frame
- Missing `AnimatePresence` when conditionally mounting nav items or tabs
