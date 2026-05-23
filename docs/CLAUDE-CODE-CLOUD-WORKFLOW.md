# Claude Code in the cloud — BEXO website builds

This doc explains how **Claude Code** and **design skills** produce each user’s portfolio site on the mandatory stack: **Next.js, React, Tailwind CSS, TypeScript** (static export).

## Two places Claude Code runs

| Environment | Role |
|-------------|------|
| **`bexo-n8n` VM** (your SSH session) | Manual testing, `/skills`, `/init`, debugging |
| **Cloud Run `bexo-codegen`** | **Production** — every user build from the app |

User-facing builds **must** go through Cloud Run so n8n, GCS, QA, and callbacks stay automated. The VM is for you; production uses the same skills **bundled in the Docker image**.

## End-to-end flow

```
BEXO app (profile ≥90%)
  → api-server POST /portfolio/trigger-build
  → n8n Workflow A
  → Cloud Run POST /build
       1. spec_builder.py → portfolio.md + data.json
       2. Claude Code CLI (DeepSeek via ANTHROPIC_BASE_URL)
          Skills: stitch → imagegen → frontend-design → image-to-code → …
       3. npm run build (orchestrator only)
       4. Playwright QA → optional Claude fix pass
       5. Upload gs://bexo-sites-public/{profileId}/site/
  → n8n Workflow B → live URL
```

## Skills (same as your VM `/skills` list)

Bundled under `bexo-codegen/.claude/skills/` (copied from `BEXO/.agents/skills/`):

| Skill | Build role |
|-------|------------|
| `stitch-design-taste` | DESIGN tokens from portfolio spec |
| `imagegen-frontend-web` | One comp per section (or spec-only if no image tool) |
| `frontend-design` | **Mandatory** — anti-generic UI |
| `image-to-code` | Implement Next.js workspace from comps/spec |
| `impeccable` | Polish + a11y |
| `brandkit`, `high-end-visual-design`, … | Added from profile keywords |

Sync after editing skills in BEXO:

```bash
cd bexo-codegen
chmod +x scripts/sync-skills-from-bexo.sh
./scripts/sync-skills-from-bexo.sh
```

Then redeploy Cloud Run (see `docs/BUILD-CLAUDE-STEP-BY-STEP.md`).

## VM setup (optional, for parity with production)

On `bexo-n8n`:

```bash
# DeepSeek for Claude Code (same as Cloud Run)
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_AUTH_TOKEN=<DEEPSEEK_KEY>
export ANTHROPIC_MODEL=deepseek-v4-pro[1m]

# Work in a project dir, not ~
cd ~/bexo-codegen   # git clone or scp from Mac
claude
# /init  → reads .claude/CLAUDE.md
```

Install skills on the VM (match production):

```bash
cd ~/bexo-codegen && ./scripts/sync-skills-from-bexo.sh
```

## Production env (Cloud Run)

| Variable | Purpose |
|----------|---------|
| `CODEGEN_ENGINE=claude` | Use Claude path (default) |
| `SKIP_CLAUDE=false` | Run Claude CLI |
| `REQUIRE_CLAUDE=true` | Fail build if CLI fails (recommended) |
| `DEEPSEEK_API_KEY` | Secret → Anthropic-compatible API |
| `CLAUDE_CODE_MAX_TURNS` | Default 20 |
| `CLAUDE_TIMEOUT_SEC` | Default 480 |

Verify after deploy:

```bash
CODEGEN_URL=$(gcloud run services describe bexo-codegen --region=us-central1 --format='value(status.url)')
curl -s "$CODEGEN_URL/health" | jq '.skills'
```

Expect `"pipeline": ["stitch-design-taste", "imagegen-frontend-web", "frontend-design", "image-to-code"]` and those names under `"found"`.

## n8n VM env

In `~/bexo-n8n/.env`:

```
CLOUD_RUN_BUILD_URL=https://bexo-codegen-xxxxx.run.app/build
BEXO_INTERNAL_SECRET=<same as Secret Manager>
```

Workflow: `infra/n8n/workflows/bexo-portfolio-generate.json` (no OpenRouter AI nodes — codegen owns Claude).

## Stack guarantee

- Template: `templates/portfolio-next/` (Next 14, React 18, Tailwind 3, TypeScript 5)
- Claude may only customize `./workspace` per build; orchestrator runs `npm run build` and QA
- No Vite/CRA/plain HTML for user sites in the Claude engine path

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Generic template site only | `SKIP_CLAUDE=true` or missing DeepSeek key — set secrets, `REQUIRE_CLAUDE=true` |
| `[CLAUDE] claude CLI not found` | Redeploy image (`Dockerfile` installs `@anthropic-ai/claude-code`) |
| Skills missing in `/health` | Run `sync-skills-from-bexo.sh`, rebuild image |
| Build works on VM but not Cloud Run | VM is manual; wire n8n → Cloud Run URL |

See also: `docs/SKILLS-ORCHESTRATOR.md`, `docs/AI_MODELS.md`, `docs/BUILD-CLAUDE-STEP-BY-STEP.md`.
