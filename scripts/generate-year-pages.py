#!/usr/bin/env python3
"""Keep Australian year pages in sync with worksheet PDFs.

New worksheet cards are auto-managed. Foundation cards are placed inside the
relevant subject sections so the subject navigation remains meaningful.
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
W = ROOT / "worksheets"
START = "<!-- AUTO-YEAR-WORKSHEETS:START -->"
END = "<!-- AUTO-YEAR-WORKSHEETS:END -->"

SUBJECTS = {"maths":"Maths","english":"English","science":"Science","phonics":"Phonics","reading":"Reading","writing":"Writing"}

def title_for(p: Path, level: str, subject: str) -> str:
    words = re.split(r"[-_]+", p.stem)
    drop = {"worksheet","free","printable","australia","australian","colour","color","pdf","with","answers","answer","key","year",level.split()[-1].lower(),subject.lower()}
    out=[]
    for w in words:
        low=w.lower()
        if low in drop or re.fullmatch(r"year\d",low) or re.fullmatch(r"ac9[a-z0-9]+",low):
            continue
        out.append({"naplan":"NAPLAN","cvc":"CVC"}.get(low,low.capitalize()))
    return " ".join(out) or f"{level} {subject} Practice"

def subject_for(p: Path) -> str:
    parts=[x.lower() for x in p.parts]
    for key,label in SUBJECTS.items():
        if key in parts:
            return label
    lower=p.stem.lower()
    if re.search(r"ac9m[a-z0-9]+",lower):
        return "Maths"
    if re.search(r"ac9s[a-z0-9]+",lower):
        return "Science"
    if re.search(r"ac9e[a-z0-9]+",lower):
        return "English"
    if any(x in lower for x in ("phonics","reading","writing","spelling","grammar")):
        return "English"
    return "Worksheet"

def page_for_pdf(p: Path, level: str) -> str:
    name = p.stem
    clean = re.sub(r"^(us|usa)-", "", name, flags=re.I)
    clean = re.sub(r"^(grade|year)-?\d+-", "", clean, flags=re.I)
    clean = re.sub(r"^(math|maths|ela|english|science)-", "", clean, flags=re.I)
    clean = re.sub(r"-ccss-[a-z0-9-]+-free-printable$", "", clean, flags=re.I)
    clean = re.sub(r"-ac9[a-z0-9]+-free-printable$", "", clean, flags=re.I)
    clean = re.sub(r"-free-printable$", "", clean, flags=re.I)
    slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
    if "school-holiday-learning-pack" in slug or "learning-pack" in slug:
        level_slug = re.sub(r"[^a-z0-9]+", "-", level.lower()).strip("-")
        slug = f"{level_slug}-{slug}"
    page_name = f"free-printable-{slug}-worksheet.html"
    page_name = page_name.replace("-worksheet-worksheet.html", "-worksheet.html")
    return f"pages/{page_name}"

def card(p: Path, level: str, i: int) -> str:
    rel=p.relative_to(ROOT).as_posix()
    subject=subject_for(p)
    title=title_for(p,level,subject)
    code=(re.search(r"ac9[a-z0-9]+",p.stem,re.I) or [None])[0]
    badge=f"{code.upper()} · Australian Curriculum V9.0" if code else "Free printable PDF"
    return (
      f'        <li class="wcard auto-year-card"><div class="thumb c{i%4+1}">{escape(level)} · {escape(subject)}</div>'
      f'<div class="body"><p class="tag">{escape(subject)} · Free PDF</p><h3>{escape(title)}</h3>'
      f'<span class="curriculum-badge">{escape(badge)}</span>'
      f'<p class="card-desc">Printable {escape(level)} {escape(subject)} practice worksheet.</p>'
      f'<p class="card-actions"><a class="btn btn-secondary btn-sm" href="{escape(page_for_pdf(p,level),quote=True)}">View Worksheet</a> '
      f'<a class="btn btn-primary btn-sm" href="{escape(rel,quote=True)}" download>⬇ Download PDF</a></p></div></li>'
    )

def block(paths, level):
    if not paths:
        return ""
    cards="\n".join(card(p,level,i) for i,p in enumerate(paths))
    return f'''{START}
<section class="section auto-year-worksheets" aria-label="New {escape(level)} worksheet downloads">
  <div class="wrap">
    <div class="section-head"><div><h2>More {escape(level)} Worksheets</h2><p>New printable worksheets added automatically from the worksheet library.</p></div></div>
    <ul class="grid-cards browse-grid">
{cards}
    </ul>
  </div>
</section>
{END}'''

def foundation_block_by_subject(paths, level):
    groups={label:[] for label in SUBJECTS.values()}
    for p in paths:
        groups.setdefault(subject_for(p),[]).append(p)
    parts=[]
    for subject,items in groups.items():
        if not items:
            continue
        cards="\n".join(card(p,level,i) for i,p in enumerate(items))
        parts.append(f'''<section class="section auto-year-subject" id="{subject.lower()}" aria-labelledby="auto-{subject.lower()}-heading">
  <div class="wrap">
    <div class="section-head"><div><h2 id="auto-{subject.lower()}-heading">Foundation {subject} Worksheets</h2><p>New printable {subject} resources added from the worksheet library.</p></div></div>
    <ul class="grid-cards browse-grid">
{cards}
    </ul>
  </div>
</section>''')
    return "\n".join(parts)

def update_foundation(page: Path, folder: Path, level: str):
    text = page.read_text(encoding="utf-8")

    # Rebuild only bot-owned subject sections. Older versions could append
    # duplicate Reading/Science sections because these sections had no markers.
    text = re.sub(
        r'\s*<section class="section auto-year-subject"[\s\S]*?</section>\s*',
        "\n",
        text,
    )

    extra = []
    for subject in ("Reading", "Writing", "Phonics", "Science"):
        subject_folder = folder / subject.lower()
        pdfs = sorted(subject_folder.rglob("*.pdf"), key=lambda p: p.as_posix().lower()) if subject_folder.exists() else []
        # A PDF already listed in a hand-curated section should not be duplicated.
        pdfs = [p for p in pdfs if p.relative_to(ROOT).as_posix() not in text]
        if not pdfs:
            continue

        cards = "\n".join(card(p, level, i) for i, p in enumerate(pdfs))
        extra.append(f'''<section class="section auto-year-subject" id="{subject.lower()}" aria-labelledby="auto-{subject.lower()}-heading">
  <div class="wrap">
    <div class="section-head"><div><h2 id="auto-{subject.lower()}-heading">Foundation {subject} Worksheets</h2><p>Printable {subject} resources from the worksheet library.</p></div></div>
    <ul class="grid-cards browse-grid">
{cards}
    </ul>
  </div>
</section>''')

    if extra:
        anchor = re.search(
            r'<section class="section">\s*<div class="wrap">\s*<div class="section-head">\s*<div><h2>Browse more year levels</h2>',
            text,
        )
        insertion = "\n" + "\n".join(extra) + "\n"
        if anchor:
            text = text[:anchor.start()] + insertion + text[anchor.start():]
        else:
            text = text.replace("</main>", insertion + "</main>", 1)

    page.write_text(text, encoding="utf-8")
    print(f"{page.name}: rebuilt {len(extra)} Foundation subject sections without duplicates")


def update(page: Path, folder: Path, level: str):
    if level == "Foundation":
        update_foundation(page, folder, level)
        return

    text = page.read_text(encoding="utf-8")

    # Remove the previous bot-owned "More Year" block and its generated cards
    # before rebuilding. This makes repeat runs idempotent instead of stacking
    # stale cards at the bottom of the page.
    text = re.sub(
        re.escape(START) + r"[\s\S]*?" + re.escape(END),
        "",
        text,
    )
    text = re.sub(
        r'\s*<section class="section auto-year-worksheets"[\s\S]*?</section>\s*',
        "\n",
        text,
    )
    text = re.sub(
        r'<li class="wcard auto-year-card">[\s\S]*?</li>',
        "",
        text,
    )

    pdfs = sorted(folder.rglob("*.pdf"), key=lambda p: p.as_posix().lower()) if folder.exists() else []
    # The cards remaining in the HTML are manually curated and must be preserved.
    missing = [p for p in pdfs if p.relative_to(ROOT).as_posix() not in text]

    groups = {"maths": [], "english": [], "science": []}
    fallback = []
    for p in missing:
        subject = subject_for(p).lower()
        target = "maths" if subject in {"maths", "math"} else "science" if subject == "science" else "english"
        groups.setdefault(target, []).append(p)

    for target, items in groups.items():
        if not items:
            continue
        section_match = re.search(
            rf'<section\b(?=[^>]*\bid="{re.escape(target)}")[^>]*>[\s\S]*?</section>',
            text,
        )
        if not section_match:
            fallback.extend(items)
            continue

        section = section_match.group(0)
        list_match = re.search(r'<ul class="grid-cards browse-grid"[^>]*>', section)
        if not list_match:
            fallback.extend(items)
            continue

        cards = "\n".join(card(p, level, i) for i, p in enumerate(items))
        insert_at = section_match.start() + section.rfind("</ul>")
        if insert_at < section_match.start():
            fallback.extend(items)
            continue
        text = text[:insert_at] + "\n" + cards + "\n" + text[insert_at:]

    if fallback:
        section = block(fallback, level)
        text = text.replace("</main>", section + "\n</main>", 1)

    page.write_text(text, encoding="utf-8")
    print(
        f"{page.name}: scanned {len(pdfs)} PDFs; placed {len(missing) - len(fallback)} "
        f"new cards in subject sections; fallback={len(fallback)}"
    )

def main():
    targets=[("foundation.html",W/"foundation","Foundation")]
    targets += [(f"year-{n}.html",W/f"year-{n}",f"Year {n}") for n in range(1,7)]
    for name,folder,level in targets:
        page=ROOT/name
        if page.exists():
            update(page,folder,level)

if __name__=="__main__":
    main()
