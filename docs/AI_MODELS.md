# BEXO AI model routing (DeepSeek + Kimi)

## Per-task assignment

| Pipeline step | Where | Provider | Default model | Env override |
|---------------|-------|----------|---------------|--------------|
| Personality JSON | n8n | **OpenRouter (free)** | `openrouter/free` | `OPENROUTER_MODEL_SPEC` |
| `portfolio.md` spec | n8n | **OpenRouter (free)** | `openrouter/free` | `OPENROUTER_MODEL_SPEC` |
| HTML generation (attempt 1) | Cloud Run | **Kimi** | `kimi-k2-turbo-preview` | `KIMI_MODEL_GENERATE` |
| HTML fix (attempts 2–3) | Cloud Run | **DeepSeek** | `deepseek-chat` | `DEEPSEEK_MODEL_FIX` |
| Content moderation | Cloud Run | **DeepSeek** | `deepseek-chat` | `DEEPSEEK_MODEL_MODERATION` |

If Kimi fails on generation, codegen falls back to DeepSeek, then OpenRouter (if configured).

## API keys (GCP Secret Manager)

| Secret | Used for |
|--------|----------|
| `deepseek-api-key` | DeepSeek direct API |
| `kimi-api-key` | Moonshot / Kimi direct API |
| `openrouter-api-key` | Optional unified gateway + fallback |

Get keys:

- DeepSeek: https://platform.deepseek.com/api_keys
- Kimi (Moonshot): https://platform.moonshot.ai/console/api-keys

## OpenRouter-only mode

Set only `OPENROUTER_API_KEY` (no DeepSeek/Kimi keys). Defaults:

- Spec/fix: `deepseek/deepseek-chat`
- Generate: `moonshotai/kimi-k2`

Override with `OPENROUTER_MODEL_*` env vars.

## n8n workflow models (OpenRouter, free only)

Workflow A uses **OpenRouter** for both AI nodes. Set on the VM in `~/bexo-n8n/.env`:

- `OPENROUTER_MODEL_SPEC=openrouter/free` (default — OpenRouter’s free model router)

Other free options (if you want a fixed model instead of the router):

- `meta-llama/llama-3.3-8b-instruct:free`
- `google/gemma-2-9b-it:free`

Do **not** use `deepseek/deepseek-chat` on OpenRouter unless you have credits — it is not in the free tier.
