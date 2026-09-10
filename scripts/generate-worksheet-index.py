#!/usr/bin/env python3
"""Generate the auto-managed worksheet card section in worksheets.html."""

from html import escape
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
WORKSHEETS_DIR = ROOT / "worksheets"
PAGE = ROOT / "worksheets.html"
START = "<!-- AUTO-WORKSHEETS:START -->"
END = "<!-- AUTO-WORKSHEETS:END -->"

ACARA_RE = re.compile(r"^ac9[a-z0-9]+$", re.IGNORECASE)
CCSS_RE = re.compile(r"^(?:ccss|[k1-6](?:cc|oa|nbt|nf|md|g|rf|ri|rl|w|l|sl))[a-z0-9-]*$", re.IGNORECASE)
DROP_WORDS = {
    "worksheet", "worksheets", "free", "printable", "pdf", "australia",
    "australian", "colour", "color", "with", "answers", "answer", "key",
    "final", "version", "copy",
}
SPECIAL = {
    "cvc": "CVC", "ela": "ELA", "naplan": "NAPLAN", "pdf": "PDF",
    "usa": "USA", "us": "USA", "cvc": "CVC",
}


def level_and_subject(path: Path) -> tuple[str, str, str]:
    parts = [part.lower() for part in path.parts]
    region = "USA" if "usa" in parts or path.name.lower().startswith(("us-", "usa-")) else "Australia"

    level = "Worksheet"
    for part in parts:
        if part == "kindergarten":
            level = "Kindergarten"
            break
        if part == "foundation":
            level = "Foundation"
            break
        match = re.fullmatch(r"(?:year|grade)[-_ ]?(\d)", part)
        if match:
            label = "Grade" if region == "USA" else "Year"
            level = f"{label} {match.group(1)}"
            break

    subject_map = {
        "math": "Math", "maths": "Maths", "ela": "ELA", "english": "English",
        "science": "Science", "reading": "Reading", "writing": "Writing",
        "phonics": "Phonics",
    }
    subject = next((subject_map[p] for p in parts if p in subject_map), "Worksheet")
    return region, level, subject


def human_title(path: Path, level: str, subject: str) -> str:
    words = re.split(r"[-_]+", path.stem)
    kept: list[str] = []
    skip = {
        "us", "usa", "foundation", "math", "maths", "ela", "english",
        "science", "reading", "writing", "phonics",
    }
    skip.update(level.lower().split())
    skip.update(subject.lower().split())

    for word in words:
        low = word.lower()
        if low in skip or low in DROP_WORDS or low.isdigit():
            continue
        if ACARA_RE.fullmatch(low) or CCSS_RE.fullmatch(low) or re.fullmatch(r"[a-z]\d[a-z]?", low):
            continue
        if re.fullmatch(r"(?:year|grade)\d", low):
            continue
        kept.append(SPECIAL.get(low, low.capitalize()))

    title = " ".join(kept).strip()
    return title or f"{level} {subject} Practice"


def card(path: Path, index: int) -> str:
    rel = path.relative_to(ROOT).as_posix()
    region, level, subject = level_and_subject(path.relative_to(WORKSHEETS_DIR))
    title = human_title(path, level, subject)
    colour = f"c{index % 4 + 1}"
    return (
        '      <li class="wcard auto-worksheet-card">'
        f'<div class="thumb {colour}">{escape(level)} · {escape(subject)}</div>'
        '<div class="body">'
        f'<p class="tag">{escape(region)} · Free PDF</p>'
        f'<h3>{escape(title)}</h3>'
        f'<a class="btn btn-primary btn-sm" href="{escape(rel, quote=True)}" '
        'download target="_blank" rel="noopener">⬇ Download PDF</a>'
        '</div></li>'
    )


def generated_section(paths: list[Path]) -> str:
    cards = "\n".join(card(path, index) for index, path in enumerate(paths))
    return f'''{START}
<section class="section" id="all-worksheet-downloads" aria-labelledby="all-worksheet-heading">
  <div class="wrap">
    <div class="section-head"><div>
      <p class="eyebrow">Automatically updated</p>
      <h2 id="all-worksheet-heading">All Worksheet Downloads</h2>
      <p>{len(paths)} free printable PDF worksheets currently available.</p>
    </div></div>
    <ul class="grid-cards">
{cards}
    </ul>
  </div>
</section>
{END}'''


def update_page(section: str) -> None:
    text = PAGE.read_text(encoding="utf-8")
    if START in text and END in text:
        before, remainder = text.split(START, 1)
        _, after = remainder.split(END, 1)
        updated = before + section + after
    else:
        anchor = '<section class="section" id="years">'
        if anchor not in text:
            raise SystemExit("ERROR: could not find the Year Level section in worksheets.html")
        updated = text.replace(anchor, section + "\n\n" + anchor, 1)
    PAGE.write_text(updated, encoding="utf-8")


def main() -> None:
    paths = sorted(
        (path for path in WORKSHEETS_DIR.rglob("*.pdf") if path.is_file()),
        key=lambda path: path.relative_to(ROOT).as_posix().lower(),
    )
    if not paths:
        raise SystemExit("ERROR: no worksheet PDFs found")
    if len({path.relative_to(ROOT).as_posix() for path in paths}) != len(paths):
        raise SystemExit("ERROR: duplicate worksheet paths found")

    update_page(generated_section(paths))
    result = PAGE.read_text(encoding="utf-8")
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        if f'href="{rel}"' not in result:
            raise SystemExit(f"ERROR: missing generated link for {rel}")
    print(f"Generated worksheets.html cards for {len(paths)} PDFs")


if __name__ == "__main__":
    main()
