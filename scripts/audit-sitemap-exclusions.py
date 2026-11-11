#!/usr/bin/env python3
"""Read-only sitemap audit: distinguish hard exclusions from review signals."""
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
SITEMAP = ROOT / "sitemap.xml"
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


def page_url(path):
    rel = path.relative_to(ROOT).as_posix()
    return BASE if rel == "index.html" else BASE + rel


def main():
    hard_exclusions = defaultdict(list)
    review_signals = defaultdict(list)
    eligible = []
    text_seen = {}

    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            hard_exclusions["non-public directory"].append(rel.as_posix())
            continue
        if path.name in EXCLUDED_NAMES:
            hard_exclusions["reserved/non-public filename"].append(rel.as_posix())
            continue
        if " " in path.name and not (path.name == "index.html" and path.parent == ROOT):
            hard_exclusions["filename contains spaces"].append(rel.as_posix())
            continue

        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
        if parser.noindex:
            hard_exclusions["explicit robots noindex"].append(rel.as_posix())
            continue

        visible = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
        words = re.findall(r"\b[\w'-]+\b", visible)
        if len(words) < 80:
            review_signals["under 80 visible-text words (informational only)"].append(
                f"{rel.as_posix()} ({len(words)} words)"
            )

        normalized = re.sub(r"[^a-z0-9]+", " ", visible.lower()).strip()
        if normalized:
            if normalized in text_seen:
                review_signals["duplicate visible text (informational only)"].append(
                    f"{rel.as_posix()} duplicates {text_seen[normalized]}"
                )
            else:
                text_seen[normalized] = rel.as_posix()
        eligible.append(path)

    sitemap_root = ET.parse(SITEMAP).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    existing_urls = {
        node.text.strip()
        for node in sitemap_root.findall(".//sm:loc", ns)
        if node.text and node.text.strip()
    }
    eligible_urls = {page_url(path) for path in eligible}
    missing_urls = sorted(eligible_urls - existing_urls)
    stale_urls = sorted(existing_urls - eligible_urls)

    print(f"Eligible public HTML pages (noindex and hard exclusions applied): {len(eligible_urls)}")
    print(f"URLs currently in sitemap.xml: {len(existing_urls)}")
    print(f"Eligible URLs missing from current sitemap: {len(missing_urls)}")
    for url in missing_urls:
        print(f"  MISSING: {url}")
    print(f"Existing sitemap URLs no longer eligible: {len(stale_urls)}")
    for url in stale_urls:
        print(f"  STALE: {url}")

    print("\nHARD EXCLUSIONS (these are the only automatic exclusions):")
    for reason, entries in sorted(hard_exclusions.items()):
        print(f"  {reason}: {len(entries)}")
        for entry in entries:
            print(f"    {entry}")

    print("\nREVIEW SIGNALS ONLY (do not exclude these URLs):")
    for reason, entries in sorted(review_signals.items()):
        print(f"  {reason}: {len(entries)}")
        for entry in entries:
            print(f"    {entry}")

    print("\nRead-only audit complete; no files were changed.")


if __name__ == "__main__":
    main()
