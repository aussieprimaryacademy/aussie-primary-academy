#!/usr/bin/env python3
"""Generate the auto-managed worksheet catalogue in worksheets.html."""

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
    "usa": "USA", "us": "USA",
}

SKILL_RULES = [
    ("fractions", "Fractions"), ("fraction", "Fractions"),
    ("phonics", "Phonics"), ("cvc", "Phonics"),
    ("reading", "Reading"), ("comprehension", "Reading"),
    ("naplan", "NAPLAN"),
    ("measurement", "Measurement"), ("metric", "Measurement"),
    ("length", "Measurement"), ("mass", "Measurement"), ("capacity", "Measurement"),
    ("time", "Time"), ("money", "Money"),
    ("addition", "Number"), ("subtraction", "Number"),
    ("multiplication", "Number"), ("division", "Number"),
    ("number", "Number"), ("place-value", "Number"), ("place value", "Number"),
    ("spelling", "Spelling"), ("grammar", "Grammar"),
    ("apostrophe", "Grammar"), ("punctuation", "Grammar"),
    ("writing", "Writing"), ("sentences", "Writing"), ("sentence", "Writing"),
    ("science", "Science"),
]


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
        "science": "Science", "reading": "Reading", "writing": "Writing", "phonics": "Phonics",
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


def skill_for(path: Path, title: str, subject: str) -> str:
    haystack = f"{path.as_posix()} {title} {subject}".lower()
    for needle, skill in SKILL_RULES:
        if needle in haystack:
            return skill
    return subject if subject not in {"Worksheet", "Math"} else "General"


def card(path: Path, index: int) -> str:
    rel = path.relative_to(ROOT).as_posix()
    region, level, subject = level_and_subject(path.relative_to(WORKSHEETS_DIR))
    title = human_title(path, level, subject)
    skill = skill_for(path, title, subject)
    colour = f"c{index % 4 + 1}"
    search_text = f"{title} {skill} {level} {subject} {region}"
    return (
        '      <li class="wcard auto-worksheet-card" '
        f'data-region="{escape(region, quote=True)}" '
        f'data-year="{escape(level, quote=True)}" '
        f'data-subject="{escape(subject, quote=True)}" '
        f'data-skill="{escape(skill, quote=True)}" '
        f'data-search="{escape(search_text, quote=True)}">'
        f'<div class="thumb {colour}">{escape(level)} · {escape(subject)}</div>'
        '<div class="body">'
        f'<p class="tag">{escape(region)} · {escape(skill)} · Free PDF</p>'
        f'<h3>{escape(title)}</h3>'
        f'<a class="btn btn-primary btn-sm" href="{escape(rel, quote=True)}" download target="_blank" rel="noopener">⬇ Download PDF</a>'
        '</div></li>'
    )


def generated_section(paths: list[Path]) -> str:
    cards = "\n".join(card(path, index) for index, path in enumerate(paths))
    return f'''{START}
<section class="section" id="worksheet-catalogue" aria-labelledby="worksheet-catalogue-heading">
  <div class="wrap">
    <div class="worksheet-finder-panel">
      <div class="section-head"><div>
        <p class="eyebrow">Find exactly what you need</p>
        <h2 id="worksheet-catalogue-heading">Search the Worksheet Catalogue</h2>
        <p>Search by worksheet name or skill, then narrow the results by year, subject and topic.</p>
      </div></div>
      <div class="worksheet-filter-grid">
        <div class="worksheet-filter-field">
          <label for="worksheet-search">Search</label>
          <input id="worksheet-search" type="search" placeholder="e.g. fractions, phonics, measurement" autocomplete="off">
        </div>
        <div class="worksheet-filter-field">
          <label for="worksheet-year">Year</label>
          <select id="worksheet-year">
            <option value="">All years</option>
            <option>Foundation</option>
            <option>Year 1</option><option>Year 2</option><option>Year 3</option><option>Year 4</option><option>Year 5</option><option>Year 6</option>
            <option>Kindergarten</option>
            <option>Grade 1</option><option>Grade 2</option><option>Grade 3</option><option>Grade 4</option><option>Grade 5</option><option>Grade 6</option>
          </select>
        </div>
        <div class="worksheet-filter-field">
          <label for="worksheet-subject">Subject</label>
          <select id="worksheet-subject">
            <option value="">All subjects</option>
            <option>Maths</option><option>Math</option><option>English</option><option>ELA</option><option>Science</option><option>Reading</option><option>Writing</option><option>Phonics</option>
          </select>
        </div>
        <div class="worksheet-filter-field">
          <label for="worksheet-skill">Topic / Skill</label>
          <select id="worksheet-skill"><option value="">All topics</option></select>
        </div>
        <button class="btn btn-secondary worksheet-clear-button" id="worksheet-clear-filters" type="button">Clear Filters</button>
      </div>
      <div class="worksheet-quick-skills" aria-label="Popular skill collections">
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Fractions" aria-pressed="false">Fractions Progression</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Phonics" aria-pressed="false">Phonics Sequence</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Reading" aria-pressed="false">Reading Comprehension Series</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Measurement" aria-pressed="false">Measurement</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="NAPLAN" aria-pressed="false">NAPLAN Practice</button>
      </div>
      <div class="worksheet-filter-summary" aria-live="polite">
        <p id="worksheet-results-count">Showing 0 worksheets</p>
        <p>Use the filters to jump straight to a skill.</p>
      </div>
    </div>
  </div>
</section>

<section class="section" id="all-worksheet-downloads" aria-labelledby="all-worksheet-heading">
  <div class="wrap">
    <div class="section-head"><div>
      <p class="eyebrow">Automatically updated catalogue</p>
      <h2 id="all-worksheet-heading">All Worksheet Downloads</h2>
      <p>{len(paths)} free printable PDF worksheets currently available.</p>
    </div></div>
    <ul class="grid-cards" id="worksheet-results">
{cards}
    </ul>
    <div class="worksheet-no-results" id="worksheet-no-results" hidden>
      <strong>No worksheets match those filters.</strong>
      <p>Try a broader search or clear the filters to see all available worksheets.</p>
    </div>
    <div class="worksheet-load-more-wrap" id="worksheet-load-more-wrap" hidden>
      <button class="btn btn-secondary" id="worksheet-load-more" type="button">Show more worksheets</button>
    </div>
  </div>
</section>

<script>
(function () {{
  const cards = Array.from(document.querySelectorAll('.auto-worksheet-card'));
  const search = document.getElementById('worksheet-search');
  const year = document.getElementById('worksheet-year');
  const subject = document.getElementById('worksheet-subject');
  const skill = document.getElementById('worksheet-skill');
  const clear = document.getElementById('worksheet-clear-filters');
  const count = document.getElementById('worksheet-results-count');
  const empty = document.getElementById('worksheet-no-results');
  const moreWrap = document.getElementById('worksheet-load-more-wrap');
  const more = document.getElementById('worksheet-load-more');
  const chips = Array.from(document.querySelectorAll('[data-skill-filter]'));
  const pageSize = 24;
  let visibleLimit = pageSize;

  const skills = [...new Set(cards.map(card => card.dataset.skill).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  skills.forEach(value => {{
    const option = document.createElement('option');
    option.value = value;
    option.textContent = value;
    skill.appendChild(option);
  }});

  function normalise(value) {{ return (value || '').toLowerCase().trim(); }}
  function matches(card) {{
    const query = normalise(search.value);
    const text = normalise(card.dataset.search);
    return (!query || text.includes(query))
      && (!year.value || card.dataset.year === year.value)
      && (!subject.value || card.dataset.subject === subject.value)
      && (!skill.value || card.dataset.skill === skill.value);
  }}

  function applyFilters(resetLimit = true) {{
    if (resetLimit) visibleLimit = pageSize;
    const matching = cards.filter(matches);
    cards.forEach(card => {{ card.hidden = true; }});
    matching.slice(0, visibleLimit).forEach(card => {{ card.hidden = false; }});
    count.textContent = matching.length === 1 ? 'Showing 1 worksheet' : `Showing ${{matching.length}} worksheets`;
    empty.hidden = matching.length !== 0;
    moreWrap.hidden = matching.length <= visibleLimit;
    more.textContent = `Show more worksheets (${{Math.min(pageSize, matching.length - visibleLimit)}})`;
    chips.forEach(chip => chip.setAttribute('aria-pressed', skill.value === chip.dataset.skillFilter ? 'true' : 'false'));
  }}

  [search, year, subject, skill].forEach(control => control.addEventListener('input', () => applyFilters()));
  [year, subject, skill].forEach(control => control.addEventListener('change', () => applyFilters()));
  clear.addEventListener('click', () => {{
    search.value = ''; year.value = ''; subject.value = ''; skill.value = '';
    applyFilters(); search.focus();
  }});
  chips.forEach(chip => chip.addEventListener('click', () => {{
    skill.value = skill.value === chip.dataset.skillFilter ? '' : chip.dataset.skillFilter;
    applyFilters();
    document.getElementById('all-worksheet-downloads').scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}));
  more.addEventListener('click', () => {{ visibleLimit += pageSize; applyFilters(false); }});
  applyFilters();
}})();
</script>
{END}'''


def remove_legacy_finder(text: str) -> str:
    """Remove the older manually-maintained finder so only one filter UI remains."""
    pattern = r'\n<section class="section" id="worksheet-finder"[\s\S]*?</section>\n(?=\s*' + re.escape(START) + r')'
    return re.sub(pattern, "\n", text, count=1)


def update_page(section: str) -> None:
    text = PAGE.read_text(encoding="utf-8")
    text = remove_legacy_finder(text)
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
    print(f"Generated worksheets.html catalogue for {len(paths)} PDFs")


if __name__ == "__main__":
    main()
