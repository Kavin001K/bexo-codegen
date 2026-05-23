"""Inject mobile layout fixes so free-tier LLM output passes Playwright gates."""

MOBILE_SAFETY_CSS = """
/* BEXO auto-injected mobile safety */
*, *::before, *::after { box-sizing: border-box; }
html, body {
  overflow-x: hidden !important;
  max-width: 100vw;
  width: 100%;
}
main, section, header, footer, nav, .container, [class*="container"] {
  max-width: 100%;
  overflow-x: hidden;
}
img, video, iframe, svg, table, pre, canvas {
  max-width: 100% !important;
  height: auto;
}
a, button, [role="button"], input[type="submit"], input[type="button"], .btn {
  min-height: 44px !important;
  min-width: 44px !important;
  padding: 0.5rem 0.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
nav a, .nav a, .nav-link {
  min-height: 44px !important;
  padding: 0.75rem 1rem;
}
"""

MARKER = "bexo-mobile-safety"


def inject_mobile_safety(html: str) -> str:
    if MARKER in html:
        return html
    block = f'<style id="{MARKER}">\n{MOBILE_SAFETY_CSS}\n</style>'
    lower = html.lower()
    head_end = lower.find("</head>")
    if head_end != -1:
        return html[:head_end] + block + html[head_end:]
    return block + html


def inject_mobile_safety_to_site_dir(site_dir: str) -> int:
    """Inject touch-target CSS into every HTML file in a Next static export."""
    from pathlib import Path

    count = 0
    for path in Path(site_dir).rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        patched = inject_mobile_safety(text)
        if patched != text:
            path.write_text(patched, encoding="utf-8")
            count += 1
    if count:
        print(f"[MOBILE] Injected safety CSS into {count} HTML file(s)")
    return count
