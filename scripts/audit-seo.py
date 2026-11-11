#!/usr/bin/env python3
"""Read-only SEO audit: separate hard issues, editorial reviews, and information."""
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
import sys
import importlib.util

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("sitemap_generator", ROOT / "scripts" / "generate-sitemap.py")
SITEMAP_GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SITEMAP_GENERATOR)
is_excluded_path = SITEMAP_GENERATOR.is_excluded_path


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
        attrs = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "html":
            self.lang = attrs.get("lang")
        elif tag == "title":
            self._title = ""
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            name = attrs.get("name", "").strip().lower()
            if name == "description":
                self.descriptions.append(attrs.get("content", "").strip())
            elif name == "viewport":
                self.viewport_count += 1
            elif name == "robots":
                directives = {item.strip().lower() for item in attrs.get("content", "").split(",")}
                if "noindex" in directives:
                    self.noindex = True
        elif tag == "link" and "canonical" in {
            item.strip().lower() for item in attrs.get("rel", "").split()
        }:
            self.canonicals.append(attrs.get("href", "").strip())

    def handle_data(self, data):
        if self._title is not None:
            self._title += data

    def handle_endtag(self, tag):
        if tag.lower() == "title" and self._title is not None:
            self.titles.append(self._title.strip())
            self._title = None


def main():
    pages = {}
    for path in sorted(ROOT.rglob("*.html")):
        if is_excluded_path(path):
            continue
        html = path.read_text(encoding="utf-8", errors="ignore")
        audit = Audit()
        audit.feed(html)
        if audit.noindex:
            continue
        pages[str(path.relative_to(ROOT))] = (audit, html)

    title_counts = Counter(
        a.titles[0] for a, _ in pages.values()
        if len(a.titles) == 1 and a.titles[0]
    )
    description_counts = Counter(
        a.descriptions[0] for a, _ in pages.values()
        if len(a.descriptions) == 1 and a.descriptions[0]
    )
    issues = defaultdict(list)
    review = defaultdict(list)
    info = defaultdict(list)

    for relative_path, (audit, html) in pages.items():
        canonical = audit.canonicals
        if not (
            len(canonical) == 1
            and canonical[0].startswith("https://")
            and "?" not in canonical[0]
            and not canonical[0].endswith("/index.html")
        ):
            issues["canonical missing, duplicate or invalid"].append(relative_path)

        if len(audit.titles) != 1 or not audit.titles[0]:
            issues["title missing or multiple"].append(relative_path)
        else:
            if len(audit.titles[0]) >= 60:
                review["title is 60+ characters"].append(relative_path)
            if title_counts[audit.titles[0]] > 1:
                issues["duplicate title"].append(relative_path)

        if len(audit.descriptions) != 1 or not audit.descriptions[0]:
            issues["description missing or multiple"].append(relative_path)
        else:
            if len(audit.descriptions[0]) >= 160:
                review["description is 160+ characters"].append(relative_path)
            if description_counts[audit.descriptions[0]] > 1:
                issues["duplicate description"].append(relative_path)

        if audit.h1_count != 1:
            issues["not exactly one H1"].append(relative_path)

        relative = Path(relative_path)
        parts = {part.lower() for part in relative.parts}
        filename = relative.name.lower()
        expected_lang = "en-US" if "usa" in parts or filename.startswith(("us-", "usa-")) else "en-AU"
        if audit.lang != expected_lang:
            issues[f"locale mismatch (expected {expected_lang})"].append(relative_path)

        if audit.viewport_count != 1:
            info["viewport count is not one"].append(relative_path)
        if "G-41Q0QR6ZHD" not in html:
            info["GA4 ID not found"].append(relative_path)

    affected = {path for paths in issues.values() for path in paths}
    review_affected = {path for paths in review.values() for path in paths}
    print(f"Indexable HTML pages audited: {len(pages)}")
    print(f"Pages with hard SEO issues: {len(affected)}")
    for category, paths in sorted(issues.items(), key=lambda item: -len(item[1])):
        print(f"{category}: {len(paths)}")
    print(f"Pages with editorial length review signals: {len(review_affected)}")
    for category, paths in sorted(review.items(), key=lambda item: -len(item[1])):
        print(f"{category}: {len(paths)}")
    print("Informational checks (not SEO failures):", {
        key: len(value) for key, value in info.items()
    } or "none")

    for category, counts, field_index in (
        ("duplicate title groups", title_counts, 0),
        ("duplicate description groups", description_counts, 1),
    ):
        duplicates = [(value, count) for value, count in counts.items() if count > 1]
        if duplicates:
            print(f"\n{category}:")
            for value, count in sorted(duplicates, key=lambda item: (-item[1], item[0])):
                matching = [
                    path for path, (audit, _) in pages.items()
                    if (audit.titles[0] if field_index == 0 and len(audit.titles) == 1
                        else audit.descriptions[0] if field_index == 1 and len(audit.descriptions) == 1
                        else None) == value
                ]
                print(f"  {count} pages — {value}")
                for path in matching:
                    print(f"    {path}")

    if "-v" in sys.argv:
        for category, paths in issues.items():
            print(f"\n[{category}]")
            print("\n".join(paths))


if __name__ == "__main__":
    main()
