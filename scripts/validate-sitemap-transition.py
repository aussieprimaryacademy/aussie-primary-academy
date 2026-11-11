#!/usr/bin/env python3
"""Reject unexplained sitemap URL removals; allow only explicit hard exclusions."""
from pathlib import Path
from urllib.parse import unquote
import importlib.util
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "sitemap_generator", ROOT / "scripts" / "generate-sitemap.py"
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def sitemap_urls(path):
    root = ET.parse(path).getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return {
        node.text.strip()
        for node in root.findall(".//sm:loc", ns)
        if node.text and node.text.strip()
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate-sitemap-transition.py PREVIOUS_URL_LIST")
    previous_file = Path(sys.argv[1])
    previous = set(previous_file.read_text(encoding="utf-8").splitlines())
    current = sitemap_urls(ROOT / "sitemap.xml")
    removed = sorted(previous - current)
    unexpected = []

    for url in removed:
        if not url.startswith(GENERATOR.BASE):
            unexpected.append(url + " (outside canonical site)")
            continue
        relative = unquote(url[len(GENERATOR.BASE):]) or "index.html"
        page = ROOT / relative
        if not page.is_file():
            unexpected.append(url + " (source file missing; manual review required)")
            continue
        if not (GENERATOR.is_excluded_path(page) or GENERATOR.parse_page(page)[0]):
            unexpected.append(url + " (not covered by an explicit exclusion rule)")

    print(f"Previous URLs: {len(previous)}; generated URLs: {len(current)}")
    print(f"Removed URLs: {len(removed)}; expected hard-exclusion removals: {len(removed) - len(unexpected)}")
    if removed:
        print("Reviewed removals:")
        for url in removed:
            print(f"  {url}")
    if unexpected:
        print("Unexpected removals:")
        for url in unexpected:
            print(f"  {url}")
        raise SystemExit("ERROR: unexplained sitemap removals require manual review.")
    print("Sitemap URL comparison passed: no unexplained removals.")


if __name__ == "__main__":
    main()
