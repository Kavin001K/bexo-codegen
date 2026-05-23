# Scaling the BEXO codegen orchestrator

## Current architecture

```
App (trigger-build) → n8n Workflow A → POST /build (Cloud Run) → Claude phases → GCS + GitHub → n8n Workflow B
```

- **One build = one Cloud Run request** (synchronous today). Timeout 600s, 4Gi RAM.
- **Workspace** is `workspace/` on disk — not safe for concurrent builds on the same instance without per-build directories (see roadmap).

## Target (thousands of users)

| Layer | Pattern |
|-------|---------|
| Ingress | n8n or API enqueues job; returns `buildId` immediately |
| Queue | Cloud Tasks or Pub/Sub → `POST /build/internal` with dedupe on `buildId` |
| Workers | Cloud Run `max-instances` + `concurrency=1` per instance for Claude/npm |
| Storage | GCS `bexo-sites-public/{profileId}/site/` — CDN via Cloudflare Worker |
| Hot path | `sync-data` updates `data.json` only — no full rebuild |

## Orchestrator phases (Claude engine)

1. **Spec** — `spec_builder.py` (deterministic, no LLM)
2. **Plan + design** — Claude + skills (`frontend-design` mandatory)
3. **Compile** — `npm run build` (server only)
4. **Verify** — Playwright QA on `out/` over HTTP
5. **Fix** — Claude + QA list injected (optional)
6. **Publish** — GCS rsync + GitHub source push + n8n callback

## Skill policy

- **`frontend-design`**: always selected (`skill_orchestrator.MANDATORY_SKILLS`)
- **Others**: chosen from `portfolio.md` / profile snapshot (`skill_orchestrator.select_skills`)

## Env knobs

| Variable | Purpose |
|----------|---------|
| `CODEGEN_ENGINE` | `claude` (default) or `python` (legacy HTML) |
| `SKIP_CLAUDE` | Template-only build |
| `CLAUDE_CODE_MAX_TURNS` | Cap agent turns (default 20) |
| `CLAUDE_TIMEOUT_SEC` | CLI timeout (default 480) |
| `MAX_BUILD_ATTEMPTS` | Python engine retries only |

## Roadmap (code)

- [ ] Per-build workspace: `workspace/{buildId}/`
- [ ] `POST /build` → 202 + Cloud Tasks worker
- [ ] Idempotent GCS upload (etag / generation skip)
- [ ] GitHub batch commit or Actions-only deploy
