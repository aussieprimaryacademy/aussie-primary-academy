#!/usr/bin/env python3
"""Check live HTTP responses for every repository HTML/PDF and internal HTML/PDF link.

This is a live deployment audit, not a source-only existence check. It records
redirect chains and verifies the terminal response without downloading PDF bodies.
"""
from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
HOST = "aussieprimaryacademy.github.io"
PREFIX = "/aussie-primary-academy/"
TIMEOUT = 25
RETRIES = 3
WORKERS = 6
REDIRECTS = {301, 302, 303, 307, 308}
TRANSIENT = {408, 425, 429, 500, 502, 503, 504}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


OPENER = build_opener(NoRedirect())


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"a", "link", "iframe", "source", "video", "audio"}:
            value = attrs.get("href")
            if value:
                self.values.append(value)
        if tag in {"img", "iframe", "source", "video", "audio"}:
            value = attrs.get("src")
            if value:
                self.values.append(value)


def normalise_url(url: str) -> str:
    parts = urlsplit(url)
    # Query strings and fragments do not change the resource being tested.
    path = quote(unquote(parts.path), safe="/:@-._~!$&'()*+,;=%")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def internal_target(page_url: str, raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None
    joined = urljoin(page_url, raw)
    parts = urlsplit(joined)
    if parts.scheme not in {"http", "https"} or (parts.hostname or "").lower() != HOST:
        return None
    path = parts.path or "/"
    suffix = Path(unquote(path)).suffix.lower()
    if suffix not in {".html", ".pdf"} and not path.endswith("/"):
        return None
    return normalise_url(joined)


def collect_targets():
    targets = defaultdict(set)
    html_files = sorted(
        p for p in ROOT.rglob("*.html")
        if not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
    )
    pdf_files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")

    for path in html_files + pdf_files:
        rel = path.relative_to(ROOT).as_posix()
        url = BASE + quote(rel, safe="/:@-._~")
        targets[url].add(f"[repository file] {rel}")

    for page in html_files:
        rel = page.relative_to(ROOT).as_posix()
        page_url = BASE + quote(rel, safe="/:@-._~")
        parser = Links()
        try:
            parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            targets[f"LOCAL-READ-ERROR:{rel}"].add(str(exc))
            continue
        for raw in parser.values:
            target = internal_target(page_url, raw)
            if target:
                targets[target].add(rel)

    return targets, len(html_files), len(pdf_files)


def request_once(url: str, method: str):
    request = Request(
        url,
        method=method,
        headers={
            "User-Agent": "APA-Live-Link-Audit/1.0 (+https://aussieprimaryacademy.github.io/)",
            "Range": "bytes=0-0" if method == "GET" else "bytes=0-",
            "Accept": "text/html,application/pdf,*/*;q=0.8",
        },
    )
    try:
        response = OPENER.open(request, timeout=TIMEOUT)
        status = response.status
        location = response.headers.get("Location")
        response.close()
        return status, location, None
    except HTTPError as exc:
        location = exc.headers.get("Location") if exc.headers else None
        exc.close()
        return exc.code, location, None
    except (URLError, TimeoutError, OSError) as exc:
        return None, None, str(exc)


def check_url(url: str):
    if url.startswith("LOCAL-READ-ERROR:"):
        return {
            "url": url, "initial_status": "", "final_status": "",
            "redirect_chain": "", "final_url": "", "result": "SOURCE_READ_ERROR",
            "error": next(iter(targets[url])),
        }

    chain = []
    current = url
    visited = set()
    method = "HEAD"
    last_error = ""
    initial_status = None

    for hop in range(11):
        if current in visited:
            return {
                "url": url, "initial_status": initial_status or "",
                "final_status": "", "redirect_chain": " -> ".join(chain),
                "final_url": current, "result": "REDIRECT_LOOP",
                "error": "Redirect loop detected",
            }
        visited.add(current)

        status = location = error = None
        for attempt in range(RETRIES):
            status, location, error = request_once(current, method)
            if status == 405 and method == "HEAD":
                method = "GET"
                continue
            if status not in TRANSIENT and error is None:
                break
            last_error = error or f"HTTP {status}"
            if attempt < RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))

        if status is None:
            return {
                "url": url, "initial_status": initial_status or "",
                "final_status": "", "redirect_chain": " -> ".join(chain),
                "final_url": current, "result": "REQUEST_ERROR",
                "error": last_error or error or "Unknown request error",
            }

        if initial_status is None:
            initial_status = status
        chain.append(f"{status} {current}")

        if status in REDIRECTS:
            if not location:
                return {
                    "url": url, "initial_status": initial_status,
                    "final_status": status, "redirect_chain": " -> ".join(chain),
                    "final_url": current, "result": "REDIRECT_WITHOUT_LOCATION",
                    "error": "Redirect response did not include Location",
                }
            if hop == 10:
                return {
                    "url": url, "initial_status": initial_status,
                    "final_status": status, "redirect_chain": " -> ".join(chain),
                    "final_url": current, "result": "TOO_MANY_REDIRECTS",
                    "error": "More than 10 redirects",
                }
            current = urljoin(current, location)
            if (urlsplit(current).hostname or "").lower() != HOST:
                return {
                    "url": url, "initial_status": initial_status,
                    "final_status": status, "redirect_chain": " -> ".join(chain),
                    "final_url": current, "result": "REDIRECT_EXTERNAL",
                    "error": "Internal URL redirects outside the APA host",
                }
            method = "GET" if status == 303 else method
            continue

        result = "OK" if 200 <= status < 300 else (
            "TRANSIENT_HTTP" if status in TRANSIENT else "HTTP_ERROR"
        )
        return {
            "url": url, "initial_status": initial_status,
            "final_status": status, "redirect_chain": " -> ".join(chain),
            "final_url": current, "result": result, "error": last_error,
        }

    raise RuntimeError("Unexpected redirect handling exit")


def main():
    global targets
    targets, html_count, pdf_count = collect_targets()
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(check_url, url): url for url in targets}
        for future in as_completed(futures):
            row = future.result()
            row["sources"] = "; ".join(sorted(targets[row["url"]])[:12])
            row["source_count"] = len(targets[row["url"]])
            results.append(row)

    results.sort(key=lambda row: (row["result"] != "OK", row["url"]))
    counts = defaultdict(int)
    for row in results:
        counts[row["result"]] += 1

    report = {
        "scope": "Live HTTP check of all repository HTML/PDF files plus all internal HTML/PDF links found in HTML href/src attributes.",
        "base_url": BASE,
        "repository_html_files": html_count,
        "repository_pdf_files": pdf_count,
        "unique_urls_checked": len(results),
        "results": dict(sorted(counts.items())),
        "redirects": sum(1 for row in results if row["initial_status"] in REDIRECTS),
        "failures": sum(1 for row in results if row["result"] not in {"OK"}),
        "items": results,
    }
    Path("live-http-audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with Path("live-http-audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "url", "initial_status", "final_status", "redirect_chain",
            "final_url", "result", "error", "source_count", "sources",
        ])
        writer.writeheader()
        writer.writerows(results)

    summary = [
        "# APA live HTTP audit",
        "",
        f"- Repository HTML files: **{html_count:,}**",
        f"- Repository PDF files: **{pdf_count:,}**",
        f"- Unique live URLs checked: **{len(results):,}**",
        f"- Redirect responses followed: **{report['redirects']:,}**",
        "",
        "## Final response results",
    ]
    for key, value in sorted(counts.items()):
        summary.append(f"- **{key}:** {value:,}")
    summary += [
        "",
        "Redirects ending in a successful 2xx response are recorded but are not treated as broken.",
        "Transient HTTP errors are retried and reported separately; inspect them before changing site links.",
        "Full URL-by-URL evidence is in live-http-audit.csv and live-http-audit.json.",
    ]
    text = "\n".join(summary) + "\n"
    print(text)
    step_summary = Path(__import__("os").environ.get("GITHUB_STEP_SUMMARY", ""))
    if str(step_summary) not in {"", "."}:
        with step_summary.open("a", encoding="utf-8") as handle:
            handle.write(text)

    if any(row["result"] not in {"OK"} for row in results):
        raise SystemExit("Live HTTP audit found URLs requiring review; see uploaded reports.")


if __name__ == "__main__":
    main()
