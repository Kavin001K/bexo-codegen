import os
import traceback

import requests
from flask import Flask, jsonify, request

from generator import fix_website, generate_website, read_portfolio_spec, save_to_gcs
from mobile_safety import inject_mobile_safety
from github_push import push_to_github
from moderation import moderate_text
from supabase_client import update_build
from tester import run_tests

app = Flask(__name__)

MAX_ATTEMPTS = int(os.environ.get("MAX_BUILD_ATTEMPTS", "3"))
N8N_CALLBACK = os.environ.get("N8N_CALLBACK_URL", "")
INTERNAL_SECRET = os.environ.get("BEXO_INTERNAL_SECRET", "")
PORTFOLIO_DOMAIN = os.environ.get("PORTFOLIO_DOMAIN", "mybexo.com")


def _verify_internal_secret() -> bool:
    if not INTERNAL_SECRET:
        return True
    return request.headers.get("X-BEXO-Internal-Secret") == INTERNAL_SECRET


def _notify_n8n(payload: dict) -> None:
    if not N8N_CALLBACK:
        print("[CALLBACK] N8N_CALLBACK_URL not set — skip Workflow B")
        return
    headers = {"Content-Type": "application/json"}
    if INTERNAL_SECRET:
        headers["X-BEXO-Internal-Secret"] = INTERNAL_SECRET
    try:
        resp = requests.post(N8N_CALLBACK, json=payload, headers=headers, timeout=30)
        print(f"[CALLBACK] n8n {resp.status_code} {N8N_CALLBACK}")
        if resp.status_code >= 400:
            print(f"[CALLBACK] body: {resp.text[:400]}")
    except Exception as e:
        print(f"[CALLBACK] n8n notify failed: {e}")


@app.route("/")
def index():
    return jsonify(
        {
            "service": "bexo-codegen",
            "status": "ok",
            "endpoints": {
                "health": "GET /health",
                "build": "POST /build (requires X-BEXO-Internal-Secret)",
            },
        }
    )


@app.route("/health")
def health():
    return {"status": "ok", "service": "bexo-codegen"}


@app.route("/build", methods=["POST"])
def build():
    if not _verify_internal_secret():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    profile_id = data.get("profileId") or data.get("userId")
    build_id = data.get("buildId")
    handle = (data.get("handle") or profile_id or "").strip().lower()

    if not profile_id:
        return jsonify({"error": "profileId required"}), 400
    if not handle:
        return jsonify({"error": "handle required"}), 400

    log_lines: list[str] = []
    site_url = f"https://{handle}.{PORTFOLIO_DOMAIN}"
    repo_url = ""

    try:
        if build_id:
            update_build(build_id, status="building", build_log="Codegen started")

        print(f"[BUILD] Starting profile={profile_id} handle={handle}")
        spec = read_portfolio_spec(profile_id)
        log_lines.append(f"Spec loaded ({len(spec)} chars)")

        mod_issues = moderate_text(spec, "portfolio spec")
        if mod_issues:
            raise ValueError("; ".join(mod_issues))

        html = None
        issues: list = []
        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = generate_website(spec, attempt, issues if attempt > 1 else None)
            html = inject_mobile_safety(result["html"])
            log_lines.append(f"Generated attempt {attempt}")

            mod_html = moderate_text(html, "generated html")
            if mod_html:
                issues = mod_html
            else:
                run_lh = attempt == MAX_ATTEMPTS
                issues = run_tests(html, profile_id, lighthouse=run_lh)

            if not issues:
                log_lines.append("All tests passed")
                break
            log_lines.append(f"Attempt {attempt} issues: {issues[:5]}")
            if attempt < MAX_ATTEMPTS:
                html = inject_mobile_safety(fix_website(html, issues, spec))

        if issues:
            raise RuntimeError(f"Build failed after {MAX_ATTEMPTS} attempts: {issues[:5]}")

        save_to_gcs(profile_id, html)
        log_lines.append(f"GCS site: gs://{os.environ.get('GCS_BUCKET', 'bexo-portfolios')}/{profile_id}/site/index.html")

        repo_url = ""
        if os.environ.get("SKIP_GITHUB_PUSH", "").lower() in ("1", "true", "yes"):
            log_lines.append("GitHub push skipped (SKIP_GITHUB_PUSH)")
        else:
            try:
                repo_url = push_to_github(handle, html, spec, profile_id)
                log_lines.append(f"GitHub: {repo_url}")
            except Exception as gh_err:
                log_lines.append(f"GitHub skipped (non-fatal): {gh_err}")
                print(f"[GITHUB] non-fatal: {gh_err}")

        build_log = "\n".join(log_lines)
        if build_id:
            update_build(
                build_id,
                status="building",
                portfolio_url=site_url,
                build_log=build_log,
            )

        payload = {
            "profileId": profile_id,
            "buildId": build_id,
            "handle": handle,
            "status": "success",
            "siteUrl": site_url,
            "repoUrl": repo_url,
            "issues": [],
            "error": None,
            "buildLog": build_log,
        }
        _notify_n8n(payload)
        return jsonify(payload)

    except Exception as e:
        traceback.print_exc()
        err = str(e)
        build_log = "\n".join(log_lines + [f"ERROR: {err}"])
        if build_id:
            update_build(build_id, status="failed", build_log=build_log)
        payload = {
            "profileId": profile_id,
            "buildId": build_id,
            "handle": handle,
            "status": "error",
            "siteUrl": site_url,
            "repoUrl": repo_url,
            "issues": [],
            "error": err,
            "buildLog": build_log,
        }
        _notify_n8n(payload)
        return jsonify(payload), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
