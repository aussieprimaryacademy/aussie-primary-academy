#!/usr/bin/env python3
"""Generate a complete sitemap.xml from the repository file tree."""
import os
from pathlib import Path

BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
ROOT = Path(__file__).resolve().parent.parent

# Core pages (order matters for readability)
CORE = [
    "",  # homepage
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

def is_clean_html(path: Path) -> bool:
    name = path.name
    if not name.endswith(".html"):
        return False
    if " " in name:
        return False
    if name == "404.html":
        return False
    if name.endswith(".pdf"):
        return False
    return True

def collect_urls():
    urls = []
    seen = set()

    def add(rel: str):
        if rel not in seen:
            seen.add(rel)
            urls.append(rel)

    for p in CORE:
        add(p)

    # Blog
    blog_dir = ROOT / "blog"
    if blog_dir.is_dir():
        for f in sorted(blog_dir.glob("*.html")):
            if is_clean_html(f):
                add(f"blog/{f.name}")

    # pages/
    pages_dir = ROOT / "pages"
    if pages_dir.is_dir():
        for f in sorted(pages_dir.glob("*.html")):
            if is_clean_html(f):
                add(f"pages/{f.name}")

    return urls

def write_sitemap(urls):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for rel in urls:
        loc = BASE if rel == "" else BASE + rel
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append("    <changefreq>monthly</changefreq>")
        lines.append("    <priority>0.7</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    content = "\n".join(lines) + "\n"
    out = ROOT / "sitemap.xml"
    out.write_text(content, encoding="utf-8")
    return len(urls), len(content)

if __name__ == "__main__":
    urls = collect_urls()
    count, size = write_sitemap(urls)
    print(f"Generated sitemap.xml with {count} URLs ({size} bytes)")
    # Basic validation
    text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    assert text.startswith("<?xml")
    assert "<urlset" in text
    assert text.rstrip().endswith("</urlset>")
    assert "PLACEHOLDER" not in text
    assert text.count("<loc>") == count
    print("Validation passed")
