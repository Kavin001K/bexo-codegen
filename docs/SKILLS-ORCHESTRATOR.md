# Design skills and orchestrator

## Mandatory stack

Every Claude build outputs **Next.js + React + TypeScript + Tailwind CSS** (static export). See `.claude/CLAUDE.md`.

## Premium pipeline (every build)

`src/skill_orchestrator.py` runs this **Skill tool order**:

1. `stitch-design-taste`
2. `imagegen-frontend-web`
3. `frontend-design` (**mandatory**)
4. `image-to-code`
5. `impeccable`, `web-design-guidelines`
6. Profile-triggered: `brandkit`, `high-end-visual-design`, `minimalist-ui`, …

Logs: `[SKILLS] build: stitch-design-taste, imagegen-frontend-web, frontend-design, image-to-code, ...`

## Sync skills from BEXO app repo

```bash
./scripts/sync-skills-from-bexo.sh
```

Copies `BEXO/.agents/skills/*` → `skills/` and `.claude/skills/`.

## Docker / Cloud Run

`Dockerfile` copies `skills/` → `.claude/skills/` so the CLI finds them in the container.

Verify after deploy:

```bash
curl -s "$CODEGEN_URL/health" | jq .skills
```

## Claude invocation

```
claude -p prompts/build.txt \
  --append-system-prompt "<orchestrator + skill excerpts>" \
  --allowedTools Edit,Bash,Write,Skill \
  --add-dir workspace/<profileId>
```

`REQUIRE_CLAUDE=true` on Cloud Run fails the build if the CLI does not complete (no silent template-only sites).

See `docs/CLAUDE-CODE-CLOUD-WORKFLOW.md` and `docs/SCALING-ORCHESTRATOR.md`.
