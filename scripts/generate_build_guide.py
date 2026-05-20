#!/usr/bin/env python3
"""Generate docs/bexo-unified-build-guide.html"""

from __future__ import annotations

import json
from pathlib import Path

CHECKS = [
    ("p0-1", "gcp", "BEXO mobile app builds and onboarding completes"),
    ("p0-2", "gcp", "Supabase project live with migrations applied"),
    ("p0-3", "gcp", "Domain mybexo.com on Cloudflare"),
    ("p0-4", "gcp", "GCP billing linked to bexo-prod"),
    ("p1-1", "gcp", "gcloud project set to bexo-prod"),
    ("p1-2", "gcp", "All required APIs enabled"),
    ("p1-3", "gcp", "Secret Manager: deepseek-api-key (optional)"),
    ("p1-3b", "gcp", "Secret Manager: kimi-api-key (optional)"),
    ("p1-3c", "gcp", "Secret Manager: openrouter-api-key"),
    ("p1-4", "gcp", "Secret Manager: github-token"),
    ("p1-5", "gcp", "Secret Manager: cloudflare-token + zone-id (Phase 7)"),
    ("p1-6", "gcp", "Secret Manager: supabase-url + service key"),
    ("p1-7", "gcp", "Secret Manager: bexo-internal-secret"),
    ("p1-8", "gcp", "GCS bucket bexo-portfolios created"),
    ("p1-9", "gcp", "Service account bexo-codegen + IAM"),
    ("p1-10", "gcp", "Service account n8n-invoker + run.invoker"),
    ("p1-11", "gcp", "Ran infra/gcp/setup-foundation.sh successfully"),
    ("p2-1", "n8n", "GCE VM bexo-n8n running (e2-micro)"),
    ("p2-2", "n8n", "docker-compose.micro.yml — Postgres + n8n healthy"),
    ("p2-3", "n8n", "https://n8n.mybexo.com loads with SSL"),
    ("p2-4", "n8n", "n8n basic auth + N8N_ENCRYPTION_KEY set"),
    ("p2-5", "n8n", "N8N_BLOCK_ENV_ACCESS_IN_NODE=false + recover-n8n.sh tested"),
    ("p2-6", "n8n", "Optional: Redis + worker queue (not used on micro stack)"),
    ("p3-1", "n8n", "Workflow A imported + published (bexo-portfolio-generate)"),
    ("p3-2", "n8n", "Workflow B imported (bexo-build-done — activate Phase 7)"),
    ("p3-3", "n8n", "Optional: bexo-rebuild workflow imported"),
    ("p3-4", "n8n", "Supabase env on VM (SUPABASE_URL + service role key)"),
    ("p3-5", "n8n", "OpenRouter free (OPENROUTER_API_KEY + openrouter/free)"),
    ("p3-6", "n8n", "GCS credential + upload writes portfolio.md"),
    ("p3-7", "n8n", "BEXO_INTERNAL_SECRET + Cloud Run URL in workflow"),
    ("p3-8", "n8n", "Test webhook returns 200"),
    ("p3-9", "n8n", "Workflow A E2E: all nodes green incl. Cloud Run /build"),
    ("p4-1", "codegen", "tester.py + github_push.py + mobile_safety.py"),
    ("p4-2", "codegen", "Cloud Build deploys image (cloudbuild.yaml)"),
    ("p4-3", "codegen", "Cloud Run live — /build secret-gated, /health public"),
    ("p4-4", "codegen", "Secrets on Cloud Run (OPENROUTER_FREE_ONLY=true)"),
    ("p4-5", "codegen", "GET /health returns ok"),
    ("p4-6", "codegen", "POST /build returns 200 — site/index.html in GCS"),
    ("p5-1", "codegen", "GitHub org bexo-sites (optional)"),
    ("p5-2", "codegen", "Org secrets for GitHub Actions deploy"),
    ("p5-3", "codegen", "portfolio-{handle} repo + deploy workflow"),
    ("p6-1", "dns", "Public bucket bexo-sites-public + setup script"),
    ("p6-2", "dns", "GCS site/index.html written for test profile"),
    ("p6-3", "dns", "Public URL https://{handle}.mybexo.com works"),
    ("p7-1", "dns", "Workflow B published — KV put + Supabase done"),
    ("p7-2", "dns", "Wildcard DNS + route *.mybexo.com/* on Worker"),
    ("p7-3", "dns", "wrangler deploy bexo-portfolio-proxy + KV binding"),
    ("p8-1", "gcp", "N8N_WEBHOOK_URL on BEXO api-server"),
    ("p8-2", "gcp", "N8N_WEBHOOK_SECRET matches n8n VM"),
    ("p8-3", "gcp", "App Generating screen triggers build"),
    ("p8-4", "gcp", "site_builds status done + portfolio_url"),
    ("p8-5", "gcp", "Live URL on mobile + desktop"),
    ("p9-1", "gcp", "Cloud Tasks queue (optional)"),
    ("p9-2", "gcp", "Error alerting on failed builds"),
    ("p9-3", "gcp", "OpenRouter budget documented"),
    ("p9-4", "gcp", "n8n workflow export backed up weekly"),
]

DEFAULT_COMPLETED: frozenset[str] = frozenset(
    {
        "p0-2",
        "p0-4",
        "p1-1",
        "p1-2",
        "p1-3c",
        "p1-4",
        "p1-6",
        "p1-7",
        "p1-8",
        "p1-9",
        "p1-10",
        "p1-11",
        "p2-1",
        "p2-2",
        "p2-3",
        "p2-4",
        "p2-5",
        "p3-1",
        "p3-2",
        "p3-4",
        "p3-5",
        "p3-6",
        "p3-7",
        "p3-8",
        "p3-9",
        "p4-1",
        "p4-2",
        "p4-3",
        "p4-4",
        "p4-5",
        "p4-6",
        "p6-2",
        "p6-1",
        "p6-3",
        "p7-1",
        "p7-2",
        "p7-3",
    }
)

PHASE_STATUS: dict[int, tuple[str, str]] = {
    0: ("partial", "Supabase + billing done; confirm app + Cloudflare"),
    1: ("done", "bexo-prod foundation complete"),
    2: ("done", "n8n VM + micro stack operational"),
    3: ("done", "Workflow A E2E — OpenRouter → GCS → Cloud Run 200"),
    4: ("done", "Codegen deployed; HTML in GCS bucket"),
    5: ("pending", "GitHub org/repos — optional"),
    6: ("done", "bexo-sites-public + Worker serves HTML"),
    7: ("done", "Workflow B + KV + https://kavink.mybexo.com verified"),
    8: ("active", "Wire BEXO api-server — see docs/PHASE-8-SETUP.md"),
    9: ("pending", "Alerts, backups, cost caps"),
}

PHASES = [
    (0, "Prerequisites", "App, Supabase, domain, billing"),
    (1, "GCP Foundation", "APIs, secrets, bucket, service accounts"),
    (2, "n8n VM", "docker-compose.micro.yml, SSL, env"),
    (3, "n8n Workflows", "Workflow A — free OpenRouter + GCS + Cloud Run"),
    (4, "Cloud Run Codegen", "Deploy + /build E2E verified"),
    (5, "GitHub", "Org, repos, Actions deploy"),
    (6, "Hosting", "Public CDN / static serving"),
    (7, "DNS + build-done", "Workflow B + Cloudflare"),
    (8, "Wire BEXO App", "api-server env + in-app E2E"),
    (9, "Hardening", "Alerts, backups, limits"),
]

PHASE_NEXT: dict[int, str] = {
    4: "Phases 5–7 done for MVP hosting; optional GitHub org (Phase 5).",
    7: "Complete — see docs/PHASE-7-PRODUCTION-CHECKLIST.md for security review.",
    8: "Follow docs/PHASE-8-SETUP.md — N8N_WEBHOOK_URL + secret on BEXO api-server.",
}

TERMINAL_BLOCKS = {
    1: """gcloud config set project bexo-prod
chmod +x infra/gcp/setup-foundation.sh && ./infra/gcp/setup-foundation.sh""",
    2: """gcloud compute ssh bexo-n8n --zone=us-central1-a --project=bexo-prod
cd ~/bexo-n8n && docker compose -f docker-compose.micro.yml up -d
bash recover-n8n.sh""",
    3: """curl -X POST "https://n8n.mybexo.com/webhook/bexo-portfolio-generate" \\
  -H "Content-Type: application/json" \\
  -H "X-BEXO-Secret: YOUR_SECRET" \\
  -d '{"profileId":"UUID","buildId":"UUID","triggered_by":"test"}'""",
    4: """gcloud builds submit --config=cloudbuild.yaml --project=bexo-prod .
# https://bexo-codegen-901109516440.us-central1.run.app""",
    6: """# Public portfolio HTML bucket (no IAM conditions on allUsers)
./infra/gcp/setup-public-sites-bucket.sh
gcloud storage cp gs://bexo-portfolios/PROFILE_ID/site/index.html \\
  gs://bexo-sites-public/PROFILE_ID/site/index.html""",
    7: """# Worker + KV — see docs/PORTFOLIO-HOSTING-PLAN.md
cd infra/cloudflare/worker && npx wrangler deploy
# Dashboard: route *.mybexo.com/* + custom domain *.mybexo.com""",
    8: """# BEXO api-server .env
N8N_WEBHOOK_URL=https://n8n.mybexo.com/webhook/bexo-portfolio-generate
N8N_WEBHOOK_SECRET=<same as ~/bexo-n8n/.env>""",
}


def _phase_num(cid: str) -> int:
    return int(cid[1])


def _phase_section(num: int, title: str, desc: str) -> str:
    status_key, status_note = PHASE_STATUS.get(num, ("pending", ""))
    badge_label = {
        "done": "Complete",
        "partial": "Partial",
        "active": "In progress",
        "pending": "To build",
    }[status_key]

    check_html = "\n".join(
        f'<motion class="check-item" data-id="{cid}" data-cat="{cat}" data-phase="{num}">'
        f'<motion class="cb" onclick="toggleCheck(this)"></motion>'
        f'<motion class="ci-text">{label}</motion>'
        f'<span class="ci-cat">{cat}</span></motion>'
        for cid, cat, label in CHECKS
        if _phase_num(cid) == num
    )

    term = ""
    if num in TERMINAL_BLOCKS:
        term = (
            '<motion class="terminal"><motion class="t-bar"><span class="t-bar-title">Commands</span>'
            '<button class="t-copy" onclick="copyBlock(this)">copy</button></motion>'
            f'<pre class="t-body">{TERMINAL_BLOCKS[num]}</pre></motion>'
        )

    next_box = ""
    if num in PHASE_NEXT:
        next_box = f'<div class="callout callout-next"><strong>Next:</strong> {PHASE_NEXT[num]}</div>'

    display = "block" if num == 0 else "none"
    prev_btn = f'<button class="nav-btn" onclick="goPhase({num - 1})">← Previous</button>' if num > 0 else ""
    next_label = "Finish" if num == 9 else "Next →"

    return f"""<section class="phase-section" id="phase-{num}" style="display:{display}">
  <div class="phase-header">
    <div class="ph-row">
      <div class="ph-eyebrow">Phase {num:02d}</div>
      <span class="ph-badge ph-badge-{status_key}">{badge_label}</span>
    </div>
    <div class="ph-title">{title}</div>
    <div class="ph-desc">{desc}</div>
    <div class="ph-status-note">{status_note}</div>
  </div>
  {next_box}
  <div class="steps-container">{term}
    <div class="checklist">{check_html}</div>
  </div>
  <div class="nav-buttons">{prev_btn}
    <button class="nav-btn primary" onclick="goPhase({num + 1})">{next_label}</button>
  </div>
</section>"""


def main() -> None:
    baseline_json = json.dumps({k: True for k in DEFAULT_COMPLETED})
    phases_html = "\n".join(_phase_section(n, t, d) for n, t, d in PHASES)
    sidebar = "\n".join(
        f'<button class="sb-item{" active" if i == 0 else ""}" onclick="goPhase({i})" '
        f'data-phase-status="{PHASE_STATUS.get(i, ("pending", ""))[0]}">'
        f'<span class="si-num">{i:02d}</span><span>{t}</span></button>'
        for i, t, _ in PHASES
    )

    html = HTML_TEMPLATE.format(
        total_checks=len(CHECKS),
        completed_count=len(DEFAULT_COMPLETED),
        sidebar=sidebar,
        phases=phases_html,
        baseline_json=baseline_json,
    )
    html = html.replace("<motion ", "<div ").replace("</motion>", "</div>")

    out = Path(__file__).resolve().parents[1] / "docs" / "bexo-unified-build-guide.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html)} bytes, baseline {len(DEFAULT_COMPLETED)}/{len(CHECKS)})")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BEXO — Unified Build Guide</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Syne:wght@700;800&family=Instrument+Sans:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{{--void:#050508;--ink:#0d0d14;--panel:#13131d;--line:rgba(255,255,255,.08);
--txt:#e8e6f0;--txt2:#9896b0;--txt3:#5e5c72;--hi:#6c5ce7;--hi2:#00cec9;--hi5:#55efc4;
--warn:#fdcb6e;--mono:'IBM Plex Mono',monospace;--display:'Syne',sans-serif;--body:'Instrument Sans',sans-serif}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--void);color:var(--txt);font-family:var(--body);font-size:14px;line-height:1.6}}
#topbar{{position:fixed;top:0;left:0;right:0;z-index:300;height:52px;background:rgba(5,5,8,.97);
border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 20px;gap:16px}}
.tb-logo{{font-family:var(--display);font-weight:800;font-size:15px}}
.tp-bar{{flex:1;max-width:200px;height:4px;background:var(--line);border-radius:2px}}
.tp-fill{{height:100%;background:linear-gradient(90deg,var(--hi),var(--hi2));width:0%;transition:.3s}}
.layout{{display:flex;padding-top:52px;min-height:100vh}}
#sidebar{{width:220px;background:var(--ink);border-right:1px solid var(--line);
position:sticky;top:52px;height:calc(100vh - 52px);overflow-y:auto;padding:12px 0}}
.sb-item{{display:flex;gap:10px;width:100%;padding:8px 16px;border:none;background:none;
color:var(--txt3);cursor:pointer;text-align:left;font-size:12px;align-items:center}}
.sb-item.active,.sb-item:hover{{color:var(--hi5);background:rgba(85,239,196,.06)}}
.sb-item[data-phase-status="done"] .si-num{{background:rgba(85,239,196,.15);color:var(--hi5)}}
.sb-item[data-phase-status="partial"] .si-num{{background:rgba(116,185,255,.12);color:#74b9ff}}
.si-num{{font-family:var(--mono);font-size:10px;width:22px;height:22px;display:flex;align-items:center;
justify-content:center;background:var(--panel);border-radius:4px;flex-shrink:0}}
#main{{flex:1;overflow-y:auto}}
.hero{{padding:48px 40px;background:var(--ink);border-bottom:1px solid var(--line)}}
.hero-title{{font-family:var(--display);font-size:40px;font-weight:800;letter-spacing:-1px;margin:12px 0}}
.hero-sub{{color:var(--txt2);max-width:720px}}
.hero-pill{{display:inline-block;margin-top:12px;padding:6px 12px;border-radius:20px;font-family:var(--mono);
font-size:11px;background:rgba(85,239,196,.1);color:var(--hi5);border:1px solid rgba(85,239,196,.25)}}
.flow-svg{{width:100%;max-width:920px;margin:20px 0}}
.phase-header{{padding:28px 40px 0}}
.ph-row{{display:flex;align-items:center;gap:12px}}
.ph-eyebrow{{font-family:var(--mono);font-size:10px;color:var(--hi2);letter-spacing:2px}}
.ph-badge{{font-family:var(--mono);font-size:10px;padding:3px 10px;border-radius:12px;font-weight:600}}
.ph-badge-done{{background:rgba(85,239,196,.15);color:var(--hi5)}}
.ph-badge-partial{{background:rgba(116,185,255,.12);color:#74b9ff}}
.ph-badge-pending{{background:rgba(253,203,110,.12);color:var(--warn)}}
.ph-badge-active{{background:rgba(108,92,231,.2);color:#a29bfe}}
.sb-item[data-phase-status="active"] .si-num{{background:rgba(108,92,231,.2);color:#a29bfe}}
.ph-title{{font-family:var(--display);font-size:26px;font-weight:800;margin:6px 0}}
.ph-desc{{color:var(--txt2)}}
.ph-status-note{{font-family:var(--mono);font-size:11px;color:var(--txt3);margin-top:8px}}
.steps-container{{padding:20px 40px 32px}}
.checklist{{margin-top:16px}}
.check-item{{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--line);align-items:flex-start}}
.cb{{width:18px;height:18px;border:1.5px solid rgba(255,255,255,.2);border-radius:4px;cursor:pointer;flex-shrink:0;margin-top:2px}}
.cb.checked{{background:var(--hi5);border-color:var(--hi5)}}
.cb.checked::after{{content:'\\2713';display:block;text-align:center;font-size:11px;color:#000;font-weight:700;line-height:16px}}
.ci-text{{flex:1}}
.ci-text.checked{{color:var(--txt3);text-decoration:line-through}}
.ci-cat{{font-family:var(--mono);font-size:9px;color:var(--txt3);padding:2px 6px;background:var(--panel);border-radius:4px}}
.terminal{{background:#02020a;border:1px solid #1e1c35;border-radius:8px;margin:16px 0;overflow:hidden}}
.t-bar{{display:flex;justify-content:space-between;padding:8px 14px;background:#0f0e1e;font-family:var(--mono);font-size:11px;color:var(--txt3)}}
.t-body{{padding:16px;font-family:var(--mono);font-size:12px;white-space:pre-wrap;color:#c8c6e0;margin:0}}
.t-copy{{background:var(--panel);border:1px solid var(--line);color:var(--txt3);padding:2px 8px;border-radius:4px;cursor:pointer}}
.nav-buttons{{display:flex;gap:12px;padding:0 40px 40px}}
.nav-btn{{padding:10px 18px;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:var(--txt);cursor:pointer}}
.nav-btn.primary{{background:var(--hi5);color:#000;border-color:var(--hi5);font-weight:600}}
.toolbar{{padding:12px 40px;display:flex;gap:8px;flex-wrap:wrap}}
.filter-btn{{padding:4px 12px;border-radius:20px;border:1px solid var(--line);background:transparent;color:var(--txt2);cursor:pointer;font-size:11px;font-family:var(--mono)}}
.filter-btn.active{{border-color:var(--hi);color:var(--hi)}}
.callout{{border-left:3px solid var(--hi);padding:12px 16px;margin:16px 40px;background:rgba(108,92,231,.08);color:var(--txt2);font-size:13px}}
.callout-next{{border-left-color:var(--warn);background:rgba(253,203,110,.06)}}
.callout code{{font-family:var(--mono);font-size:12px;color:var(--hi5)}}
@media(max-width:800px){{#sidebar{{display:none}}}}
</style>
</head>
<body>
<div id="topbar">
  <motion class="tb-logo">BEXO / Unified Build Guide</motion>
  <motion class="tp-bar"><motion id="tp-fill" class="tp-fill"></motion></motion>
  <span id="tp-text" style="font-family:var(--mono);font-size:11px;color:var(--txt3)">0%</span>
  <button class="t-copy" onclick="exportProgress()">Export</button>
  <button class="t-copy" onclick="applyBaseline()">Reset baseline</button>
</div>
<div class="layout">
<nav id="sidebar">{sidebar}</nav>
<main id="main">
<div class="hero">
  <div style="font-family:var(--mono);font-size:11px;color:var(--hi5)">● Updated 2026-05-20</div>
  <h1 class="hero-title">Automated portfolio factory</h1>
  <p class="hero-sub"><strong>Done (Phases 1–7):</strong> Live portfolios at https://{{handle}}.mybexo.com (Worker + KV + GCS).
  <strong>Now (Phase 8):</strong> Wire BEXO app webhooks — docs/PHASE-8-SETUP.md.
  <strong>Optional:</strong> Phase 5 GitHub org, Phase 9 hardening.</p>
  <span class="hero-pill">Baseline: {completed_count} / {total_checks} steps verified</span>
</div>
<div class="callout">Log: <code>docs/BUILD_PROGRESS.md</code> · Cloud Run: <code>bexo-codegen-901109516440.us-central1.run.app</code></div>
<div class="toolbar">
  <button class="filter-btn active" data-filter="all" onclick="setFilter('all')">All</button>
  <button class="filter-btn" data-filter="gcp" onclick="setFilter('gcp')">GCP</button>
  <button class="filter-btn" data-filter="n8n" onclick="setFilter('n8n')">n8n</button>
  <button class="filter-btn" data-filter="codegen" onclick="setFilter('codegen')">Codegen</button>
  <button class="filter-btn" data-filter="dns" onclick="setFilter('dns')">DNS</button>
</div>
{phases}
</main>
</div>
<script>
const STORAGE_KEY='bexoBuildProgress';
const BASELINE_PROGRESS={baseline_json};
const PHASES=10;
function loadProgress(){{try{{return JSON.parse(localStorage.getItem(STORAGE_KEY)||'{{}}')}}catch(e){{return {{}}}}}}
function saveProgress(p){{localStorage.setItem(STORAGE_KEY,JSON.stringify(p))}}
function mergeBaseline(p){{Object.keys(BASELINE_PROGRESS).forEach(id=>{{if(p[id]===undefined)p[id]=BASELINE_PROGRESS[id]}});return p}}
function applyBaseline(){{saveProgress({{...BASELINE_PROGRESS}});location.reload()}}
function updateProgressBar(){{
  const total=document.querySelectorAll('.check-item').length;
  const done=document.querySelectorAll('.cb.checked').length;
  const pct=total?Math.round(done/total*100):0;
  document.getElementById('tp-fill').style.width=pct+'%';
  document.getElementById('tp-text').textContent=pct+'% ('+done+'/'+total+')';
}}
function toggleCheck(cb){{
  cb.classList.toggle('checked');
  const txt=cb.nextElementSibling;
  if(txt)txt.classList.toggle('checked');
  const id=cb.closest('.check-item')?.dataset?.id;
  const p=loadProgress();
  if(id)p[id]=cb.classList.contains('checked');
  saveProgress(p);
  updateProgressBar();
}}
function goPhase(n){{
  if(n<0||n>=PHASES)return;
  document.querySelectorAll('.phase-section').forEach((el,i)=>el.style.display=i===n?'block':'none');
  document.querySelectorAll('.sb-item').forEach((el,i)=>el.classList.toggle('active',i===n));
  document.getElementById('main').scrollTo(0,0);
}}
function copyBlock(btn){{
  const pre=btn.closest('.terminal').querySelector('.t-body');
  navigator.clipboard.writeText(pre.textContent).then(()=>{{btn.textContent='copied';setTimeout(()=>btn.textContent='copy',1500)}});
}}
function setFilter(cat){{
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.toggle('active',b.dataset.filter===cat));
  document.querySelectorAll('.check-item').forEach(el=>{{
    el.style.display=(cat==='all'||el.dataset.cat===cat)?'flex':'none';
  }});
}}
function exportProgress(){{
  const blob=new Blob([JSON.stringify(loadProgress(),null,2)],{{type:'application/json'}});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download='bexo-build-progress.json';
  a.click();
}}
document.addEventListener('DOMContentLoaded',()=>{{
  const p=mergeBaseline(loadProgress());
  saveProgress(p);
  document.querySelectorAll('.check-item').forEach(el=>{{
    if(p[el.dataset.id]){{
      el.querySelector('.cb').classList.add('checked');
      el.querySelector('.ci-text')?.classList.add('checked');
    }}
  }});
  updateProgressBar();
  goPhase(7);
}});
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
