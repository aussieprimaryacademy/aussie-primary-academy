#!/usr/bin/env python3
"""Set correct English locales using the shared USA detector in audit-seo.py."""
from pathlib import Path
import re
import importlib.util
import sys

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("apa_seo_audit", ROOT / "scripts" / "audit-seo.py")
SEO_AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEO_AUDIT)
SITEMAP_SPEC = importlib.util.spec_from_file_location(
    "sitemap_generator", ROOT / "scripts" / "generate-sitemap.py"
)
SITEMAP_GENERATOR = importlib.util.module_from_spec(SITEMAP_SPEC)
SITEMAP_SPEC.loader.exec_module(SITEMAP_GENERATOR)

LANG_ATTRIBUTE = re.compile(r'(<html\b[^>]*\blang\s*=\s*")([^"]+)(")', re.I)
META_TAG = re.compile(r"<meta\b[^>]*>", re.I)
ATTRIBUTE = re.compile(r"""(\b{attribute}\s*=\s*)(["'])(.*?)\2""", re.I)


def expected_language(path: Path, html: str = "") -> str:
    relative_path = path.relative_to(ROOT).as_posix()
    return "en-US" if SEO_AUDIT.is_usa_resource(relative_path, html) else "en-AU"


def update_open_graph_locale(html: str, locale: str) -> str:
    """Update existing og:locale metadata without adding metadata to other pages."""
    def update_tag(match: re.Match) -> str:
        tag = match.group(0)
        property_pattern = ATTRIBUTE.pattern.format(attribute="property")
        property_value = re.search(property_pattern, tag, re.I)
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


def main(dry_run: bool = False) -> int:
    changed = 0
    unchanged = 0
    change_rows = []
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
        signals = SEO_AUDIT.usa_detection_signals(relative, html)
        locale = "en_US" if target == "en-US" else "en_AU"
        updated = html[:match.start(2)] + target + html[match.end(2):]
        updated = update_open_graph_locale(updated, locale)

        if updated == html:
            unchanged += 1
            continue
        if current.lower() not in {"en", "en-au", "en-us"}:
            unusual.append(f"{relative}: {current}")
            continue

        if not dry_run:
            path.write_text(updated, encoding="utf-8")
        changed += 1
        change_rows.append((relative, current, target, "; ".join(signals) if signals else "Australian default"))

    print("FULL LANGUAGE CHANGE MANIFEST (path | old lang | new lang | triggering signal):")
    for row in change_rows:
        print(" | ".join(row))
    action = "would update (dry-run)" if dry_run else "updated"
    print(f"Public indexable HTML pages {action}: {changed}")
    print(f"Already correct: {unchanged}")
    print(f"Missing lang attribute: {len(missing)}")
    print(f"Unusual locales left for review: {len(unusual)}")
    if missing or unusual:
        for item in (missing + unusual)[:50]:
            print(f"REVIEW: {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(dry_run="--dry-run" in sys.argv))
