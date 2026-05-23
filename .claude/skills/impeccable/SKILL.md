# impeccable — visual QC and polish

Apply after layout direction is set (run after `frontend-design`).

## Polish checklist

- 8px spacing rhythm; consistent `gap-*` within sections
- Contrast: body text readable on background (WCAG-minded, not washed out)
- Focus states visible on nav and CTAs (`focus-visible:ring-*`)
- No text smaller than 14px on mobile for primary content
- Images: `alt` text, `max-w-full`, no layout shift from missing dimensions where possible

## Quiet / balance

- If more than two accent colors, reduce to one
- If more than three font sizes in a section, simplify hierarchy

## Accessibility

- Single `<h1>`; logical heading order
- `<nav aria-label="Primary navigation">` with working `#section` anchors
- Touch targets ≥44px on all interactive elements
