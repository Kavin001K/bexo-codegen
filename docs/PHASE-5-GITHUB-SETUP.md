# Phase 5 — GitHub backup (one repo per handle)

**Already implemented in code:** each successful `/build` calls `push_to_github()` which creates or updates `portfolio-{handle}` with `index.html`, `portfolio.md`, and `README.md`.

**Live site does not depend on GitHub** — hosting is GCS + Worker + KV. GitHub is your **git backup / history**.

---

## Step-by-step (do in order)

### Step 1 — Create org `bexo-sites` (browser, ~5 min)

1. Open https://github.com/organizations/plan
2. Choose **Create a free organization**
3. Name: **`bexo-sites`** (must match exactly)
4. Add your user (`Kavin001K`) as **Owner**
5. Finish setup (no paid plan required)

Verify in terminal:

```bash
gh api orgs/bexo-sites --jq .login
# should print: bexo-sites
```

If `gh` says missing `admin:org` scope: `gh auth refresh -h github.com -s admin:org`

---

### Step 2 — Create PAT and store in GCP (~5 min)

**Classic PAT (recommended):** https://github.com/settings/tokens/new

| Setting | Value |
|---------|--------|
| Note | `bexo-codegen-cloud-run` |
| Expiration | 90 days or No expiration (your policy) |
| Scopes | **`repo`** (full control of private repositories) |

If the token is only for **org** repos under `bexo-sites`, also ensure the token owner is an **org owner** (or grant the machine user access).

**Test before GCP:**

```bash
export GITHUB_TOKEN=github_pat_YOUR_NEW_TOKEN
chmod +x scripts/verify-github-phase5.sh
./scripts/verify-github-phase5.sh bexo-sites
```

**Upload to Secret Manager** (do not commit the token):

```bash
echo -n "github_pat_YOUR_NEW_TOKEN" | gcloud secrets versions add github-token \
  --data-file=- \
  --project=bexo-prod
```

---

### Step 3 — Point Cloud Run at the org + redeploy (~10 min)

In `cloudbuild.yaml`, change `GITHUB_ORG=auto` → `GITHUB_ORG=bexo-sites`, then:

```bash
cd ~/Documents/GitHub/bexo-codegen
gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod
```

Wait for build **SUCCESS** (~5–8 min).

Confirm env:

```bash
gcloud run services describe bexo-codegen --region=us-central1 --project=bexo-prod \
  --format='value(spec.template.spec.containers[0].env)' | tr ';' '\n' | grep GITHUB_ORG
# GITHUB_ORG=bexo-sites
```

---

### Step 4 — Prove it with one build (~5 min)

Trigger any portfolio build (app Generate or n8n curl). Then:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="bexo-codegen" AND textPayload:GITHUB' \
  --project=bexo-prod --limit=5 --format='value(textPayload)'
```

Expect: `GitHub: https://github.com/bexo-sites/portfolio-HANDLE`

In browser: https://github.com/orgs/bexo-sites/repositories → **`portfolio-{handle}`** with `index.html`, `portfolio.md`.

---

### Step 5 — Optional: Actions deploy workflow

Skip unless you want GitHub push → GCS as a second path. Live sites already use codegen → `bexo-sites-public`.

---

## What happens on each build

| First build for handle `kavink` | Every later build |
|-------------------------------|-------------------|
| Creates repo `portfolio-kavink` (org or your user) | Updates same files |
| Adds `.github/workflows/deploy.yml` (optional CI) | New commit via API |
| Pushes `index.html`, `portfolio.md`, `README.md` | Same |

Repo URL example: `https://github.com/bexo-sites/portfolio-kavink` (if org exists).

---

## Step 1 — Create GitHub org (recommended)

1. https://github.com/organizations/plan → create **`bexo-sites`** (free).
2. Note the org name exactly (lowercase).

**Handle → repo name:** `portfolio-{handle}` — handle must be a valid GitHub repo name (letters, numbers, hyphens; no spaces).

---

## Step 2 — GitHub token (PAT)

Create a token that can create/update repos in the org:

**Classic PAT** (simplest):

- **repo** (full) — or fine-grained with:
  - Organization: `bexo-sites`
  - Repositories: all (or `portfolio-*`)
  - Contents: Read and write
  - Administration: Read and write (to create repos)

Store in GCP Secret Manager (if not already):

```bash
echo -n "github_pat_...." | gcloud secrets versions add github-token \
  --data-file=- --project=bexo-prod
```

Cloud Run already mounts `github-token` via `cloudbuild.yaml`.

---

## Step 3 — Point Cloud Run at the org

Edit `cloudbuild.yaml` — change:

```yaml
GITHUB_ORG=auto
```

to:

```yaml
GITHUB_ORG=bexo-sites
```

Redeploy:

```bash
cd ~/Documents/GitHub/bexo-codegen
gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod
```

**`GITHUB_ORG=auto` today:** if org missing, repos go under the **token owner’s user account** (still works as backup).

---

## Step 4 — Verify after one build

After Workflow A + Cloud Run succeed, check Cloud Run logs for:

```text
[GITHUB] https://github.com/bexo-sites/portfolio-HANDLE
```

Or non-fatal skip line if token/org issue.

In GitHub: org **bexo-sites** → repo **portfolio-{handle}** → files `index.html`, `portfolio.md`.

---

## Step 5 — Org Actions secrets (optional)

The template workflow in each repo (`.github/workflows/deploy.yml`) can deploy to GCS on push. **Not required** for `https://{handle}.mybexo.com` (codegen uploads to `bexo-sites-public` directly).

If you want Actions as a second deploy path, add **organization secrets** on `bexo-sites`:

| Secret | Value |
|--------|--------|
| `GCS_SA_KEY` | JSON key for SA with write to `bexo-sites-public` |
| `CF_TOKEN` | Cloudflare API token (cache purge only) |
| `CF_ZONE_ID` | `mybexo.com` zone id |

Most teams skip this and rely on codegen + GCS only.

---

## Security — never paste tokens in chat or tickets

If a PAT was exposed anywhere public, **revoke it immediately** on GitHub (Settings → Developer settings → Personal access tokens), create a new PAT, then:

```bash
echo -n "NEW_TOKEN" | gcloud secrets versions add github-token --data-file=- --project=bexo-prod
```

Redeploy Cloud Run so the service picks up the new secret version (or wait for the next deploy).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `404` on org `bexo-sites` | Create org or keep `GITHUB_ORG=auto` (user repos) |
| `GitHub skipped (non-fatal)` in logs | Fix `github-token` permissions; build still succeeds |
| No repo for handle | Check handle characters; view Cloud Run log |
| Repo exists but old HTML | Normal — next build runs `update_file` |

---

## Related code

- `src/github_push.py` — create/update repo
- `src/main.py` — calls `push_to_github` after GCS save (non-fatal on error)
