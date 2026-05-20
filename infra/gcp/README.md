# GCP foundation for BEXO pipeline

## Quick start

```bash
export PROJECT_ID=bexo-prod
./setup-foundation.sh
```

## AI secrets (DeepSeek + Kimi)

```bash
# DeepSeek — spec, fix loop, moderation (n8n + Cloud Run)
echo -n "YOUR_DEEPSEEK_KEY" | gcloud secrets create deepseek-api-key --data-file=-

# Kimi (Moonshot) — main HTML generation on Cloud Run
echo -n "YOUR_KIMI_KEY" | gcloud secrets create kimi-api-key --data-file=-

# Optional: OpenRouter fallback / n8n single-key mode
echo -n "sk-or-..." | gcloud secrets create openrouter-api-key --data-file=-
```

See [docs/AI_MODELS.md](../../docs/AI_MODELS.md) for per-task model names.

## Other secrets

```bash
echo -n "github_pat_..." | gcloud secrets create github-token --data-file=-
echo -n "cf_..." | gcloud secrets create cloudflare-token --data-file=-
echo -n "ZONE_ID" | gcloud secrets create cloudflare-zone-id --data-file=-
echo -n "https://xxx.supabase.co" | gcloud secrets create supabase-url --data-file=-
echo -n "eyJ..." | gcloud secrets create supabase-service-key --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets create bexo-internal-secret --data-file=-
echo -n "https://n8n.mybexo.com/webhook/bexo-build-done" | gcloud secrets create n8n-callback-url --data-file=-
```

Grant `bexo-codegen@` access:

```bash
for SECRET in deepseek-api-key kimi-api-key openrouter-api-key github-token cloudflare-token cloudflare-zone-id supabase-url supabase-service-key bexo-internal-secret n8n-callback-url; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:bexo-codegen@bexo-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" --quiet 2>/dev/null || true
done
```

## Optional retries

```bash
./cloud-tasks-queue.sh
```
