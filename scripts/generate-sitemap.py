#!/usr/bin/env python3
"""Generate a sitemap from public HTML pages without content-length or text-duplicate filtering.

Short pages and pages with repeated visible copy remain eligible. Those signals
belong in editorial review, not automatic sitemap exclusion. Explicit noindex
directives and known non-public paths/files are still excluded.
"""
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from subprocess import run
from xml.sax.saxutils import escape
import re
import xml.etree.ElementTree as ET

BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_NAMES = {"404.html", "email-thank-you.html", "google99305cdd54a8d1be.html"}
EXCLUDED_DIRS = {".git", ".github", "scripts", "assets", "css", "js"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        attrs = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() in {"script", "style", "noscript"}:
            self.skip_depth += 1
        if tag.lower() == "meta" and attrs.get("name", "").strip().lower() == "robots":
            directives = {item.strip().lower() for item in attrs.get("content", "").split(",")}
            if "noindex" in directives:
                self.noindex = True

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        if not self.skip_depth:
            self.parts.append(data)


def parse_page(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    visible = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return parser.noindex, visible


def is_excluded_path(path):
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return True
    if path.name in EXCLUDED_NAMES:
        return True
    if " " in path.name and not (path.name == "index.html" and path.parent == ROOT):
        return True
    return False


def collect_pages():
    pages = []
    for path in sorted(ROOT.rglob("*.html")):
        if is_excluded_path(path):
            continue
        noindex, _ = parse_page(path)
        if noindex:
            continue
        pages.append(path)
    return pages


def git_lastmod(path):
    try:
        value = run(
            ["git", "log", "-1", "--format=%cs", "--", str(path.relative_to(ROOT))],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout.strip()
        date.fromisoformat(value)
        return value
    except Exception:
        return None


def write_sitemap(pages):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in sorted(pages, key=lambda item: (item != ROOT / "index.html", item.as_posix())):
        rel = path.relative_to(ROOT).as_posix()
        loc = BASE if rel == "index.html" else BASE + rel
        lines.extend(["  <url>", f"    <loc>{escape(loc)}</loc>"])
        lastmod = git_lastmod(path)
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(pages)


if __name__ == "__main__":
    pages = collect_pages()
    count = write_sitemap(pages)
    sitemap_root = ET.parse(ROOT / "sitemap.xml").getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [
        node.text.strip()
        for node in sitemap_root.findall(".//sm:loc", ns)
        if node.text and node.text.strip()
    ]
    if len(urls) != count or len(urls) != len(set(urls)):
        raise SystemExit("ERROR: sitemap URL count does not match eligible pages or contains duplicates.")
    if BASE not in urls:
        raise SystemExit("ERROR: canonical homepage URL is missing from sitemap.")
    print(f"Generated sitemap.xml with {count} eligible public HTML URLs.")
    print("Automatic content-length and duplicate-visible-text exclusions: disabled.")
    print("XML validation passed.")
