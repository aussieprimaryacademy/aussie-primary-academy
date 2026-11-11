#!/usr/bin/env python3
"""Replace homepage-only year/subject menu anchors with dedicated site hubs."""
from pathlib import Path
import os
import re

ROOT = Path(__file__).resolve().parent.parent
YEAR_LINK = re.compile(r'href=(["\'])(?:\.\./)*index\.html#years\1')
SUBJECT_LINK = re.compile(r'href=(["\'])(?:\.\./)*index\.html#subjects\1')


def main():
    changed = 0
    scanned = 0
    for page in sorted(ROOT.rglob("*.html")):
        relative = page.relative_to(ROOT)
        if ".git" in relative.parts:
            continue
        scanned += 1
        year_href = Path(os.path.relpath(ROOT / "year-levels.html", page.parent)).as_posix()
        subject_href = Path(os.path.relpath(ROOT / "subjects.html", page.parent)).as_posix()
        content = page.read_text(encoding="utf-8", errors="ignore")
        updated = YEAR_LINK.sub(lambda match: f'href="{year_href}"', content)
        updated = SUBJECT_LINK.sub(lambda match: f'href="{subject_href}"', updated)
        if updated != content:
            page.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"Scanned {scanned} HTML pages; updated navigation links in {changed} pages.")


if __name__ == "__main__":
    main()
