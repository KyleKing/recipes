#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "playwright>=1.44",
#   "playwright-stealth>=1.0.6",
#   "browser-cookie3>=0.19",
#   "requests>=2.32",
# ]
# ///
"""Fetch a URL using a real browser to bypass bot-detection (403s, Cloudflare, etc.).

Usage:
    uv run scripts/fetch_with_browser.py <url> [options]

Options:
    --format html|text|json     Output format (default: html)
    --output FILE               Write to file instead of stdout
    --headful                   Show browser window (for interactive challenges)
    --channel chrome|msedge     Use installed Chrome/Edge instead of bundled Chromium
    --use-chrome-cookies        Use cookies from your Chrome profile (fast, no browser)
    --cdp [HOST:PORT]           Connect to an already-running Chrome with remote debugging
                                (default port 9222). See --cdp instructions below.
    --wait SECONDS              Extra wait after page load (default: 3s headless, 10s headful)

--- Cloudflare + VPN troubleshooting ---

Cloudflare's "Managed Challenge" is triggered by VPN IPs and cannot be solved headlessly.
Choose the approach that fits your situation:

Option A — Disable VPN (recommended):
    Disconnect VPN, then:
        uv run scripts/fetch_with_browser.py <url> --headful --channel chrome

Option B — Use existing Chrome session (VPN can stay on):
    1. Open Chrome normally (not via script) and navigate to the URL.
    2. Solve any CAPTCHA that appears until the page loads.
    3. Relaunch Chrome with remote debugging WHILE KEEPING YOUR SESSION:
         pkill -f "Google Chrome" && open -a "Google Chrome" --args --remote-debugging-port=9222 <url>
       Or if you don't want to restart Chrome, just run the script against your open tab:
         uv run scripts/fetch_with_browser.py <url> --cdp
       (Requires Chrome already launched with --remote-debugging-port=9222)
    4. The script connects to your real Chrome, finds the tab, and extracts the HTML.

Option C — Manual (always works, VPN can stay on):
    1. Open the page in Chrome and solve any CAPTCHA.
    2. In DevTools Console, run:
         copy(document.documentElement.outerHTML)
    3. Paste into a file and feed to the recipe parser.

--- CDP mode step-by-step ---
    # Step 1: Launch Chrome with remote debugging (closes existing Chrome)
    pkill -f "Google Chrome"; open -a "Google Chrome" --args --remote-debugging-port=9222

    # Step 2: Navigate to your URL in Chrome, solve any CAPTCHA

    # Step 3: Run this script with --cdp
    uv run scripts/fetch_with_browser.py <url> --cdp --format html --output /tmp/recipe.html
"""

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

_CLOUDFLARE_TITLES = {"just a moment", "access denied", "attention required", "checking your browser"}


def _is_cloudflare_blocked(title: str, status: int, html: str) -> bool:
    title_match = any(t in title.lower() for t in _CLOUDFLARE_TITLES)
    html_match = "challenges.cloudflare.com" in html or "cf-turnstile" in html
    return status in (403, 503) and (title_match or html_match)


def _diagnose_cloudflare(html: str) -> str:
    if "1020" in html:
        return "Error 1020: IP/VPN access rule — your IP is blocked site-wide. Disable VPN."
    if "'managed'" in html or '"managed"' in html:
        return "Managed Challenge (visual CAPTCHA for suspicious IPs like VPNs). See --cdp or Option A/B/C above."
    if "1010" in html:
        return "Error 1010: browser fingerprint mismatch. Try --headful --channel chrome."
    if "cf-turnstile" in html or "challenges.cloudflare.com" in html:
        return "Cloudflare Turnstile challenge. Try --headful --channel chrome (disable VPN first)."
    return "Cloudflare challenge. See the troubleshooting section in --help."


def _domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).hostname or ""


def fetch_with_browser(url: str, headless: bool = True, channel: str | None = None, extra_wait: int | None = None) -> dict:
    wait_ms = (extra_wait * 1000) if extra_wait is not None else (3_000 if headless else 10_000)
    with sync_playwright() as pw:
        launch_kwargs: dict = {"headless": headless}
        if channel:
            launch_kwargs["channel"] = channel
        browser = pw.chromium.launch(**launch_kwargs)
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            },
        )
        page = ctx.new_page()
        Stealth().apply_stealth_sync(page)
        response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(wait_ms)
        status = response.status if response else 0
        html = page.content()
        title = page.title()
        text = page.evaluate("() => document.body.innerText")
        browser.close()

    return {"url": url, "status": status, "title": title, "html": html, "text": text}


def fetch_with_chrome_cookies(url: str) -> dict:
    import browser_cookie3

    jar = browser_cookie3.chrome(domain_name=_domain(url))
    session = requests.Session()
    session.cookies.update(jar)
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": url,
    })
    resp = session.get(url, timeout=15)

    # Follow JS redirects (e.g. Kinsta's ki-cf-botcl check)
    if resp.status_code in (200, 403) and (m := re.search(r'window\.location.*?["\']([^"\']+ki-cf-botcl[^"\']*)["\']', resp.text)):
        redirect_url = m.group(1)
        if not redirect_url.startswith("http"):
            redirect_url = urljoin(url, redirect_url)
        resp = session.get(redirect_url, timeout=15)

    return {
        "url": resp.url,
        "status": resp.status_code,
        "title": "",
        "html": resp.text,
        "text": resp.text,
    }


def fetch_with_cdp(url: str, cdp_address: str = "localhost:9222", extra_wait: int | None = None) -> dict:
    """Connect to an already-running Chrome with --remote-debugging-port and extract the page."""
    wait_ms = (extra_wait * 1000) if extra_wait is not None else 2_000
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://{cdp_address}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()

        # Find existing tab with the target URL, or open a new one
        target_page = None
        for page in ctx.pages:
            if url in page.url or _domain(url) in page.url:
                target_page = page
                break

        if target_page is None:
            target_page = ctx.new_page()
            target_page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            target_page.wait_for_timeout(wait_ms)

        status = 200
        html = target_page.content()
        title = target_page.title()
        text = target_page.evaluate("() => document.body.innerText")
        browser.close()

    return {"url": url, "status": status, "title": title, "html": html, "text": text}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch URL via real browser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument("--output", "-o", help="Write output to file instead of stdout")
    parser.add_argument(
        "--format",
        choices=["html", "text", "json"],
        default="html",
        help="Output format (default: html)",
    )
    parser.add_argument("--headful", action="store_true", help="Show browser window")
    parser.add_argument(
        "--channel",
        choices=["chrome", "msedge"],
        help="Use installed Chrome/Edge instead of bundled Chromium",
    )
    parser.add_argument(
        "--use-chrome-cookies",
        action="store_true",
        help="Use cookies from your Chrome profile (fast, no browser launch)",
    )
    parser.add_argument(
        "--cdp",
        nargs="?",
        const="localhost:9222",
        metavar="HOST:PORT",
        help="Connect to an already-running Chrome with --remote-debugging-port (default: localhost:9222)",
    )
    parser.add_argument(
        "--wait",
        type=int,
        metavar="SECONDS",
        help="Extra wait time after page load",
    )
    args = parser.parse_args()

    if args.cdp:
        result = fetch_with_cdp(args.url, cdp_address=args.cdp, extra_wait=args.wait)
    elif args.use_chrome_cookies:
        result = fetch_with_chrome_cookies(args.url)
    else:
        result = fetch_with_browser(args.url, headless=not args.headful, channel=args.channel, extra_wait=args.wait)

    blocked = _is_cloudflare_blocked(result["title"], result["status"], result["html"])
    if blocked:
        diagnosis = _diagnose_cloudflare(result["html"])
        print(f"Cloudflare blocked: {diagnosis}", file=sys.stderr)
    elif result["status"] >= 400:
        print(f"HTTP {result['status']}: {result['title']}", file=sys.stderr)

    match args.format:
        case "html":
            content = result["html"]
        case "text":
            content = result.get("text") or result["html"]
        case "json":
            content = json.dumps({k: v for k, v in result.items() if k != "html"}, indent=2)

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Wrote {len(content)} chars → {args.output}", file=sys.stderr)
        print(f"Status: {result['status']}  Title: {result['title']!r}", file=sys.stderr)
    else:
        print(content)


if __name__ == "__main__":
    main()
