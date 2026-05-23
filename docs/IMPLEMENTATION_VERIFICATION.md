# BEXO Complete Portfolio System — verification checklist

Run after deploying Cloud Run + Worker + re-importing n8n Workflow A.

## 1. Cloud Build

```bash
cd bexo-codegen
gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod
```

## 2. Sandbox `/build`

```bash
INTERNAL=$(gcloud secrets versions access latest --secret=bexo-internal-secret --project=bexo-prod)
curl -X POST "https://bexo-codegen-XXXX.run.app/build" \
  -H "Content-Type: application/json" \
  -H "X-BEXO-Internal-Secret: $INTERNAL" \
  -d '{"profileId":"UUID","buildId":"UUID","handle":"testhandle"}'
```

## 3. GCS artifacts

```bash
gsutil ls -l "gs://bexo-sites-public/PROFILE_UUID/site/index.html"
gsutil ls "gs://bexo-sites-public/PROFILE_UUID/site/_next/"
gsutil cat "gs://bexo-sites-public/PROFILE_UUID/site/data.json" | head
```

## 4. Edge URL

- Desktop + 375px mobile: `https://HANDLE.mybexo.com`
- No horizontal scroll; projects/skills render from `data.json`

## 5. App flows

- Profile &lt;90% → trigger-build returns 403; home banner shows missing fields
- Profile ≥90% → build queues; `site_builds` → `done`
- Edit project → `sync-data` → refresh site shows new title (no Cloud Run)

## 6. n8n

- Re-import `infra/n8n/workflows/bexo-portfolio-generate.json` (no OpenRouter nodes)
- Set `CLOUD_RUN_BUILD_URL` on n8n VM

## Rollback

Set Cloud Run env `CODEGEN_ENGINE=python` for legacy HTML pipeline.
