import os
import re

from google.cloud import storage

from llm_client import complete

gcs = storage.Client()
BUCKET = os.environ.get("GCS_BUCKET", "bexo-portfolios")
PUBLIC_BUCKET = os.environ.get("GCS_PUBLIC_BUCKET", "bexo-sites-public")

SYSTEM = """You are an elite frontend engineer specialising in portfolio websites.
Given a portfolio.md spec, output ONE complete production-ready HTML file.
RULES:
- Output ONLY raw HTML. Start with <!DOCTYPE html>. Zero explanations or markdown fences.
- Embed ALL CSS in <style>. Embed ALL JS in <script> at bottom.
- Mobile-first from 320px. MUST pass on 375px width: no horizontal scroll (use box-sizing:border-box, max-width:100% on media, overflow-x:hidden on body).
- Every link and button MUST be at least 44x44px touch target (min-height/min-width 44px, adequate padding).
- No fixed pixel widths wider than 100vw. Flex/grid layouts that wrap on small screens.
- Sections: hero, about, skills, projects, contact — follow spec section order when given.
- Use CSS custom properties. Match spec colors exactly. Google Fonts via @import when named.
- Use spec asset URLs for avatar and project images when provided.
- Contact form: name, email, message with client-side validation (no backend).
- HTML5 semantic: nav, main, section, footer, ARIA roles, alt on all imgs.
- lang attribute on html. Viewport meta. Keep scripts lightweight for Lighthouse.
"""

FIX_SYSTEM = """You fix portfolio HTML to pass automated QA tests.
MUST fix every listed issue. Return ONLY the complete fixed HTML file.
Critical: body { overflow-x: hidden }, all images max-width 100%, every a/button min 44x44px.
"""


def read_portfolio_spec(profile_id: str) -> str:
    bucket = gcs.bucket(BUCKET)
    blob = bucket.blob(f"{profile_id}/portfolio.md")
    return blob.download_as_text()


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```[\w]*\n?", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)
    return text.strip()


def generate_website(spec: str, attempt: int = 1, prev_issues: list | None = None) -> dict:
    extra = ""
    if prev_issues:
        extra = "\n\nPREVIOUS ATTEMPT FAILED. Fix ALL:\n" + "\n".join(f"- {i}" for i in prev_issues)

    # Attempt 1: Kimi K2 (quality). Retries use DeepSeek fix path separately.
    task = "generate" if attempt == 1 else "fix"
    content = complete(
        task,
        [{"role": "user", "content": f"Build the portfolio from this spec:\n\n{spec}{extra}\n\nAttempt {attempt}."}],
        system=SYSTEM,
        max_tokens=int(os.environ.get("MAX_OUTPUT_TOKENS", "4096")),
    )
    html = _strip_fences(content)
    return {"html": html, "tokens_used": 0}


def fix_website(html: str, issues: list, spec: str) -> str:
    issues_str = "\n".join(f"- {i}" for i in issues)
    content = complete(
        "fix",
        [
            {
                "role": "user",
                "content": f"""Fix these issues in the portfolio website:

ISSUES:
{issues_str}

SPEC:
{spec}

CURRENT HTML:
{html}

Return ONLY the fixed complete HTML file.""",
            }
        ],
        system=FIX_SYSTEM,
        max_tokens=int(os.environ.get("MAX_OUTPUT_TOKENS", "4096")),
    )
    return _strip_fences(content)


def save_to_gcs(profile_id: str, html: str) -> None:
    path = f"{profile_id}/site/index.html"
    cache = "public, max-age=300"

    for bucket_name in (BUCKET, PUBLIC_BUCKET):
        blob = gcs.bucket(bucket_name).blob(path)
        blob.upload_from_string(html, content_type="text/html")
        blob.cache_control = cache
        blob.patch()
        print(f"[GCS] Saved site for {profile_id} → gs://{bucket_name}/{path}")
