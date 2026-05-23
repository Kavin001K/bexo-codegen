import os
from pathlib import Path

from github import Github, GithubException

TEXT_SUFFIXES = {
    ".html",
    ".css",
    ".js",
    ".json",
    ".md",
    ".txt",
    ".mjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".yml",
    ".yaml",
    ".svg",
}

DEPLOY_YML = """name: Build and sync portfolio to GCS
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Resolve profile ID
        id: profile
        run: |
          PID="${{ vars.PROFILE_ID }}"
          if [ -z "$PID" ]; then
            PID=$(grep -m1 'Profile ID:' README.md | sed 's/.*`\\([^`]*\\)`.*/\\1/')
          fi
          echo "id=$PID" >> "$GITHUB_OUTPUT"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
      - run: npm ci
      - run: npm run build
        env:
          NEXT_PUBLIC_ASSET_PREFIX: https://storage.googleapis.com/bexo-sites-public/${{ steps.profile.outputs.id }}/site
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: '${{ secrets.GCS_SA_KEY }}'
      - name: Upload static export
        run: |
          gcloud storage rsync -r ./out "gs://bexo-sites-public/${{ steps.profile.outputs.id }}/site" \\
            --delete-unmatched-destination-objects
      - name: Purge Cloudflare cache
        run: |
          curl -sS -X POST "https://api.cloudflare.com/client/v4/zones/${{ secrets.CF_ZONE_ID }}/purge_cache" \\
            -H "Authorization: Bearer ${{ secrets.CF_TOKEN }}" \\
            -H "Content-Type: application/json" \\
            --data '{"purge_everything":true}'
"""


def _client() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN is required")
    return Github(token)


def _is_text(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def _collect_source_files(ws: Path) -> list[tuple[str, str]]:
    """Next.js project files for GitHub (no node_modules / out / _next)."""
    files: list[tuple[str, str]] = []
    skip_dirs = {".git", "node_modules", ".next", "out"}
    for fp in ws.rglob("*"):
        if not fp.is_file():
            continue
        if any(part in skip_dirs for part in fp.parts):
            continue
        if not _is_text(fp):
            continue
        rel = fp.relative_to(ws).as_posix()
        files.append((rel, fp.read_text(encoding="utf-8")))
    return files


def _create_repo(owner, name: str, handle: str):
    try:
        return owner.get_repo(name)
    except GithubException:
        return owner.create_repo(
            name,
            description=f"Portfolio for @{handle} — Next.js static export (BEXO)",
            private=False,
            auto_init=True,
        )


def get_or_create_repo(handle: str):
    g = _client()
    name = f"portfolio-{handle}"
    org_name = (os.environ.get("GITHUB_ORG") or "").strip()

    if org_name and org_name.lower() not in ("none", "user", "auto"):
        try:
            org = g.get_organization(org_name)
            return _create_repo(org, name, handle)
        except GithubException as e:
            if getattr(e, "status", None) != 404:
                raise
            print(f"[GITHUB] org '{org_name}' not found — using token user account")

    user = g.get_user()
    return _create_repo(user, name, handle)


def upsert(repo, path: str, content: str, msg: str) -> None:
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, msg, content, existing.sha)
    except GithubException:
        repo.create_file(path, msg, content)


def push_site_to_github(handle: str, workspace, out_dir, spec: str, profile_id: str) -> str:
    """Push full Next.js source; CI builds out/ and syncs to GCS."""
    domain = os.environ.get("PORTFOLIO_DOMAIN", "mybexo.com")
    repo = get_or_create_repo(handle)
    ws = Path(workspace)

    for path, content in _collect_source_files(ws):
        upsert(repo, path, content, f"sync: {path}")

    readme = (
        f"# {handle}'s Portfolio\n\n"
        f"Live: https://{handle}.{domain}\n\n"
        f"**Stack:** Next.js 14 (`output: 'export'`), Tailwind, Framer Motion.\n\n"
        f"| Path | Purpose |\n"
        f"|------|--------|\n"
        f"| `app/` | Routes (static export) |\n"
        f"| `components/` | Portfolio UI |\n"
        f"| `lib/` | `getPortfolioData()` reads `public/data.json` |\n"
        f"| `public/data.json` | Snapshot from BEXO profile |\n\n"
        f"**CI:** push to `main` runs `npm run build` and uploads `out/` to GCS.\n\n"
        f"Set repo variable **`PROFILE_ID`** = `{profile_id}` (Settings → Secrets and variables → Actions).\n\n"
        f"Profile ID: `{profile_id}`\n"
    )
    upsert(repo, "README.md", readme, "docs: readme")
    upsert(repo, "portfolio.md", spec, "docs: portfolio spec from database")
    upsert(repo, ".github/workflows/deploy.yml", DEPLOY_YML, "ci: build Next.js and sync to GCS")

    return repo.html_url


def push_to_github(handle: str, html: str, spec: str, profile_id: str) -> str:
    domain = os.environ.get("PORTFOLIO_DOMAIN", "mybexo.com")
    repo = get_or_create_repo(handle)
    upsert(repo, "legacy/index.html", html, f"build: legacy html for {handle}")
    upsert(repo, "portfolio.md", spec, "docs: portfolio spec")
    upsert(
        repo,
        "README.md",
        f"# {handle}'s Portfolio\n\nLive: https://{handle}.{domain}\n\nProfile ID: `{profile_id}`\n",
        "docs: readme",
    )
    return repo.html_url
