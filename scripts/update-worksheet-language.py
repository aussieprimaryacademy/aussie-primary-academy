#!/usr/bin/env python3
"""Set the correct English locale on every eligible public HTML page.

Australian resources use en-AU; USA resources use en-US. Only the html lang
attribute is changed. Page copy, metadata, canonicals, links, and PDFs are
left untouched. Explicit noindex and non-public pages are skipped.
"""
from pathlib import Path
import re
import importlib.util

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "sitemap_generator", ROOT / "scripts" / "generate-sitemap.py"
)
SITEMAP_GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SITEMAP_GENERATOR)
LANG_ATTRIBUTE = re.compile(r'(<html\b[^>]*\blang\s*=\s*")([^"]+)(")', re.I)


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

    for path in sorted(ROOT.rglob("*.html")):
        if SITEMAP_GENERATOR.is_excluded_path(path):
            continue
        noindex, _ = SITEMAP_GENERATOR.parse_page(path)
        if noindex:
            continue

        html = path.read_text(encoding="utf-8")
        match = LANG_ATTRIBUTE.search(html)
        relative = path.relative_to(ROOT).as_posix()
        if not match:
            missing.append(relative)
            continue

        current = match.group(2)
        target = expected_language(path)
        if current == target:
            unchanged += 1
            continue
        if current.lower() not in {"en", "en-au", "en-us"}:
            unusual.append(f"{relative}: {current}")
            continue

        updated = html[:match.start(2)] + target + html[match.end(2):]
        path.write_text(updated, encoding="utf-8")
        changed += 1

    print(f"Public indexable HTML pages updated: {changed}")
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
