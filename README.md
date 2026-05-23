# bexo-codegen

Cloud Run service that builds student portfolio websites from **Supabase profile data**.

## Pipeline (v2)

1. **BEXO app** → `POST /api/portfolio/trigger-build` (≥90% profile complete) → **n8n** Workflow A
2. **POST /build** → `spec_builder.py` (deterministic `portfolio.md` from DB)
3. **Claude Code** + Next.js static export (`CODEGEN_ENGINE=claude`) or legacy HTML (`python`)
4. Uploads `out/*` + `data.json` to GCS; callbacks **n8n** `bexo-build-done`
5. **Profile edits** → `POST /api/portfolio/sync-data` updates `data.json` only (no rebuild)

## User site stack (fixed)

**Next.js · React · TypeScript · Tailwind CSS** — static export from `templates/portfolio-next/`. Claude customizes `workspace/{profileId}/` only.

## Claude Code + skills (cloud)

Production runs **Claude Code CLI** inside Cloud Run (DeepSeek API). Premium pipeline: `stitch-design-taste` → `imagegen-frontend-web` → `frontend-design` → `image-to-code` → polish skills.

- Sync skills from BEXO: `./scripts/sync-skills-from-bexo.sh`
- VM + Cloud Run guide: [docs/CLAUDE-CODE-CLOUD-WORKFLOW.md](docs/CLAUDE-CODE-CLOUD-WORKFLOW.md)
- Skill selection: [docs/SKILLS-ORCHESTRATOR.md](docs/SKILLS-ORCHESTRATOR.md)
- Scale / queue: [docs/SCALING-ORCHESTRATOR.md](docs/SCALING-ORCHESTRATOR.md)

## Docs

- [docs/AI_MODELS.md](docs/AI_MODELS.md) — Claude proxy, DeepSeek, Kimi
- [docs/BUILD-CLAUDE-STEP-BY-STEP.md](docs/BUILD-CLAUDE-STEP-BY-STEP.md) — first deploy
- [docs/BUILD_PROGRESS.md](docs/BUILD_PROGRESS.md)
- n8n: [infra/n8n/workflows/](infra/n8n/workflows/)
- Hosting: [docs/PORTFOLIO-HOSTING-PLAN.md](docs/PORTFOLIO-HOSTING-PLAN.md)

## Local dev

```bash
cp .env.example .env
pip install -r requirements.txt
export CODEGEN_ENGINE=claude SKIP_CLAUDE=true  # template-only without Claude CLI
python src/main.py
```

## Deploy

```bash
gcloud builds submit --config=cloudbuild.yaml
```

## Production reset (wipe test sites)

```bash
bash scripts/production-reset.sh --execute --kv --github
```

See [docs/PRODUCTION-RESET.md](docs/PRODUCTION-RESET.md).
