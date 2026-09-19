#!/usr/bin/env python3
"""Create individual worksheet HTML pages for PDFs that do not already have one.

Safety rules:
- never overwrites an existing HTML page
- skips answer-key PDFs
- requires a matching preview PNG
- can be limited to a small test batch with MAX_NEW_PAGES
- can be scoped with PAGE_GENERATOR_SCOPE (comma-separated directories)
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from html import escape

BASE_URL = "https://aussieprimaryacademy.github.io/aussie-primary-academy/"
PDF_ROOT = Path("worksheets")
PAGES_ROOT = Path("pages")


def humanize(text: str) -> str:
    text = re.sub(r"[-_]+", " ", text)
    text = re.sub(r"\bfree printable\b", "", text, flags=re.I)
    text = re.sub(r"\bworksheet\b", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    return text.title()


def parse(pdf: Path) -> dict[str, str]:
    name = pdf.stem
    lower = name.lower()
    parts = pdf.parts
    region = "USA" if "usa" in parts or lower.startswith(("us-", "usa-")) else "Australia"

    grade_match = re.search(r"(?:grade|year)[-_ ]?(\d+)", lower)
    if grade_match:
        number = grade_match.group(1)
        level = f"Grade {number}" if region == "USA" else f"Year {number}"
    elif "foundation" in lower or "kindergarten" in lower:
        level = "Kindergarten" if region == "USA" else "Foundation"
    else:
        level = "Primary"

    subject = "Math" if any(x in lower for x in ("/math/", "-math-", "_math_")) else "English"
    if "/science/" in lower or "-science-" in lower:
        subject = "Science"
    elif any(x in lower for x in ("/ela/", "-ela-", "-english-", "/english/", "reading", "writing", "phonics", "spelling", "grammar")):
        subject = "English"

    standard = ""
    m = re.search(r"ccss-([a-z0-9-]+?)-free-printable$", lower)
    if m:
        raw = m.group(1)
        tokens = raw.split("-")
        if len(tokens) >= 4:
            standard = "CCSS " + ".".join(tokens[:4])
            if len(tokens) > 4:
                # Common multi-number CCSS filenames such as 6-rp-a-1-3.
                extras = [x for x in tokens[4:] if x.isdigit()]
                if extras:
                    standard += " / " + ".".join(tokens[:3] + [extras[0]])
    if not standard:
        m = re.search(r"(ac9[a-z0-9]+)", lower)
        if m:
            standard = m.group(1).upper()

    clean = re.sub(r"^(us|usa)-", "", name, flags=re.I)
    clean = re.sub(r"^(grade|year)-?\d+-", "", clean, flags=re.I)
    clean = re.sub(r"^(math|maths|ela|english|science)-", "", clean, flags=re.I)
    clean = re.sub(r"-ccss-[a-z0-9-]+-free-printable$", "", clean, flags=re.I)
    clean = re.sub(r"-ac9[a-z0-9]+-free-printable$", "", clean, flags=re.I)
    clean = re.sub(r"-free-printable$", "", clean, flags=re.I)
    title = humanize(clean)

    slug = re.sub(r'[^a-z0-9]+', '-', clean.lower()).strip('-')
    # Holiday/workbook packs can have the same title across year levels.
    # Keep the level in the URL so Year 1 and Year 2 never collide.
    if "school-holiday-learning-pack" in slug or "learning-pack" in slug:
        level_slug = re.sub(r'[^a-z0-9]+', '-', level.lower()).strip('-')
        slug = f"{level_slug}-{slug}"
    page_name = f"free-printable-{slug}-worksheet.html"
    # Avoid accidental duplicate '-worksheet-worksheet'.
    page_name = page_name.replace("-worksheet-worksheet.html", "-worksheet.html")

    preview = pdf.parent / "previews" / f"{pdf.stem}.png"
    return {
        "title": title,
        "level": level,
        "subject": subject,
        "region": region,
        "standard": standard,
        "page": str(PAGES_ROOT / page_name),
        "pdf": str(pdf),
        "preview": str(preview),
    }


def page_html(meta: dict[str, str]) -> str:
    pdf_href = "../" + meta["pdf"]
    preview_href = "../" + meta["preview"]
    canonical = BASE_URL + meta["page"]
    hub = "../worksheets.html"
    if meta["region"] == "USA" and meta["level"].startswith("Grade "):
        hub = f"../usa-grade-{meta['level'].split()[-1]}.html"
    elif meta["level"].startswith("Year "):
        hub = f"../year-{meta['level'].split()[-1]}.html"

    standard_text = escape(meta["standard"] or "Curriculum alignment listed in the worksheet filename")
    title = escape(meta["title"])
    level = escape(meta["level"])
    subject = escape(meta["subject"])
    region = escape(meta["region"])

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Free Printable {title} Worksheet PDF | {level}</title>
<meta name="description" content="Free printable {level} {subject.lower()} worksheet for {title.lower()}. Download the PDF for classroom, homework, tutoring or homeschool practice.">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{escape(canonical)}">
<link rel="icon" type="image/png" href="../favicon.png">
<link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=Nunito+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../styles.css">
<style>
.resource-hero{{background:linear-gradient(135deg,#f8f2ff 0%,#fff8ed 54%,#eef8ff 100%);border-bottom:1px solid #eadff0;padding:42px 0 34px}}
.resource-kicker{{color:#6d477f;font-weight:700;letter-spacing:.04em;text-transform:uppercase;font-size:.82rem}}
.trust-row{{display:flex;flex-wrap:wrap;gap:9px;margin-top:18px}}
.trust-badge{{background:#fff;border:1px solid #e5d8ec;border-radius:999px;padding:8px 13px;font-weight:700;font-size:.86rem}}
.resource-layout{{display:grid;grid-template-columns:minmax(0,1.12fr) minmax(290px,.88fr);gap:30px}}
.premium-card{{background:#fff;border:1px solid #eadff0;border-radius:20px;box-shadow:0 12px 34px rgba(70,48,84,.08);padding:24px}}
.preview-shell{{background:linear-gradient(145deg,#f5eff9,#fffaf2);border:1px solid #e6d9ec;border-radius:18px;padding:16px}}
.download-primary{{display:flex!important;justify-content:center;width:100%;padding:14px 18px!important;margin:18px 0 10px}}
.facts-list{{list-style:none;padding:0;margin:16px 0 0}}.facts-list li{{padding:7px 0;border-bottom:1px solid #f0e6f5}}
.content-grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.content-card{{background:#fff;border:1px solid #eadff0;border-radius:16px;padding:20px}}
@media(max-width:900px){{.resource-layout,.content-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class="site"><div class="wrap nav"><a href="../index.html" class="brand"><span class="mark">AP</span> Aussie Primary Academy</a><nav class="links"><a href="../worksheets.html">Worksheets</a><a class="btn btn-primary nav-cta" href="../worksheets.html">Browse Free Worksheets</a></nav></div></header>
<main id="main">
<nav class="breadcrumb wrap"><ol><li><a href="../index.html">Home</a></li><li><a href="{hub}">{level}</a></li><li aria-current="page">{title}</li></ol></nav>
<section class="resource-hero"><div class="wrap"><p class="resource-kicker">{region} · {level} · {subject}</p><h1>{title}</h1><p class="lead">A ready-to-use printable worksheet for focused practice in {title.lower()}.</p><div class="trust-row"><span class="trust-badge">Free printable PDF</span><span class="trust-badge">{level}</span><span class="trust-badge">{subject}</span></div></div></section>
<section class="section"><div class="wrap resource-layout"><div><div class="premium-card"><div class="preview-shell"><img src="{escape(preview_href)}" alt="{title} worksheet preview" style="width:100%;height:auto;border-radius:12px;" loading="lazy"></div></div></div>
<aside><div class="premium-card"><p class="resource-kicker">Download</p><h2 style="margin:.2rem 0 .6rem;font-size:1.25rem">Get this worksheet</h2><p>Printable PDF for classroom, homework, tutoring or homeschool practice.</p><a class="btn btn-primary download-primary" href="{escape(pdf_href)}" download>⬇ Download Free PDF</a><ul class="facts-list"><li><strong>Level:</strong> {level}</li><li><strong>Subject:</strong> {subject}</li><li><strong>Curriculum:</strong> {standard_text}</li></ul></div></aside></div></section>
<section class="section" style="padding-top:0"><div class="wrap"><div class="content-grid"><article class="content-card"><h2>About this worksheet</h2><p>This printable resource focuses on one clear learning skill so students can practise independently or with adult support.</p></article><article class="content-card"><h2>Learning focus</h2><p>Use the worksheet for targeted practice, revision, homework, tutoring or homeschool learning. Review student responses and revisit the skill where needed.</p></article></div></div></section>
<section class="section"><div class="wrap"><p><a class="btn btn-secondary" href="{hub}">Browse more {level} worksheets</a></p></div></section>
</main>
<footer><div class="wrap"><div class="foot-bottom"><span>© 2026 Aussie Primary Academy. Made with care in Australia.</span></div></div></footer>
<script defer src="../download-tracking.js"></script>
</body>
</html>
'''


def main() -> int:
    scopes = [x.strip().rstrip("/") for x in os.getenv("PAGE_GENERATOR_SCOPE", "worksheets").split(",") if x.strip()]
    limit = int(os.getenv("MAX_NEW_PAGES", "5"))
    created = 0
    skipped = 0

    candidates: list[Path] = []
    for scope in scopes:
        root = Path(scope)
        if root.exists():
            candidates.extend(sorted(root.rglob("*.pdf")))

    seen: set[Path] = set()
    for pdf in candidates:
        if pdf in seen:
            continue
        seen.add(pdf)
        if "answer-key" in pdf.name.lower() or "answerkey" in pdf.name.lower():
            continue
        meta = parse(pdf)
        page = Path(meta["page"])
        if page.exists():
            skipped += 1
            continue
        if not Path(meta["preview"]).exists():
            print(f"SKIP (no preview): {pdf}")
            continue
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(page_html(meta), encoding="utf-8")
        created += 1
        print(f"CREATED: {page} <- {pdf}")
        if created >= limit:
            break

    print(f"SUMMARY: created={created} skipped_existing={skipped} limit={limit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
