"""
Portfolio build engines: Claude Code + Next static export, or legacy Python HTML.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from generator import (
    fix_website,
    generate_website,
    read_portfolio_spec,
    save_data_json_to_gcs,
    save_site_dir_to_gcs,
    save_to_gcs,
)
from github_push import push_site_to_github
from mobile_safety import inject_mobile_safety, inject_mobile_safety_to_site_dir
from moderation import moderate_text
from skill_orchestrator import build_claude_system_append, select_skills
from snapshot_builder import build_portfolio_snapshot
from spec_builder import fetch_profile_graph
from tester import run_site_tests, run_tests

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / "templates" / "portfolio-next"
WORKSPACE_ROOT = ROOT / "workspace"
PROMPTS_DIR = ROOT / "prompts"


def _rmtree_force(path: Path) -> None:
    """Remove workspace tree; tolerate Cloud Run concurrent/racy deletes."""
    if not path.exists():
        return
    shutil.rmtree(path, ignore_errors=True)
    if path.exists():
        shutil.rmtree(path)


def _engine() -> str:
    return os.environ.get("CODEGEN_ENGINE", "claude").strip().lower()


def _run_cmd(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> None:
    merged = {**os.environ, **(env or {})}
    print(f"[CMD] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=merged, check=True)


def _write_data_json(workspace: Path, snapshot: dict) -> None:
    (workspace / "public" / "data.json").write_text(
        json.dumps(snapshot, indent=2), encoding="utf-8"
    )


def _prepare_workspace(profile_id: str, spec: str, snapshot: dict) -> Path:
    workspace = WORKSPACE_ROOT / profile_id
    _rmtree_force(workspace)
    shutil.copytree(TEMPLATE_DIR, workspace)

    (ROOT / "portfolio.md").write_text(spec, encoding="utf-8")
    _write_data_json(workspace, snapshot)
    return workspace


def _llm_env(phase: str = "primary") -> dict[str, str]:
    """
    Build env vars for Claude Code (Anthropic-compatible API shape).

    phase=primary → DeepSeek (GCP secret deepseek-api-key)
    phase=fix     → Kimi via OpenRouter (GCP secret kimi-api-key), else DeepSeek
    Fallback: OPENROUTER_API_KEY if primary keys missing
    """
    env: dict[str, str] = {}

    deepseek_key = (
        os.environ.get("ANTHROPIC_AUTH_TOKEN")
        or os.environ.get("DEEPSEEK_API_KEY", "")
    ).strip()
    kimi_key = os.environ.get("KIMI_API_KEY", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    if phase == "fix" and kimi_key:
        model = os.environ.get("KIMI_MODEL", "moonshotai/kimi-k2").strip()
        env["ANTHROPIC_BASE_URL"] = os.environ.get(
            "KIMI_ANTHROPIC_BASE_URL", "https://openrouter.ai/api"
        ).strip()
        env["ANTHROPIC_AUTH_TOKEN"] = kimi_key
        env["ANTHROPIC_API_KEY"] = kimi_key
        env["ANTHROPIC_MODEL"] = model
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
        print(f"[LLM] fix phase → OpenRouter/Kimi model={model}")
        return env

    if deepseek_key:
        base = os.environ.get(
            "DEEPSEEK_ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic"
        ).strip()
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro[1m]").strip()
        fast = os.environ.get("DEEPSEEK_MODEL_FAST", "deepseek-v4-flash").strip()
        env["ANTHROPIC_BASE_URL"] = base
        env["ANTHROPIC_AUTH_TOKEN"] = deepseek_key
        env["ANTHROPIC_API_KEY"] = deepseek_key
        env["ANTHROPIC_MODEL"] = model
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = fast
        env["CLAUDE_CODE_SUBAGENT_MODEL"] = os.environ.get(
            "CLAUDE_CODE_SUBAGENT_MODEL", fast
        ).strip()
        env["CLAUDE_CODE_EFFORT_LEVEL"] = os.environ.get(
            "CLAUDE_CODE_EFFORT_LEVEL", "max"
        ).strip()
        print(f"[LLM] primary phase → DeepSeek model={model}")
        return env

    if openrouter_key:
        model = os.environ.get(
            "OPENROUTER_MODEL_GENERATE", "deepseek/deepseek-chat"
        ).strip()
        env["ANTHROPIC_BASE_URL"] = os.environ.get(
            "OPENROUTER_ANTHROPIC_BASE_URL", "https://openrouter.ai/api"
        ).strip()
        env["ANTHROPIC_AUTH_TOKEN"] = openrouter_key
        env["ANTHROPIC_API_KEY"] = openrouter_key
        env["ANTHROPIC_MODEL"] = model
        env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model
        env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model
        env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model
        print("[LLM] primary phase → OpenRouter fallback")
        return env

    raise RuntimeError(
        "No LLM API key configured. Set deepseek-api-key and/or kimi-api-key in GCP Secret Manager."
    )


def _invoke_claude(
    prompt_file: str,
    *,
    workspace: Path,
    phase: str = "primary",
    spec: str = "",
    snapshot: dict | None = None,
    qa_issues: list[str] | None = None,
) -> bool:
    """Run Claude Code; return False on skip/failure (build continues with template)."""
    prompt = (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
    claude_bin = os.environ.get("CLAUDE_BIN", "claude")
    skip = os.environ.get("SKIP_CLAUDE", "").lower() in ("1", "true", "yes")
    if skip:
        print("[CLAUDE] SKIP_CLAUDE set — using template only")
        return False
    llm_env = _llm_env(phase)
    llm_env.setdefault("CI", "true")
    llm_env.setdefault("TERM", "dumb")
    llm_env.setdefault("CLAUDE_CODE_MAX_TURNS", os.environ.get("CLAUDE_CODE_MAX_TURNS", "20"))
    merged = {**os.environ, **llm_env}
    phase_name = "fix" if phase == "fix" else "build"
    system_append = ""
    if spec and snapshot is not None:
        skills = select_skills(spec, snapshot)
        print(f"[SKILLS] {phase_name}: {', '.join(skills)}")
        system_append = build_claude_system_append(
            spec, snapshot, phase=phase_name, qa_issues=qa_issues
        )
    cmd = [
        claude_bin,
        "-p",
        prompt,
        "--allowedTools",
        "Edit,Bash,Write,Skill",
        "--add-dir",
        str(workspace),
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--permission-mode",
        "bypassPermissions",
    ]
    if system_append:
        cmd.extend(["--append-system-prompt", system_append])
    print(f"[CMD] {' '.join(cmd[:4])} ...")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=merged,
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("CLAUDE_TIMEOUT_SEC", "480")),
        )
    except FileNotFoundError:
        print("[CLAUDE] claude CLI not found — using template only")
        return False
    except subprocess.TimeoutExpired:
        print("[CLAUDE] timed out — using template only")
        return False
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[-2500:]
        print(f"[CLAUDE] exit {result.returncode}")
        if tail:
            print(tail)
        return False
    if result.stdout.strip():
        print(f"[CLAUDE] ok ({len(result.stdout)} chars output)")
    return True


def _npm_build(workspace: Path, profile_id: str) -> Path:
    public_bucket = os.environ.get("GCS_PUBLIC_BUCKET", "bexo-sites-public").strip()
    asset_prefix = (
        f"https://storage.googleapis.com/{public_bucket}/{profile_id}/site"
    )
    build_env = {
        "NEXT_PUBLIC_ASSET_PREFIX": asset_prefix,
    }
    install_cmd = ["npm", "ci"] if (workspace / "package-lock.json").is_file() else ["npm", "install"]
    _run_cmd(install_cmd, cwd=workspace)
    _run_cmd(["npm", "run", "build"], cwd=workspace, env=build_env)
    out = workspace / "out"
    if not out.is_dir():
        raise RuntimeError("Next build did not produce out/ directory")
    return out


def run_claude_build(profile_id: str, handle: str) -> list[str]:
    log: list[str] = []
    graph = fetch_profile_graph(profile_id)
    from spec_builder import build_portfolio_markdown

    spec = build_portfolio_markdown(graph)
    log.append(f"Spec from DB ({len(spec)} chars)")

    mod_issues = moderate_text(spec, "portfolio spec")
    if mod_issues:
        raise ValueError("; ".join(mod_issues))

    snapshot = build_portfolio_snapshot(profile_id, graph=graph)
    workspace = _prepare_workspace(profile_id, spec, snapshot)
    log.append("Workspace prepared from template")
    log.append(f"Skills: {', '.join(select_skills(spec, snapshot))}")

    require_claude = os.environ.get("REQUIRE_CLAUDE", "").lower() in ("1", "true", "yes")
    claude_ok = _invoke_claude(
        "build.txt", workspace=workspace, phase="primary", spec=spec, snapshot=snapshot
    )
    if claude_ok:
        log.append("Claude Code build pass complete (DeepSeek/OpenRouter via Claude CLI)")
    elif require_claude:
        raise RuntimeError(
            "Claude Code is required but did not complete. Check DEEPSEEK_API_KEY / "
            "OPENROUTER_API_KEY secrets and Cloud Run logs for [CLAUDE]."
        )
    else:
        log.append(
            "Claude Code skipped or failed — continuing with Next.js template only "
            "(set REQUIRE_CLAUDE=true to fail instead)"
        )

    out_dir = _npm_build(workspace, profile_id)
    log.append("npm run build succeeded")

    (out_dir / "data.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    inject_mobile_safety_to_site_dir(str(out_dir))
    log.append("Mobile safety CSS injected into static export")

    issues = run_site_tests(str(out_dir), profile_id, lighthouse=False)
    if issues:
        log.append(f"QA issues: {issues[:5]}")
        fixed = _invoke_claude(
            "fix.txt",
            workspace=workspace,
            phase="fix",
            spec=spec,
            snapshot=snapshot,
            qa_issues=issues,
        )
        if fixed:
            log.append("Claude Code fix pass complete")
            _write_data_json(workspace, snapshot)
            out_dir = _npm_build(workspace, profile_id)
            (out_dir / "data.json").write_text(
                json.dumps(snapshot, indent=2), encoding="utf-8"
            )
            inject_mobile_safety_to_site_dir(str(out_dir))
            issues = run_site_tests(str(out_dir), profile_id, lighthouse=True)
        else:
            log.append("Claude Code fix skipped or failed — not rebuilding")
        if issues:
            soft_only = all(
                any(
                    k in i.lower()
                    for k in ("touch target", "overflow", "horizontal")
                )
                for i in issues
            )
            if soft_only:
                log.append(
                    f"QA layout warnings (uploading site anyway): {issues[:5]}"
                )
            else:
                raise RuntimeError(f"Build failed QA: {issues[:5]}")
    else:
        log.append("All tests passed")

    save_site_dir_to_gcs(profile_id, str(out_dir))
    save_data_json_to_gcs(profile_id, snapshot)
    log.append(f"GCS site uploaded for {profile_id}")

    if os.environ.get("SKIP_GITHUB_PUSH", "").lower() not in ("1", "true", "yes"):
        try:
            url = push_site_to_github(handle, workspace, out_dir, spec, profile_id)
            log.append(f"GitHub: {url}")
        except Exception as e:
            log.append(f"GitHub skipped: {e}")

    return log


def run_python_build(profile_id: str, handle: str) -> list[str]:
    """Legacy single-file HTML pipeline."""
    max_attempts = int(os.environ.get("MAX_BUILD_ATTEMPTS", "3"))
    log: list[str] = []
    spec = read_portfolio_spec(profile_id)
    log.append(f"Spec loaded ({len(spec)} chars)")

    mod_issues = moderate_text(spec, "portfolio spec")
    if mod_issues:
        raise ValueError("; ".join(mod_issues))

    html = None
    issues: list = []
    for attempt in range(1, max_attempts + 1):
        result = generate_website(spec, attempt, issues if attempt > 1 else None)
        html = inject_mobile_safety(result["html"])
        log.append(f"Generated attempt {attempt}")

        mod_html = moderate_text(html, "generated html")
        if mod_html:
            issues = mod_html
        else:
            run_lh = attempt == max_attempts
            issues = run_tests(html, profile_id, lighthouse=run_lh)

        if not issues:
            log.append("All tests passed")
            break
        log.append(f"Attempt {attempt} issues: {issues[:5]}")
        if attempt < max_attempts:
            html = inject_mobile_safety(fix_website(html, issues, spec))

    if issues:
        raise RuntimeError(f"Build failed after {max_attempts} attempts: {issues[:5]}")

    save_to_gcs(profile_id, html)
    snapshot = build_portfolio_snapshot(profile_id)
    save_data_json_to_gcs(profile_id, snapshot)
    log.append("GCS HTML + data.json saved")
    return log


def run_build(profile_id: str, handle: str) -> list[str]:
    if _engine() == "python":
        return run_python_build(profile_id, handle)
    return run_claude_build(profile_id, handle)
