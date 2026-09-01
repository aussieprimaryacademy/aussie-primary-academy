#!/usr/bin/env python3
"""Generate sitemap.xml from all public HTML pages in the repository."""
from pathlib import Path
from xml.sax.saxutils import escape

BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
ROOT = Path(__file__).resolve().parent.parent

# These are the important root-level pages that should always be included.
CORE = [
    "",
    "foundation.html",
    "year-1.html",
    "year-2.html",
    "year-3.html",
    "year-4.html",
    "year-5.html",
    "year-6.html",
    "maths.html",
    "english.html",
    "science.html",
    "worksheets.html",
    "about.html",
    "free-student-planner.html",
    "privacy-policy.html",
    "terms-of-use.html",
]

EXCLUDED_NAMES = {"404.html"}
EXCLUDED_DIRS = {".git", ".github", "scripts", "assets", "css", "js"}


def is_clean_html(path: Path) -> bool:
    """Return True only for clean, public HTML pages."""
    return (
        path.suffix.lower() == ".html"
        and path.name not in EXCLUDED_NAMES
        and " " not in path.name
    )


def collect_urls() -> list[str]:
    urls: set[str] = set(CORE)

    # Include every public HTML page under blog/ and pages/.
    for folder in ("blog", "pages"):
        directory = ROOT / folder
        if directory.is_dir():
            for path in directory.rglob("*.html"):
                if is_clean_html(path):
                    urls.add(path.relative_to(ROOT).as_posix())

    # Also include any clean root-level HTML pages not already listed in CORE.
    for path in ROOT.glob("*.html"):
        if is_clean_html(path):
            urls.add(path.name)

    return sorted(urls, key=lambda item: (item != "", item))


def write_sitemap(urls: list[str]) -> int:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for rel in urls:
        loc = BASE if rel == "" else BASE + rel
        lines.extend(
            [
                "  <url>",
                f"    <loc>{escape(loc)}</loc>",
                "    <changefreq>monthly</changefreq>",
                "    <priority>0.7</priority>",
                "  </url>",
            ]
        )

    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(urls)


if __name__ == "__main__":
    urls = collect_urls()
    count = write_sitemap(urls)
    print(f"Generated sitemap.xml with {count} URLs")

    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    assert text.startswith("<?xml")
    assert text.rstrip().endswith("</urlset>")
    assert text.count("<loc>") == count
    print("Validation passed")
