# web-design-guidelines

Baseline UX and accessibility audit before finishing edits.

## Must pass

- `<meta name="viewport" content="width=device-width, initial-scale=1">` (in layout)
- `lang="en"` on `<html>` (or profile locale if specified)
- Keyboard: all nav links and CTAs focusable; visible `:focus-visible`
- No `outline: none` without replacement focus style
- Body `overflow-x: hidden` (globals.css)

## Mobile

- No horizontal scroll at 375px width
- Tap targets ≥44×44px
- No tiny text-only links in footer as sole navigation

## Static export

- Do not add server-only APIs or dynamic routes that break `output: 'export'`
