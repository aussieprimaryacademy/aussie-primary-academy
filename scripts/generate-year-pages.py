#!/usr/bin/env python3
"""Keep Australian year pages in sync with worksheet PDFs.

Adds an auto-managed "New worksheet downloads" block to Foundation-Year 6 pages.
PDFs already linked anywhere else on a year page are excluded, so curated cards
are preserved and never duplicated.
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
    drop = {"worksheet","free","printable","australia","australian","colour","color","pdf",
            "with","answers","answer","key","year",level.split()[-1].lower(),subject.lower()}
    out=[]
    for w in words:
        low=w.lower()
        if low in drop or re.fullmatch(r"year\d",low) or re.fullmatch(r"ac9[a-z0-9]+",low):
            continue
        out.append({"naplan":"NAPLAN","cvc":"CVC"}.get(low,low.capitalize()))
    return " ".join(out) or f"{level} {subject} Practice"

def subject_for(p: Path) -> str:
    parts=[x.lower() for x in p.parts]
    return next((label for key,label in SUBJECTS.items() if key in parts), "Worksheet")

def page_for_pdf(p: Path, level: str) -> str:
    """Return the exact individual worksheet page path used by generate-worksheet-pages.py."""
    name = p.stem
    lower = name.lower()
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

def update(page: Path, folder: Path, level: str):
    text=page.read_text(encoding="utf-8")
    # Remove old generated block before checking which PDFs are already curated.
    text=re.sub(re.escape(START)+r"[\s\S]*?"+re.escape(END),"",text,count=1)
    pdfs=sorted(folder.rglob("*.pdf"),key=lambda p:p.as_posix().lower()) if folder.exists() else []
    missing=[p for p in pdfs if p.relative_to(ROOT).as_posix() not in text]
    section=block(missing,level)
    if section:
        anchor="</main>"
        if anchor not in text:
            raise SystemExit(f"ERROR: </main> missing in {page.name}")
        text=text.replace(anchor,section+"\n"+anchor,1)
    page.write_text(text,encoding="utf-8")
    print(f"{page.name}: {len(pdfs)} PDFs, {len(missing)} auto-added")

def main():
    targets=[("foundation.html",W/"foundation","Foundation")]
    targets += [(f"year-{n}.html",W/f"year-{n}",f"Year {n}") for n in range(1,7)]
    for name,folder,level in targets:
        page=ROOT/name
        if page.exists():
            update(page,folder,level)

if __name__=="__main__":
    main()
