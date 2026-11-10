#!/usr/bin/env python3
"""Set worksheet landing-page language to the English locale for its resource region.

Only the HTML lang attribute is changed. Page copy, titles, canonicals, links,
download tracking, and worksheet content are left untouched.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "pages"
LANG_ATTRIBUTE = re.compile(r'(<html[^>]*lang=")([^"]+)(")', re.I)


def expected_language(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    filename = path.name.lower()
    is_usa = "usa" in parts or filename.startswith(("us-", "usa-"))
    return "en-US" if is_usa else "en-AU"


def main() -> int:
    changed = 0
    unchanged = 0
    missing = []
    unusual = []

    for path in sorted(PAGES.rglob("*.html")):
        html = path.read_text(encoding="utf-8")
        match = LANG_ATTRIBUTE.search(html)
        if not match:
            missing.append(path.relative_to(ROOT).as_posix())
            continue

        current = match.group(2)
        target = expected_language(path)
        if current == target:
            unchanged += 1
            continue
        if current.lower() not in {"en", "en-au", "en-us"}:
            unusual.append(f"{path.relative_to(ROOT).as_posix()}: {current}")
            continue

        updated = html[:match.start(2)] + target + html[match.end(2):]
        path.write_text(updated, encoding="utf-8")
        changed += 1

    print(f"Worksheet pages updated: {changed}")
    print(f"Already correct: {unchanged}")
    print(f"Missing lang attribute: {len(missing)}")
    print(f"Unusual locales left for review: {len(unusual)}")

    if missing or unusual:
        for item in (missing + unusual)[:50]:
            print(f"REVIEW: {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
