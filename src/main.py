import os
import traceback

import requests
from flask import Flask, jsonify, request

from build_engine import run_build
from generator import site_index_exists_in_gcs
from skill_orchestrator import skills_for_health
from supabase_client import update_build

app = Flask(__name__)

N8N_CALLBACK = os.environ.get("N8N_CALLBACK_URL", "")
CODEGEN_ENGINE = os.environ.get("CODEGEN_ENGINE", "claude")
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


def _health_payload() -> dict:
    return {
        "service": "bexo-codegen",
        "status": "ok",
        "engine": CODEGEN_ENGINE,
        "llm": {
            "primary": os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro[1m]"),
            "fix": os.environ.get("KIMI_MODEL", "moonshotai/kimi-k2"),
        },
        "skills": skills_for_health(),
        "endpoints": {
            "health": "GET /health",
            "build": "POST /build (requires X-BEXO-Internal-Secret)",
        },
    }


@app.route("/", methods=["GET"])
def index():
    return jsonify(_health_payload())


@app.route("/health")
def health():
    return jsonify(_health_payload())


@app.route("/build", methods=["POST"])
@app.route("/", methods=["POST"])
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

        print(f"[BUILD] Starting profile={profile_id} handle={handle} engine={CODEGEN_ENGINE}")
        log_lines.extend(run_build(profile_id, handle))

        if not site_index_exists_in_gcs(profile_id):
            raise RuntimeError(
                f"Build finished but gs://bexo-sites-public/{profile_id}/site/index.html is missing"
            )

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
