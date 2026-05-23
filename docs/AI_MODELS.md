# BEXO AI model routing (Claude Code + DeepSeek + Kimi)

## Architecture (v2)

| Step | Where | Engine |
|------|-------|--------|
| User facts | Supabase | Database only — **no AI portfolio.md** |
| `portfolio.md` | Cloud Run | `spec_builder.py` (deterministic) |
| Site shell | Cloud Run | Claude Code CLI + Next.js static export |
| Content updates | api-server | `POST /portfolio/sync-data` → GCS `data.json` (no AI) |
| Legacy HTML | Cloud Run | `CODEGEN_ENGINE=python` rollback |

## Claude Code proxy (DeepSeek / Kimi)

Set on Cloud Run (map from GCP secrets):

| Env | Purpose |
|-----|---------|
| `ANTHROPIC_BASE_URL` | DeepSeek Anthropic-compatible endpoint or OpenRouter bridge |
| `ANTHROPIC_AUTH_TOKEN` | `DEEPSEEK_API_KEY` or `OPENROUTER_API_KEY` |
| `ANTHROPIC_MODEL` | Primary codegen model |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Same as primary |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Kimi / fast model for QA fix pass |
| `CODEGEN_ENGINE` | `claude` (default) or `python` |
| `SKIP_CLAUDE` | `true` to template-only build (no CLI) |

DeepSeek **context caching** reduces cost on repeated file-tree turns when using a compatible `ANTHROPIC_BASE_URL`.

## API keys (GCP Secret Manager)

| Secret | Used for |
|--------|----------|
| `deepseek-api-key` | Claude proxy + moderation |
| `kimi-api-key` | Fix pass / fallback |
| `openrouter-api-key` | Optional gateway fallback |

## n8n Workflow A (v2)

No OpenRouter nodes. Flow: webhook → Supabase `building` → Cloud Run `/build`.

Set on n8n VM: `CLOUD_RUN_BUILD_URL`, `BEXO_INTERNAL_SECRET`, 300s HTTP timeout on Cloud Run node.

## Content sync (api-server)

`POST /api/portfolio/sync-data` requires:

- `GCS_PUBLIC_BUCKET` (default `bexo-sites-public`)
- `GCS_SA_KEY_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`

## Rollback

Deploy with `CODEGEN_ENGINE=python` to use the legacy Kimi/DeepSeek HTML loop.
