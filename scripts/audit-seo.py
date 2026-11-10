#!/usr/bin/env python3
"""Read-only SEO audit. Reports indexable-page SEO issues separately from informational checks."""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter, defaultdict
import sys

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"google99305cdd54a8d1be.html"}

class Audit(HTMLParser):
    def __init__(self):
        super().__init__()
        self.titles = []
        self.descriptions = []
        self.canonicals = []
        self.h1_count = 0
        self.lang = None
        self.viewport_count = 0
        self.noindex = False
        self._title = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang")
        elif tag == "title":
            self._title = ""
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.descriptions.append(attrs.get("content", ""))
            elif name == "viewport":
                self.viewport_count += 1
            elif name == "robots" and "noindex" in attrs.get("content", "").lower():
                self.noindex = True
        elif tag == "link" and attrs.get("rel", "").lower() == "canonical":
            self.canonicals.append(attrs.get("href", ""))

    def handle_data(self, data):
        if self._title is not None:
            self._title += data

    def handle_endtag(self, tag):
        if tag == "title" and self._title is not None:
            self.titles.append(self._title.strip())
            self._title = None

def main():
    pages = {}
    for path in sorted(ROOT.rglob("*.html")):
        if {".git", ".github"} & set(path.parts) or path.name in SKIP:
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        audit = Audit()
        audit.feed(html)
        if audit.noindex:
            continue
        pages[str(path.relative_to(ROOT))] = (audit, html)

    title_counts = Counter(a.titles[0] for a, _ in pages.values() if len(a.titles) == 1 and a.titles[0])
    description_counts = Counter(a.descriptions[0] for a, _ in pages.values() if len(a.descriptions) == 1 and a.descriptions[0])
    seo = defaultdict(list)
    info = defaultdict(list)

    for relative_path, (audit, html) in pages.items():
        canonical = audit.canonicals
        if not (len(canonical) == 1 and canonical[0].startswith("https://") and "?" not in canonical[0] and not canonical[0].endswith("/index.html")):
            seo["canonical missing, duplicate or invalid"].append(relative_path)

        if len(audit.titles) != 1 or not audit.titles[0]:
            seo["title missing or multiple"].append(relative_path)
        else:
            if len(audit.titles[0]) >= 60:
                seo["title 60+ characters (review)"].append(relative_path)
            if title_counts[audit.titles[0]] > 1:
                seo["duplicate title"].append(relative_path)

        if len(audit.descriptions) != 1 or not audit.descriptions[0]:
            seo["description missing or multiple"].append(relative_path)
        else:
            if len(audit.descriptions[0]) >= 160:
                seo["description 160+ characters (review)"].append(relative_path)
            if description_counts[audit.descriptions[0]] > 1:
                seo["duplicate description"].append(relative_path)

        if audit.h1_count != 1:
            seo["not exactly one H1"].append(relative_path)
        relative = Path(relative_path)
        parts = {part.lower() for part in relative.parts}
        filename = relative.name.lower()
        expected_lang = "en-US" if "usa" in parts or filename.startswith(("us-", "usa-")) else "en-AU"
        if audit.lang != expected_lang:
            seo[f"lang is not {expected_lang}"].append(relative_path)

        if audit.viewport_count != 1:
            info["viewport count is not one"].append(relative_path)
        if "G-41Q0QR6ZHD" not in html:
            info["GA4 ID not found"].append(relative_path)

    affected = {path for paths in seo.values() for path in paths}
    print(f"Indexable HTML pages audited: {len(pages)}")
    print(f"Pages with at least one SEO issue/review item: {len(affected)}")
    for category, paths in sorted(seo.items(), key=lambda item: -len(item[1])):
        print(f"{category}: {len(paths)}")
    print("Informational checks (not SEO failures):", {key: len(value) for key, value in info.items()} or "none")
    if "-v" in sys.argv:
        for category, paths in seo.items():
            print(f"\n[{category}]")
            print("\n".join(paths))

if __name__ == "__main__":
    main()
