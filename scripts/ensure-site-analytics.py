#!/usr/bin/env python3
"""Keep GA4 and PDF click tracking consistent across all public HTML pages."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEASUREMENT_ID = "G-41Q0QR6ZHD"
VERIFICATION_PAGE = "google99305cdd54a8d1be.html"

FULL_GA4_SNIPPET = f"""<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{MEASUREMENT_ID}');
</script>
"""

INLINE_GA4_INIT = f"""<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{MEASUREMENT_ID}');
</script>
"""


def add_download_tracking(text: str, page: Path) -> tuple[str, bool]:
    """Add the relative tracker script only to pages that link to PDFs."""
    if not re.search(r"\.pdf(?:[?#\"'\s]|$)", text, re.IGNORECASE):
        return text, False
    if re.search(
        r"<script\b[^>]*src=[\"'][^\"']*download-tracking\.js",
        text,
        re.IGNORECASE,
    ):
        return text, False

    body_end = re.search(r"</body\s*>", text, re.IGNORECASE)
    if not body_end:
        print(f"SKIP tracker (no closing body): {page.relative_to(ROOT)}")
        return text, False

    relative_tracker = Path(
        __import__("os").path.relpath(ROOT / "download-tracking.js", page.parent)
    ).as_posix()
    tag = f'<script defer src="{relative_tracker}"></script>\n'
    return text[: body_end.start()] + tag + text[body_end.start() :], True


def add_ga4(text: str, page: Path) -> tuple[str, bool]:
    """Add the APA GA4 measurement ID without duplicating an existing loader."""
    if MEASUREMENT_ID in text:
        return text, False

    head_end = re.search(r"</head\s*>", text, re.IGNORECASE)
    if not head_end:
        print(f"SKIP GA4 (no closing head): {page.relative_to(ROOT)}")
        return text, False

    init = re.search(
        r"""(<script\b[^>]*>)([\s\S]*?gtag\s*\(\s*['"]js['"][\s\S]*?)(</script\s*>)""",
        text,
        re.IGNORECASE,
    )
    if init:
        block = init.group(0)
        js_call = re.search(
            r"""gtag\s*\(\s*['"]js['"][\s\S]*?\);""",
            block,
            re.IGNORECASE,
        )
        if js_call:
            replacement = (
                block[: js_call.end()]
                + f"\n  gtag('config', '{MEASUREMENT_ID}');"
                + block[js_call.end() :]
            )
            return text[: init.start()] + replacement + text[init.end() :], True

    # Reuse an existing gtag.js loader if present; otherwise install the full tag.
    if re.search(r"googletagmanager\.com/gtag/js", text, re.IGNORECASE):
        snippet = INLINE_GA4_INIT
    else:
        snippet = FULL_GA4_SNIPPET
    return text[: head_end.start()] + snippet + "\n" + text[head_end.start() :], True


def main() -> int:
    tracker_added = 0
    ga4_added = 0
    skipped = 0
    structure_errors = []

    for page in sorted(ROOT.rglob("*.html")):
        relative = page.relative_to(ROOT)
        if ".git" in relative.parts or ".github" in relative.parts:
            continue
        if page.name == VERIFICATION_PAGE:
            continue

        original = page.read_text(encoding="utf-8", errors="ignore")
        updated, tracker_changed = add_download_tracking(original, page)
        updated, ga4_changed = add_ga4(updated, page)

        if tracker_changed:
            tracker_added += 1
        if ga4_changed:
            ga4_added += 1
        if updated != original:
            page.write_text(updated, encoding="utf-8")
        if not re.search(r"</head\s*>", updated, re.IGNORECASE):
            skipped += 1

    print(f"PDF tracker added to {tracker_added} HTML pages.")
    print(f"GA4 measurement {MEASUREMENT_ID} added to {ga4_added} HTML pages.")
    print(f"HTML files still missing a closing head tag: {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
