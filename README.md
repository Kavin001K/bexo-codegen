# bexo-codegen

Cloud Run service that builds student portfolio websites from `portfolio.md` specs in GCS.

## Pipeline

1. **n8n** writes `gs://bexo-portfolios/{profileId}/portfolio.md` after Supabase + AI spec pass
2. **POST /build** reads spec → **Kimi** generates HTML → **DeepSeek** fixes → Playwright/Lighthouse tests (max 3)
3. Saves `site/index.html` to GCS, pushes `portfolio-{handle}` repo to GitHub
4. Callbacks **n8n** `bexo-build-done` for DNS + Supabase `site_builds` update

## Docs

- **Living deploy log:** [docs/BUILD_PROGRESS.md](docs/BUILD_PROGRESS.md) (phases, secrets, URLs, changelog)
- Interactive build tracker: [docs/bexo-unified-build-guide.html](docs/bexo-unified-build-guide.html)
- n8n workflows: [infra/n8n/workflows/](infra/n8n/workflows/)
- GCP setup: [infra/gcp/setup-foundation.sh](infra/gcp/setup-foundation.sh)

## Local dev

```bash
cp .env.example .env
pip install -r requirements.txt
playwright install chromium   # Docker/Cloud Run uses system Chromium instead
python src/main.py
```

## Deploy

```bash
gcloud builds submit --config=cloudbuild.yaml
```
