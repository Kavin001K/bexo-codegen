# Phase 8 — App end-to-end test checklist

Use this when you **create a new account in the BEXO app** and run **Generate** (in ~2 hours or anytime).

**Yes — this is the correct test.** Manual `curl` only proves n8n/Cloud Run; the app test proves `N8N_WEBHOOK_URL` + `N8N_WEBHOOK_SECRET` and the full product path.

---

## Before you start

- [ ] BEXO api-server has `N8N_WEBHOOK_URL=https://n8n.mybexo.com/webhook/bexo-portfolio-generate`
- [ ] BEXO api-server has `N8N_WEBHOOK_SECRET` = same as `~/bexo-n8n/.env` on VM
- [ ] App deployed/restarted after env change
- [ ] Pick a **new handle** you have not used (e.g. `testuser2026`) — not only `kavink`

---

## During the test (watch ~3–5 min)

### 1. App

- [ ] Sign up / log in with a **new** account
- [ ] Complete profile so **handle** is set
- [ ] Tap **Generate** (Generating screen)
- [ ] Note `profileId` / `buildId` if the app shows them (optional)

### 2. n8n — https://n8n.mybexo.com

- [ ] **BEXO — Portfolio Generate (A):** new execution, **all green**
- [ ] **BEXO — Build Done (B):** runs after Cloud Run, **all green** (KV put + Supabase done)

### 3. Supabase

```sql
SELECT handle, status, portfolio_url, updated_at
FROM site_builds sb
JOIN profiles p ON p.id = sb.profile_id
ORDER BY sb.updated_at DESC
LIMIT 5;
```

- [ ] Latest row: `status = done`
- [ ] `portfolio_url = https://YOUR_HANDLE.mybexo.com`

### 4. Live URL

```bash
curl -sI "https://YOUR_HANDLE.mybexo.com" | head -3
```

- [ ] `HTTP/2 200`
- [ ] Open same URL in browser — portfolio loads

### 5. GitHub backup (Phase 5)

- [ ] Org or user has repo `portfolio-YOUR_HANDLE`
- [ ] `index.html` and `portfolio.md` updated (after org/token configured)

---

## If something fails

| Stuck on | Check |
|----------|--------|
| App never starts build | api-server logs; webhook URL/secret |
| Workflow A red | n8n execution error node; OpenRouter/GCS |
| No Workflow B | Cloud Run logs `[CALLBACK]`; `n8n-callback-url` secret |
| `done` but 404 on URL | Workflow B KV node; handle typo |
| GitHub missing | `GITHUB_ORG`, `github-token`; Cloud Run log `non-fatal` |

---

## Phase 8 complete when

All boxes above are checked for **one new handle** from the **app** (not only `curl`).

Then update `scripts/generate_build_guide.py` — add `p8-1` … `p8-5` to `DEFAULT_COMPLETED` — and run `python3 scripts/generate_build_guide.py`.
