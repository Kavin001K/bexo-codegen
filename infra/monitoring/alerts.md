# BEXO pipeline monitoring

## Cloud Logging filters

```
resource.type="cloud_run_revision"
resource.labels.service_name="bexo-codegen"
severity>=ERROR
```

## Recommended alerts (GCP Monitoring)

| Alert | Condition |
|-------|-----------|
| Codegen failures | Log metric `ERROR` count > 5 in 15 min |
| Cloud Run latency | p95 > 240s |
| n8n VM down | Uptime check on `https://n8n.mybexo.com/healthz` |
| DeepSeek / Kimi / OpenRouter budget | Set caps on each provider dashboard |

## Cost caps

- Cloud Run `max-instances=5` (cloudbuild.yaml)
- DeepSeek + Kimi monthly limits per provider (see docs/AI_MODELS.md)
- GCS lifecycle: delete `*/site/*` older than 90d for failed profiles (optional rule)
