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
    """Build portfolio.md from Supabase (source of truth)."""
    from spec_builder import build_spec_for_profile, upload_spec_to_gcs

    md = build_spec_for_profile(profile_id)
    try:
        upload_spec_to_gcs(profile_id, md)
    except Exception as e:
        print(f"[SPEC] GCS audit upload skipped: {e}")
    return md


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


def save_data_json_to_gcs(profile_id: str, snapshot: dict) -> None:
    import json

    body = json.dumps(snapshot, indent=2)
    path = f"{profile_id}/site/data.json"
    cache = "public, max-age=60"
    for bucket_name in (BUCKET, PUBLIC_BUCKET):
        blob = gcs.bucket(bucket_name).blob(path)
        blob.upload_from_string(body, content_type="application/json")
        blob.cache_control = cache
        blob.patch()
        print(f"[GCS] data.json → gs://{bucket_name}/{path}")


def site_index_exists_in_gcs(profile_id: str, bucket_name: str | None = None) -> bool:
    """True when public site index.html exists (Worker serves this path)."""
    bucket = (bucket_name or PUBLIC_BUCKET).strip()
    path = f"{profile_id}/site/index.html"
    return gcs.bucket(bucket).blob(path).exists()


def save_site_dir_to_gcs(profile_id: str, site_dir: str) -> None:
    """Upload Next.js static export directory to GCS."""
    import mimetypes
    from pathlib import Path

    root = Path(site_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Site dir not found: {site_dir}")

    cache = "public, max-age=300"
    for bucket_name in (BUCKET, PUBLIC_BUCKET):
        bucket = gcs.bucket(bucket_name)
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(root).as_posix()
            gcs_path = f"{profile_id}/site/{rel}"
            content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(str(file_path), content_type=content_type)
            blob.cache_control = cache
            blob.patch()
        print(f"[GCS] Site dir uploaded for {profile_id} → gs://{bucket_name}/{profile_id}/site/")
