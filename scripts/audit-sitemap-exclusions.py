#!/usr/bin/env python3
"""Read-only inventory using the same exclusion rules as generate-sitemap.py."""
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
MIN_WORDS = 80
EXCLUDED_NAMES = {"404.html", "email-thank-you.html", "google99305cdd54a8d1be.html"}
EXCLUDED_DIRS = {".git", ".github", "scripts", "assets", "css", "js"}

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def main():
    reasons = defaultdict(list)
    candidates = []
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        name = path.name
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            reasons["excluded directory"].append(rel.as_posix())
            continue
        if name in EXCLUDED_NAMES:
            reasons["excluded filename"].append(rel.as_posix())
            continue
        if " " in name or (name == "index.html" and path.parent == ROOT):
            if name == "index.html" and path.parent == ROOT:
                pass  # The root homepage is represented by the folder URL.
            else:
                reasons["filename contains spaces"].append(rel.as_posix())
                continue

        html = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*noindex', html, re.I):
            reasons["noindex"].append(rel.as_posix())
            continue

        parser = TextExtractor()
        parser.feed(html)
        text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
        words = re.findall(r"\b[\w'-]+\b", text)
        if len(words) < MIN_WORDS:
            reasons["under 80 visible-text words"].append(f"{rel.as_posix()} ({len(words)} words)")
            continue
        normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if not normalized:
            continue
        candidates.append((path, normalized))

    seen = {}
    kept = []
    for path, normalized in sorted(
        candidates,
        key=lambda item: (
            len(item[0].relative_to(ROOT).as_posix()),
            item[0].as_posix(),
        ),
    ):
        rel = path.relative_to(ROOT).as_posix()
        if normalized in seen:
            reasons["duplicate visible text"].append(f"{rel} duplicates {seen[normalized]}")
        else:
            seen[normalized] = rel
            kept.append(rel)

    total_excluded = sum(len(entries) for entries in reasons.values())
    print(f"Eligible after filters: {len(kept)}")
    print(f"Potential sitemap exclusions: {total_excluded}")
    for reason in sorted(reasons):
        entries = reasons[reason]
        print(f"\n{reason}: {len(entries)}")
        for entry in entries:
            print(f"  {entry}")
    print("\nThis is a read-only report. It does not modify sitemap.xml or any page.")

if __name__ == "__main__":
    main()
