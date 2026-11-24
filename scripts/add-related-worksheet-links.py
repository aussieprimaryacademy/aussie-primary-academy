"""Add safe, same-level related worksheet links to worksheet detail pages.

Existing curated related sections are preserved. Generated modules are refreshed,
and eligible manual worksheet pages receive a module when they do not already have one.
"""
from __future__ import annotations

import importlib.util
import os
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF_ROOT = ROOT / "worksheets"
PAGES_ROOT = ROOT / "pages"
START = "<!-- APA-RELATED-WORKSHEETS:START -->"
END = "<!-- APA-RELATED-WORKSHEETS:END -->"
STOP_WORDS = {
    "free", "printable", "worksheet", "worksheets", "practice", "activity",
    "activities", "the", "and", "for", "with", "year", "grade", "foundation",
    "kindergarten", "english", "maths", "math", "science", "reading", "phonics",
}


def load_parser():
    path = ROOT / "scripts" / "generate-worksheet-pages.py"
    spec = importlib.util.spec_from_file_location("apa_worksheet_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load worksheet page metadata parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse


parse_pdf = load_parser()


SITE_BASE = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"


def canonical_target(page_rel: str) -> str:
    """Return the on-site page this page canonicalises to (or itself)."""
    page = ROOT / page_rel
    try:
        content = page.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return page_rel
    match = re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"', content, re.I)
    if not match or not match.group(1).startswith(SITE_BASE):
        return page_rel
    target = match.group(1)[len(SITE_BASE):]
    if target and (ROOT / target).is_file() and target != page_rel:
        return target
    return page_rel


def clean_page_title(page_rel: str, fallback: str) -> str:
    """Use the page's own H1 (never a filename-derived title) when it is readable."""
    try:
        content = (ROOT / page_rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return fallback
    match = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.I | re.S)
    if not match:
        return fallback
    title = re.sub(r"<[^>]+>", "", match.group(1))
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        return fallback
    return tidy_title(title)


SMALL_WORDS = {"a", "an", "and", "at", "for", "in", "of", "on", "or", "the", "to", "with"}


def tidy_title(title: str) -> str:
    """Remove filename-style noise (curriculum codes, 'Colour', 'Worksheet', 'PDF')."""
    title = re.sub(r"\bac9[a-z]{2,5}\d{2}\b", "", title, flags=re.I)
    title = re.sub(r"^(free printable\s+)?foundation\s+(english|maths|science|hass|health|the arts|technologies)\s+", "", title, flags=re.I)
    title = re.sub(r"^(free printable|free)\s+", "", title, flags=re.I)
    title = re.sub(r"\b(colour|color|worksheet|pdf)\b", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" -–|:")
    words = title.split(" ")
    out = []
    for i, word in enumerate(words):
        lower = word.lower()
        out.append(lower if (i and lower in SMALL_WORDS and word == word.title()) else word)
    return " ".join(out) or title


def tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def apply_end_of_year_classification(meta: dict[str, str], pdf: Path) -> dict[str, str]:
    """Apply editorial metadata for the curated End-of-Year resource collection."""
    name = pdf.stem.lower()
    if "years-1-2-school-swimming-preparation-reflection-pack" in name:
        meta.update(level="Years 1–2", subject="HPE")
    elif "years-3-6-school-swimming-preparation-reflection-pack" in name:
        meta.update(level="Years 3–6", subject="HPE")
    elif "years-1-2-my-school-year-memory-book" in name:
        meta.update(level="Years 1–2", subject="Wellbeing")
    elif "years-3-6-my-school-year-memory-book" in name:
        meta.update(level="Years 3–6", subject="Wellbeing")
    elif "year-6-secondary-school-transition-workbook" in name:
        meta.update(level="Year 6", subject="Transition")
    return meta


def select_related_candidates(current: dict[str, str], candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    current_tokens = tokens(current["title"])
    ranked = []
    for candidate in candidates:
        if candidate["page"] == current["page"]:
            continue
        if candidate["region"] != current["region"] or candidate["level"] != current["level"]:
            continue
        same_subject = candidate["subject"] == current["subject"]
        overlap = len(current_tokens & tokens(candidate["title"]))
        ranked.append((same_subject, overlap, candidate["title"].lower(), candidate))

    same_subject = [item for item in ranked if item[0]]
    # HPE, Wellbeing and Transition are curated cross-curricular resource groups.
    # Never fill a sparse group with unrelated English/Maths/Science links.
    strict_subject = current["subject"] in {"HPE", "Wellbeing", "Transition"}
    chosen_pool = same_subject if strict_subject or len(same_subject) >= 2 else ranked
    return [item[3] for item in sorted(
        chosen_pool, key=lambda item: (not item[0], -item[1], item[2])
    )[:4]]


def build_related_section(current: dict[str, str], candidates: list[dict[str, str]]) -> str:
    chosen = select_related_candidates(current, candidates)
    if not chosen:
        return ""

    label = f'{current["level"]} {current["subject"]}'
    cards = []
    for item in chosen:
        target_page = canonical_target(item["page"])
        shown_title = clean_page_title(target_page, item["title"])
        target = ROOT / target_page
        source = ROOT / current["page"]
        href = Path(os.path.relpath(target, source.parent)).as_posix()
        cards.append(
            '<article class="content-card">'
            f'<h3><a href="{escape(href, quote=True)}">{escape(shown_title)}</a></h3>'
            f'<p>{escape(item["level"])} · {escape(item["subject"])} · Free printable PDF</p>'
            '</article>'
        )
    return (
        f'{START}\n'
        '<section class="section related-worksheets" aria-labelledby="related-worksheets-heading">'
        '<div class="wrap"><div class="section-head"><div>'
        f'<h2 id="related-worksheets-heading">More {escape(label)} Worksheets</h2>'
        '<p>Explore related printable activities for further practice.</p>'
        '</div></div>'
        f'<div class="content-grid">{"".join(cards)}</div></div></section>\n'
        f'{END}'
    )


def main() -> int:
    if not PDF_ROOT.exists() or not PAGES_ROOT.exists():
        print("Worksheet or page directory not found; nothing to update.")
        return 0

    candidates = []
    seen_pages = set()
    for pdf in sorted(PDF_ROOT.rglob("*.pdf")):
        name = pdf.name.lower()
        if re.search(r"answer[-_ ]?(?:key|guide)|answerkey", name, re.I):
            continue
        meta = apply_end_of_year_classification(parse_pdf(pdf.relative_to(ROOT)), pdf)
        if "ac9sfis" in str(meta.get("page", "")).lower() or "ac9sfis" in str(meta.get("standard", "")).lower():
            continue
        page = ROOT / meta["page"]
        if not page.is_file() or meta["page"] in seen_pages:
            continue
        page_content = page.read_text(encoding="utf-8", errors="ignore")
        robots = re.search(r'<meta[^>]*name="robots"[^>]*>', page_content, re.I)
        if robots and "noindex" in robots.group(0).lower():
            continue
        seen_pages.add(meta["page"])
        candidates.append(meta)

    changed = 0
    skipped = 0
    for meta in candidates:
        page = ROOT / meta["page"]
        content = page.read_text(encoding="utf-8", errors="ignore")
        robots = re.search(r'<meta[^>]*name="robots"[^>]*>', content, re.I)
        if robots and "noindex" in robots.group(0).lower():
            skipped += 1
            continue
        generated = "<!-- AUTO-GENERATED-WORKSHEET-PAGE -->" in content
        has_unmanaged_related = (
            "related-worksheets" in content.lower()
            or re.search(
                r"<h[2-4][^>]*>\s*Related Worksheets\s*</h[2-4]>", content, re.I
            )
        )
        if not generated and has_unmanaged_related and START not in content:
            skipped += 1
            continue
        section = build_related_section(meta, candidates)
        if not section:
            continue
        block_pattern = re.compile(
            re.escape(START) + r"[\s\S]*?" + re.escape(END)
        )
        if block_pattern.search(content):
            updated = block_pattern.sub(lambda _: section, content, count=1)
        else:
            if "</main>" not in content:
                skipped += 1
                continue
            updated = content.replace("</main>", section + "\n</main>", 1)
        if updated != content:
            page.write_text(updated, encoding="utf-8")
            changed += 1

    print(
        f"Related worksheet modules: updated={changed}, "
        f"candidate_pages={len(candidates)}, skipped_manual_or_invalid={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
