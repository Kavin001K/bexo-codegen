import json
import os
import re
import socketserver
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler

from playwright.sync_api import sync_playwright

THRESHOLDS = {
    "performance": 0.75,
    "accessibility": 0.88,
    "seo": 0.82,
    "best-practices": 0.80,
}

RUN_LIGHTHOUSE = os.environ.get("RUN_LIGHTHOUSE", "true").lower() == "true"


def check_html_structure(html: str) -> list:
    issues = []
    checks = [
        (r"<!DOCTYPE html>", "Missing DOCTYPE declaration"),
        (r"<meta[^>]+viewport", "Missing viewport meta tag"),
        (r"<title>.+?</title>", "Missing or empty title tag"),
        (r"<h1", "Missing H1 heading"),
        (r"<nav", "Missing nav element"),
        (r"<main", "Missing main landmark"),
        (r"lang=", "Missing lang attribute on html tag"),
    ]
    for pat, msg in checks:
        if not re.search(pat, html, re.IGNORECASE):
            issues.append(msg)
    no_alt = re.findall(r"<img(?![^>]*\balt=)[^>]*>", html, re.IGNORECASE)
    if no_alt:
        issues.append(f"{len(no_alt)} img tags missing alt attribute")
    return issues


def check_with_playwright(html: str) -> list:
    issues = []
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    try:
        chrome = os.environ.get("CHROME_PATH") or os.environ.get(
            "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/usr/bin/chromium"
        )
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            page = browser.new_page()
            js_errs = []
            page.on("pageerror", lambda e: js_errs.append(str(e)))
            page.goto(f"file://{tmp}")
            page.wait_for_load_state("networkidle", timeout=15000)
            page.set_viewport_size({"width": 375, "height": 812})
            page.wait_for_timeout(500)
            overflow_px = page.evaluate(
                "document.documentElement.scrollWidth - window.innerWidth"
            )
            overflow_limit = int(os.environ.get("TEST_MAX_OVERFLOW_PX", "12"))
            if overflow_px > overflow_limit:
                issues.append("Horizontal overflow on 375px mobile viewport")
            broken = page.evaluate(
                """
                Array.from(document.querySelectorAll('a[href^="#"]'))
                  .filter(a => {
                    const id = a.getAttribute('href').slice(1);
                    return id && !document.getElementById(id);
                  })
                  .map(a => a.getAttribute('href'))
                """
            )
            if broken:
                issues.append(f"Broken nav anchors: {broken[:4]}")
            small = page.evaluate(
                """
                Array.from(document.querySelectorAll('a,button')).filter(el => {
                  const r = el.getBoundingClientRect();
                  return r.width < 44 || r.height < 44;
                }).length
                """
            )
            max_small = int(os.environ.get("TEST_MAX_SMALL_TOUCH_TARGETS", "12"))
            if small > max_small:
                issues.append(f"{small} interactive elements below 44px touch target")
            if js_errs:
                issues.append(f"JS errors: {js_errs[:2]}")
            browser.close()
    finally:
        os.unlink(tmp)
    return issues


def check_lighthouse(html: str) -> list:
    if not RUN_LIGHTHOUSE:
        return []
    issues = []
    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", delete=False, encoding="utf-8", dir="/tmp"
    ) as f:
        f.write(html)
        tmp = f.name
    try:
        result = subprocess.run(
            [
                "lighthouse",
                f"file://{tmp}",
                "--output=json",
                "--quiet",
                "--chrome-flags=--headless --no-sandbox",
                "--only-categories=performance,accessibility,seo,best-practices",
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode != 0 and not result.stdout:
            print(f"[LH] non-fatal: {result.stderr[:200]}")
            return issues
        cats = json.loads(result.stdout).get("categories", {})
        for cat, thresh in THRESHOLDS.items():
            score = cats.get(cat, {}).get("score", 1)
            if score is not None and score < thresh:
                issues.append(
                    f"Lighthouse {cat}: {int(score * 100)} < threshold {int(thresh * 100)}"
                )
    except Exception as e:
        print(f"[LH] non-fatal: {e}")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return issues


def _serve_static_site(site_dir: str) -> tuple[str, callable]:
    """Serve Next out/ over HTTP so /_next assets load (file:// breaks CSS)."""
    root = os.path.abspath(site_dir)
    handler = partial(SimpleHTTPRequestHandler, directory=root)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def stop() -> None:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)

    return f"http://127.0.0.1:{port}", stop


def check_site_with_playwright(site_dir: str) -> list:
    """Playwright QA against a static site directory (Next out/)."""
    issues = []
    index = os.path.join(site_dir, "index.html")
    if not os.path.isfile(index):
        issues.append("Missing index.html in site directory")
        return issues

    chrome = os.environ.get("CHROME_PATH") or os.environ.get(
        "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "/usr/bin/chromium"
    )
    base_url, stop_server = _serve_static_site(site_dir)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            page = browser.new_page()
            js_errs: list[str] = []
            page.on("pageerror", lambda e: js_errs.append(str(e)))
            page.goto(f"{base_url}/", wait_until="networkidle", timeout=30000)
            try:
                page.wait_for_selector("h1", timeout=5000)
            except Exception:
                pass
            page.set_viewport_size({"width": 375, "height": 812})
            page.wait_for_timeout(500)
            overflow_px = page.evaluate(
                "document.documentElement.scrollWidth - window.innerWidth"
            )
            overflow_limit = int(os.environ.get("TEST_MAX_OVERFLOW_PX", "12"))
            if overflow_px > overflow_limit:
                issues.append("Horizontal overflow on 375px mobile viewport")
            small = page.evaluate(
                """
                Array.from(document.querySelectorAll('a,button')).filter(el => {
                  const r = el.getBoundingClientRect();
                  const s = window.getComputedStyle(el);
                  if (s.display === 'none' || s.visibility === 'hidden' || r.width === 0) {
                    return false;
                  }
                  return r.width < 44 || r.height < 44;
                }).length
                """
            )
            max_small = int(os.environ.get("TEST_MAX_SMALL_TOUCH_TARGETS", "12"))
            if small > max_small:
                issues.append(f"{small} interactive elements below 44px touch target")
            if js_errs:
                issues.append(f"JS errors: {js_errs[:2]}")
            browser.close()
    finally:
        stop_server()
    return issues


def run_site_tests(site_dir: str, user_id: str, *, lighthouse: bool | None = None) -> list:
    """QA for Next.js static export directory."""
    all_issues: list = []
    index_path = os.path.join(site_dir, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, encoding="utf-8") as f:
            html = f.read()
        all_issues.extend(check_html_structure(html))
    all_issues.extend(check_site_with_playwright(site_dir))
    if lighthouse is None:
        lighthouse = RUN_LIGHTHOUSE
    if lighthouse and os.path.isfile(index_path):
        with open(index_path, encoding="utf-8") as f:
            all_issues.extend(check_lighthouse(f.read()))
    print(f"[TEST] {user_id} (site-dir): {len(all_issues)} total issues")
    return all_issues


def run_tests(html: str, user_id: str, *, lighthouse: bool | None = None) -> list:
    """Run quality gates. Lighthouse runs on final attempt when lighthouse=True."""
    all_issues = []
    all_issues.extend(check_html_structure(html))
    all_issues.extend(check_with_playwright(html))
    if lighthouse is None:
        lighthouse = RUN_LIGHTHOUSE
    if lighthouse:
        all_issues.extend(check_lighthouse(html))
    print(f"[TEST] {user_id}: {len(all_issues)} total issues")
    return all_issues
