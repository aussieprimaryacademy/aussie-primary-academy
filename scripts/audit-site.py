#!/usr/bin/env python3
"""Report internal-link, sitemap and basic SEO metadata issues without network access."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import posixpath
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SITE_HOST = "aussieprimaryacademy.github.io"
PROJECT_PATH = "/aussie-primary-academy"
SITE_BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
UTILITY_PAGES = {"404.html", "email-thank-you.html", "google99305cdd54a8d1be.html"}
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.lang = ""
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.h1_count = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "html":
            self.lang = values.get("lang", "")
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "meta" and values.get("name", "").lower() == "description":
            self.description = values.get("content", "").strip()
        if tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href", "").strip()
        for attr in ("href", "src", "action", "poster"):
            value = values.get(attr, "").strip()
            if value:
                self.links.append((attr, value))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def target_for(page: Path, raw_url: str) -> tuple[Path | None, str | None]:
    value = raw_url.strip()
    if not value or value.startswith("#"):
        return None, None
    parsed = urlparse(value)
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
        return None, None
    if value.startswith("//") and not parsed.netloc:
        return None, None

    decoded_path = unquote(parsed.path)
    if parsed.netloc:
        if parsed.hostname != SITE_HOST:
            return None, None
        if decoded_path == PROJECT_PATH:
            relative = ""
        elif decoded_path.startswith(PROJECT_PATH + "/"):
            relative = decoded_path[len(PROJECT_PATH) + 1 :]
        else:
            return None, f"same-host URL is missing project prefix {PROJECT_PATH}/"
    elif decoded_path.startswith("/"):
        if decoded_path == PROJECT_PATH:
            relative = ""
        elif decoded_path.startswith(PROJECT_PATH + "/"):
            relative = decoded_path[len(PROJECT_PATH) + 1 :]
        else:
            return None, f"root-relative URL is missing project prefix {PROJECT_PATH}/"
    else:
        if not decoded_path:
            return None, None
        relative = posixpath.normpath(
            posixpath.join(page.parent.relative_to(ROOT).as_posix(), decoded_path)
        )
        if relative == ".":
            relative = ""

    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None, "path escapes repository root"
    if candidate.is_dir():
        candidate = candidate / "index.html"
    elif str(candidate).endswith(("/", "\\")):
        candidate = candidate / "index.html"
    if not candidate.exists():
        return candidate, "target file does not exist"
    return candidate, None


def expected_sitemap_urls() -> set[str]:
    expected: set[str] = {SITE_BASE}
    for folder in ("blog", "pages"):
        base = ROOT / folder
        if not base.exists():
            continue
        for page in base.rglob("*.html"):
            if page.name in UTILITY_PAGES or " " in page.name:
                continue
            rel = page.relative_to(ROOT).as_posix()
            if page.name.lower() == "index.html":
                rel = page.parent.relative_to(ROOT).as_posix().rstrip("/") + "/"
            expected.add(SITE_BASE + rel)

    for page in ROOT.glob("*.html"):
        if page.name in UTILITY_PAGES or page.name.lower() == "index.html" or " " in page.name:
            continue
        expected.add(SITE_BASE + page.name)
    return expected


def main() -> int:
    broken_links: list[str] = []
    missing = {"title": [], "description": [], "canonical": [], "h1": [], "lang": []}
    html_pages = sorted(ROOT.rglob("*.html"))
    checked_links = 0

    for page in html_pages:
        rel_page = page.relative_to(ROOT)
        if ".git" in rel_page.parts or ".github" in rel_page.parts or "scripts" in rel_page.parts:
            continue
        text = page.read_text(encoding="utf-8", errors="ignore")
        parser = PageParser()
        parser.feed(text)
        parser.close()

        if page.name not in UTILITY_PAGES:
            for key, value in (
                ("title", parser.title.strip()),
                ("description", parser.description),
                ("canonical", parser.canonical),
                ("h1", parser.h1_count),
                ("lang", parser.lang),
            ):
                if not value:
                    missing[key].append(str(rel_page))

        for attr, raw_url in parser.links:
            checked_links += 1
            target, error = target_for(page, raw_url)
            if error:
                broken_links.append(f"{rel_page} [{attr}={raw_url!r}] -> {error}")

    sitemap_path = ROOT / "sitemap.xml"
    sitemap_urls: set[str] = set()
    try:
        tree = ET.parse(sitemap_path)
        sitemap_urls = {
            node.text.strip()
            for node in tree.findall(".//sm:loc", SITEMAP_NS)
            if node.text and node.text.strip()
        }
        sitemap_error = ""
    except (ET.ParseError, OSError) as exc:
        sitemap_error = str(exc)

    expected_urls = expected_sitemap_urls()
    sitemap_missing = sorted(expected_urls - sitemap_urls)
    sitemap_extra = sorted(sitemap_urls - expected_urls)

    print(f"HTML pages scanned: {len(html_pages)}")
    print(f"Internal links/assets checked: {checked_links}")
    print(f"Broken internal links or assets: {len(broken_links)}")
    for item in broken_links[:100]:
        print(f"BROKEN LINK: {item}")
    if len(broken_links) > 100:
        print(f"... plus {len(broken_links) - 100} additional broken links")

    for key, items in missing.items():
        print(f"Pages missing {key}: {len(items)}")
        for item in items[:30]:
            print(f"MISSING {key.upper()}: {item}")
        if len(items) > 30:
            print(f"... plus {len(items) - 30} additional pages")

    if sitemap_error:
        print(f"SITEMAP PARSE ERROR: {sitemap_error}")
    else:
        print(f"Sitemap URLs: {len(sitemap_urls)}")
        print(f"Expected canonical URLs missing from sitemap: {len(sitemap_missing)}")
        for item in sitemap_missing[:50]:
            print(f"SITEMAP MISSING: {item}")
        print(f"Unexpected sitemap URLs: {len(sitemap_extra)}")
        for item in sitemap_extra[:50]:
            print(f"SITEMAP EXTRA: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
