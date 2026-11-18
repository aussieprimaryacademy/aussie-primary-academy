#!/usr/bin/env python3
"""Set the correct English locale on every eligible public HTML page.

Australian resources use en-AU; USA resources use en-US. USA detection is
content-aware: a USA filename/path, a worksheet PDF under worksheets/usa/,
or a Common Core (CCSS) standard marks the page as a USA resource. The script
updates the html lang attribute and an existing Open Graph locale value.
Page copy, canonicals, links, and PDFs are left untouched. Explicit noindex
and non-public pages are skipped.
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
LANG_ATTRIBUTE = re.compile(r'(<html\\b[^>]*\\blang\\s*=\\s*")([^"]+)(")', re.I)
META_TAG = re.compile(r"<meta\\b[^>]*>", re.I)
ATTRIBUTE = re.compile(r"""(\\b{attribute}\\s*=\\s*)(["'])(.*?)\\2""", re.I)
CCSS_STANDARD = re.compile(r"\\bCCSS\\b", re.I)


def is_usa_resource(path: Path, html: str) -> bool:
    """Return True when the page contains any explicit USA resource signal."""
    parts = {part.lower() for part in path.parts}
    filename = path.name.lower()
    return (
        "usa" in parts
        or "usa" in filename
        or "worksheets/usa/" in html.lower()
        or bool(CCSS_STANDARD.search(html))
    )


def expected_language(path: Path, html: str = "") -> str:
    return "en-US" if is_usa_resource(path, html) else "en-AU"


def update_open_graph_locale(html: str, locale: str) -> str:
    """Update existing og:locale metadata without adding metadata to other pages."""
    def update_tag(match: re.Match) -> str:
        tag = match.group(0)
        property_match = ATTRIBUTE.pattern.format(attribute="property")
        property_value = re.search(property_match, tag, re.I)
        if not property_value or property_value.group(3).lower() != "og:locale":
            return tag
        content_pattern = ATTRIBUTE.pattern.format(attribute="content")
        if re.search(content_pattern, tag, re.I):
            return re.sub(
                content_pattern,
                lambda value: value.group(1) + value.group(2) + locale + value.group(2),
                tag,
                count=1,
                flags=re.I,
            )
        return tag[:-1] + f' content="{locale}">'

    return META_TAG.sub(update_tag, html)


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
        target = expected_language(path, html)
        locale = "en_US" if target == "en-US" else "en_AU"
        updated = html[:match.start(2)] + target + html[match.end(2):]
        updated = update_open_graph_locale(updated, locale)

        if updated == html:
            unchanged += 1
            continue
        if current.lower() not in {"en", "en-au", "en-us"}:
            unusual.append(f"{relative}: {current}")
            continue

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
