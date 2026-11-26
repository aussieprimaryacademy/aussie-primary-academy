#!/usr/bin/env python3
"""Generate the auto-managed worksheet catalogue in worksheets.html."""

from html import escape
from pathlib import Path
import re
from worksheet_page_paths import resolve_page_path, page_matches_pdf, page_is_indexable, same_pdf_content, duplicate_pdf_target

ROOT = Path(__file__).resolve().parent.parent
WORKSHEETS_DIR = ROOT / "worksheets"
PAGE = ROOT / "worksheets.html"
START = "<!-- AUTO-WORKSHEETS:START -->"
END = "<!-- AUTO-WORKSHEETS:END -->"

ACARA_RE = re.compile(r"^ac9[a-z0-9]+$", re.IGNORECASE)
CCSS_RE = re.compile(r"^(?:ccss|[k1-6](?:cc|oa|nbt|nf|md|g|rf|ri|rl|w|l|sl))[a-z0-9-]*$", re.IGNORECASE)
CODE_FIND_RE = re.compile(
    r"(?:ac9[a-z0-9]+|(?:ccss|[k1-6](?:cc|oa|nbt|nf|md|g|rf|ri|rl|w|l|sl))[a-z0-9-]*)",
    re.IGNORECASE,
)
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
    ("memory-book", "Reflection"), ("transition", "Transition"),
    ("bushfires", "Extreme Weather"), ("extreme-weather", "Extreme Weather"),
    ("water-safety", "Water Safety"), ("swimming", "Water Safety"),
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
    ("letter-formation", "Writing"), ("writing", "Writing"),
    ("sentences", "Writing"), ("sentence", "Writing"),
    ("science", "Science"),
]


def level_and_subject(path: Path) -> tuple[str, str, str]:
    parts = [part.lower() for part in path.parts]
    if "end-of-year-worksheets" in parts:
        stem = path.stem.lower()
        if "year-6-secondary-school-transition" in stem: return "Australia", "Year 6", "Transition"
        if "years-1-2-my-school-year-memory-book" in stem: return "Australia", "Years 1–2", "Wellbeing"
        if "years-1-2-school-swimming" in stem: return "Australia", "Years 1–2", "HPE"
        if "years-3-6-my-school-year-memory-book" in stem: return "Australia", "Years 3–6", "Wellbeing"
        if "years-3-6-school-swimming" in stem: return "Australia", "Years 3–6", "HPE"
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

    stem = path.stem.lower()
    if "water-safety-swimming-workbook-year-3-4" in stem:
        return region, "Year 3–4", "HPE"
    if "bushfires-floods-extreme-weather-workbook-year-5-6" in stem:
        return region, "Year 5–6", "Science"

    subject_map = {
        "math": "Math", "maths": "Maths", "ela": "ELA", "english": "English",
        "science": "Science", "reading": "Reading", "writing": "Writing", "phonics": "Phonics",
    }
    subject = next((subject_map[p] for p in parts if p in subject_map), "Worksheet")
    return region, level, subject


def human_title(path: Path, level: str, subject: str) -> str:
    stem = path.stem.lower()
    curated_titles = {
        "year-6-secondary-school-transition-workbook-free-printable": "Secondary School Transition Workbook",
        "years-1-2-my-school-year-memory-book-free-printable": "My School Year Memory Book",
        "years-1-2-school-swimming-preparation-reflection-pack-free-printable": "School Swimming Preparation & Reflection Pack",
        "years-3-6-my-school-year-memory-book-free-printable": "My School Year Memory Book",
        "years-3-6-school-swimming-preparation-reflection-pack-free-printable": "School Swimming Preparation & Reflection Pack",
    }
    if stem in curated_titles: return curated_titles[stem]
    if "water-safety-swimming-workbook-year-3-4" in stem:
        return "Water Safety & Swimming Workbook"
    if "bushfires-floods-extreme-weather-workbook-year-5-6" in stem:
        return "Bushfires, Floods & Extreme Weather Workbook"
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


def codes_from_name(path: Path) -> str:
    """Extract ACARA / CCSS style codes from filename so they are searchable."""
    found = CODE_FIND_RE.findall(path.stem)
    return " ".join(dict.fromkeys(found))


def page_for_pdf(path: Path, level: str) -> str:
    """Return the exact individual worksheet page path used by generate-worksheet-pages.py."""
    curated = {
        "year-6-secondary-school-transition-workbook-free-printable": "pages/free-printable-secondary-school-transition-workbook-worksheet.html",
        "years-1-2-my-school-year-memory-book-free-printable": "pages/free-printable-years-1-2-my-school-year-memory-book-worksheet.html",
        "years-1-2-school-swimming-preparation-reflection-pack-free-printable": "pages/free-printable-years-1-2-school-swimming-preparation-reflection-pack-worksheet.html",
        "years-3-6-my-school-year-memory-book-free-printable": "pages/free-printable-years-3-6-my-school-year-memory-book-worksheet.html",
        "years-3-6-school-swimming-preparation-reflection-pack-free-printable": "pages/free-printable-years-3-6-school-swimming-preparation-reflection-pack-worksheet.html",
    }
    if path.stem.lower() in curated: return curated[path.stem.lower()]
    name = path.stem
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
    base_page = ROOT / "pages" / page_name
    resolved_page = resolve_page_path(path, base_page, ROOT, WORKSHEETS_DIR, ROOT / "pages")
    return resolved_page.relative_to(ROOT).as_posix()


def existing_card_colours(text: str) -> dict[str, str]:
    """Keep the existing thumbnail colour for each PDF when regenerating cards."""
    colours = {}
    for line in text.splitlines():
        pdf_match = re.search(r'href="([^"]+\.pdf)"', line, re.I)
        colour_match = re.search(r'<div class="thumb (c[1-4])">', line, re.I)
        if pdf_match and colour_match:
            colours[pdf_match.group(1)] = colour_match.group(1)
    return colours


def card(path: Path, index: int, colours: dict[str, str] | None = None) -> str:
    rel = path.relative_to(ROOT).as_posix()
    region, level, subject = level_and_subject(path.relative_to(WORKSHEETS_DIR))
    title = human_title(path, level, subject)
    skill = skill_for(path, title, subject)
    colour = (colours or {}).get(rel, f"c{index % 4 + 1}")
    codes = codes_from_name(path)
    search_text = f"{title} {skill} {level} {subject} {region} {codes} {path.stem}"
    year_filter = {"Years 1–2": "Year 1|Year 2", "Years 3–6": "Year 3|Year 4|Year 5|Year 6", "Year 3–4": "Year 3|Year 4", "Year 5–6": "Year 5|Year 6"}.get(level, level)
    stem = path.stem.lower()
    is_end_of_year = (
        "end-of-year-worksheets" in path.parts
        or "school-holiday-learning-pack" in stem
        or "water-safety-swimming-workbook-year-3-4" in stem
        or "bushfires-floods-extreme-weather-workbook-year-5-6" in stem
    )
    end_of_year_attr = ' data-end-of-year="true"' if is_end_of_year else ""
    return (
        '      <li class="wcard auto-worksheet-card" '
        f'data-region="{escape(region, quote=True)}" '
        f'data-year="{escape(year_filter, quote=True)}" '
        f'data-subject="{escape(subject, quote=True)}" '
        f'data-skill="{escape(skill, quote=True)}"'
        f'{end_of_year_attr} '
        f'data-search="{escape(search_text, quote=True)}">'
        f'<div class="thumb {colour}">{escape(level)} · {escape(subject)}</div>'
        '<div class="body">'
        f'<p class="tag">{escape(region)} · {escape(skill)} · Free PDF</p>'
        f'<h3>{escape(title)}</h3>'
        f'<p class="card-actions"><a class="btn btn-secondary btn-sm" href="{escape(page_for_pdf(path, level), quote=True)}">View Worksheet</a> '
        f'<a class="btn btn-primary btn-sm" href="{escape(rel, quote=True)}" download target="_blank" rel="noopener">⬇ Download PDF</a></p>'
        '</div></li>'
    )


def generated_section(paths: list[Path], colours: dict[str, str] | None = None) -> str:
    cards = "\n".join(card(path, index, colours) for index, path in enumerate(paths))
    return f"""{START}
<style>
.worksheet-search-button {{ min-height: 48px; white-space: nowrap; }}
@media (max-width: 850px) {{
  .worksheet-search-button {{ width: 100%; grid-column: 1 / -1; }}
}}
@media (max-width: 560px) {{
  .worksheet-filter-grid {{ grid-template-columns: 1fr; }}
}}
</style>
<section class="section" id="worksheet-catalogue" aria-labelledby="worksheet-catalogue-heading">
  <div class="wrap">
    <span id="worksheet-grid" aria-hidden="true"></span>
    <div class="worksheet-finder-panel">
      <div class="section-head"><div>
        <p class="eyebrow">Find exactly what you need</p>
        <h2 id="worksheet-catalogue-heading">Search the Worksheet Catalogue</h2>
        <p>Search by worksheet name or skill, then narrow the results by year, subject and topic.</p>
        <p class="catalogue-region-note">This catalogue contains Australian Curriculum resources. <a href="usa-worksheets.html">Browse the separate USA Common Core collection</a>.</p>
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
            <option>Maths</option><option>Math</option><option>English</option><option>ELA</option><option>Science</option><option>HPE</option><option>Wellbeing</option><option>Transition</option><option>Reading</option><option>Writing</option><option>Phonics</option>
          </select>
        </div>
        <div class="worksheet-filter-field">
          <label for="worksheet-skill">Topic / Skill</label>
          <select id="worksheet-skill"><option value="">All topics</option></select>
        </div>
        <button class="btn btn-secondary worksheet-clear-button" id="worksheet-clear-filters" type="button">Clear Filters</button>
        <button class="btn btn-primary worksheet-search-button" id="worksheet-search-button" type="button">Search Worksheets</button>
      </div>
      <div class="worksheet-quick-skills" aria-label="Popular skill collections">
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Fractions" aria-pressed="false">Fractions Progression</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Phonics" aria-pressed="false">Phonics Sequence</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Reading" aria-pressed="false">Reading Comprehension Series</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="Measurement" aria-pressed="false">Measurement</button>
        <button class="worksheet-skill-chip" type="button" data-skill-filter="NAPLAN" aria-pressed="false">NAPLAN Practice</button>
        <button class="worksheet-skill-chip" type="button" id="end-of-year-filter" aria-pressed="false">End of Year</button>
      </div>
      <div class="worksheet-filter-summary" aria-live="polite">
        <p id="worksheet-results-count">Showing {len(paths)} worksheets</p>
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
      <p>{len(paths)} free printable PDF worksheets and learning resources currently available.</p>
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
  const searchBtn = document.getElementById('worksheet-search-button');
  const count = document.getElementById('worksheet-results-count');
  const empty = document.getElementById('worksheet-no-results');
  const moreWrap = document.getElementById('worksheet-load-more-wrap');
  const more = document.getElementById('worksheet-load-more');
  const chips = Array.from(document.querySelectorAll('[data-skill-filter]'));
  const endOfYearFilter = document.getElementById('end-of-year-filter');
  let endOfYearOnly = false;
  const pageSize = 24;
  let visibleLimit = pageSize;
  let searchDebounce = null;
  let filtersLockedByUser = false;

  if (!search || !year || !subject || !skill || !clear || !count || !empty || !moreWrap || !more) {{
    return;
  }}

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
    const text = normalise(card.dataset.search || '');
    return (!query || text.includes(query))
      && (!year.value || (card.dataset.year || "").split("|").includes(year.value))
      && (!subject.value || card.dataset.subject === subject.value)
      && (!skill.value || card.dataset.skill === skill.value)
      && (!endOfYearOnly || card.dataset.endOfYear === 'true');
  }}

  function applyFilters(resetLimit = true) {{
    if (resetLimit) visibleLimit = pageSize;
    const matching = cards.filter(matches);
    cards.forEach(card => {{ card.hidden = true; }});
    matching.slice(0, visibleLimit).forEach(card => {{ card.hidden = false; }});
    count.textContent = matching.length === 1 ? 'Showing 1 worksheet' : `Showing ${{matching.length}} worksheets`;
    empty.hidden = matching.length !== 0;
    moreWrap.hidden = matching.length <= visibleLimit;
    more.textContent = `Show more worksheets (${{Math.min(pageSize, Math.max(0, matching.length - visibleLimit))}})`;
    chips.forEach(chip => chip.setAttribute('aria-pressed', skill.value === chip.dataset.skillFilter ? 'true' : 'false'));
    if (endOfYearFilter) endOfYearFilter.setAttribute('aria-pressed', endOfYearOnly ? 'true' : 'false');
  }}

  function headerOffset() {{
    const header = document.querySelector('header.site');
    const h = header ? header.getBoundingClientRect().height : 0;
    return Math.max(72, Math.round(h + 12));
  }}

  function scrollToResults() {{
    const firstCard = document.querySelector('.auto-worksheet-card:not([hidden])');
    const target = firstCard || empty || count || document.getElementById('all-worksheet-downloads');
    if (!target) return;
    const top = target.getBoundingClientRect().top + window.pageYOffset - headerOffset();
    window.scrollTo({{ top: Math.max(0, top), behavior: 'smooth' }});
  }}

  function applyAndScroll(resetLimit = true) {{
    applyFilters(resetLimit);
    requestAnimationFrame(() => {{
      setTimeout(scrollToResults, 50);
    }});
  }}

  function runTextSearch() {{
    if (searchDebounce) clearTimeout(searchDebounce);
    if (!filtersLockedByUser) {{
      year.value = '';
      subject.value = '';
      skill.value = '';
    }}
    applyAndScroll(true);
  }}

  function onSearchInput() {{
    filtersLockedByUser = false;
    if (searchDebounce) clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {{
      runTextSearch();
    }}, 400);
  }}

  function readQueryFromUrl() {{
    const params = new URLSearchParams(window.location.search);
    const q = (params.get('q') || '').trim();
    const y = (params.get('year') || '').trim();
    const s = (params.get('subject') || '').trim();
    const sk = (params.get('skill') || '').trim();
    if (q) search.value = q;
    if (y) {{ year.value = y; filtersLockedByUser = true; }}
    if (s) {{
      const matchingSubject = Array.from(subject.options).find(option => normalise(option.value) === normalise(s));
      if (matchingSubject) subject.value = matchingSubject.value;
      else subject.value = s;
      filtersLockedByUser = true;
    }}
    if (sk) {{ skill.value = sk; filtersLockedByUser = true; }}
    return Boolean(q || y || s || sk);
  }}

  search.addEventListener('input', onSearchInput);
  search.addEventListener('keydown', (e) => {{
    if (e.key === 'Enter') {{
      e.preventDefault();
      runTextSearch();
    }}
  }});
  if (searchBtn) {{
    searchBtn.addEventListener('click', () => runTextSearch());
  }}

  [year, subject, skill].forEach(control => {{
    control.addEventListener('change', () => {{
      filtersLockedByUser = true;
      applyAndScroll(true);
    }});
  }});

  clear.addEventListener('click', () => {{
    if (searchDebounce) clearTimeout(searchDebounce);
    search.value = '';
    year.value = '';
    subject.value = '';
    skill.value = '';
    endOfYearOnly = false;
    filtersLockedByUser = false;
    if (window.history && window.history.replaceState) {{
      window.history.replaceState({{}}, '', window.location.pathname + window.location.hash);
    }}
    applyAndScroll(true);
    search.focus();
  }});

  chips.forEach(chip => chip.addEventListener('click', () => {{
    if (searchDebounce) clearTimeout(searchDebounce);
    const next = skill.value === chip.dataset.skillFilter ? '' : chip.dataset.skillFilter;
    skill.value = next;
    filtersLockedByUser = true;
    applyAndScroll(true);
  }}));

  more.addEventListener('click', () => {{ visibleLimit += pageSize; applyFilters(false); }});
  if (endOfYearFilter) {{
    endOfYearFilter.addEventListener('click', () => {{
      if (searchDebounce) clearTimeout(searchDebounce);
      endOfYearOnly = !endOfYearOnly;
      applyAndScroll(true);
    }});
  }}

  const hadUrlFilter = readQueryFromUrl();
  applyFilters();
  if (hadUrlFilter) {{
    requestAnimationFrame(() => {{
      setTimeout(scrollToResults, 60);
    }});
  }}
}})();
</script>
{END}"""


def remove_legacy_finder(text: str) -> str:
    """Remove the older manually-maintained finder so only one filter UI remains."""
    pattern = r'\n<section class="section" id="worksheet-finder"[\s\S]*?</section>\n(?=\s*' + re.escape(START) + r')'
    return re.sub(pattern, "\n", text, count=1)


def remove_dead_filter_script(text: str) -> str:
    """Remove any leftover broken filter controller that used old element IDs."""
    pattern = (
        r'\n<script>\s*\(function\s*\(\)\s*\{\s*[\'"]use strict[\'\"];\s*'
        r'var catalogue = document\.querySelector\([\'"]#all-worksheet-downloads.*?</script>'
    )
    cleaned = re.sub(pattern, "\n", text, count=1, flags=re.DOTALL)
    return cleaned


def update_page(section: str) -> None:
    text = PAGE.read_text(encoding="utf-8")
    text = remove_legacy_finder(text)
    if START in text and END in text:
        before, remainder = text.split(START, 1)
        _, after = remainder.split(END, 1)
        after = remove_dead_filter_script(after)
        after = re.sub(
            r'\n<script>\s*\(function\s*\(\)\s*\{\s*[\'"]use strict[\'\"];[\s\S]*?worksheet-year-filter[\s\S]*?</script>',
            "\n",
            after,
            count=1,
        )
        updated = before + section + after
    else:
        anchor = '<section class="section" id="years">'
        if anchor not in text:
            raise SystemExit("ERROR: could not find the Year Level section in worksheets.html")
        updated = text.replace(anchor, section + "\n\n" + anchor, 1)
    PAGE.write_text(updated, encoding="utf-8")


def main() -> None:
    candidate_paths = sorted(
        (path for path in WORKSHEETS_DIR.rglob("*.pdf") if path.is_file() and not re.search(r"answer[-_ ]?(?:guide|key)|answerkey", path.name, re.I) and level_and_subject(path.relative_to(WORKSHEETS_DIR))[0] == "Australia"),
        key=lambda path: path.relative_to(ROOT).as_posix().lower(),
    )
    paths = []
    for path in candidate_paths:
        _, level, _ = level_and_subject(path.relative_to(WORKSHEETS_DIR))
        page_file = ROOT / page_for_pdf(path, level)
        duplicate_target = duplicate_pdf_target(path, page_file, ROOT)
        if duplicate_target:
            print(
                "Skipping duplicate PDF copy: "
                f"{path.relative_to(ROOT)}; canonical page links to "
                f"{duplicate_target.relative_to(ROOT)}"
            )
            continue
        paths.append(path)
    if not paths:
        raise SystemExit("ERROR: no worksheet PDFs found")
    if len({path.relative_to(ROOT).as_posix() for path in paths}) != len(paths):
        raise SystemExit("ERROR: duplicate worksheet paths found")
    current_page = PAGE.read_text(encoding="utf-8")
    colours = existing_card_colours(current_page)
    update_page(generated_section(paths, colours))
    result = PAGE.read_text(encoding="utf-8")
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        if f'href="{rel}"' not in result:
            raise SystemExit(f"ERROR: missing generated link for {rel}")

    if __import__("os").getenv("REQUIRE_PAGE_MAP_VALIDATION") == "1":
        page_owners = {}
        for path in paths:
            _, level, _ = level_and_subject(path.relative_to(WORKSHEETS_DIR))
            page_rel = page_for_pdf(path, level)
            page_file = ROOT / page_rel
            if not page_file.is_file():
                raise SystemExit(f"ERROR: individual worksheet page is missing: {page_rel} <- {path.relative_to(ROOT)}")
            if not page_matches_pdf(page_file, path, ROOT):
                raise SystemExit(f"ERROR: worksheet page links to a different PDF: {page_rel} <- {path.relative_to(ROOT)}")
            if not page_is_indexable(page_file, ROOT):
                raise SystemExit(f"ERROR: worksheet card points to a noindex or non-canonical page: {page_rel} <- {path.relative_to(ROOT)}")
            previous = page_owners.get(page_rel)
            if previous and not same_pdf_content(previous, path):
                raise SystemExit(
                    f"ERROR: different PDFs share one worksheet page: {page_rel} "
                    f"({previous.relative_to(ROOT)} and {path.relative_to(ROOT)})"
                )
            page_owners[page_rel] = path
        print(f"Verified {len(paths)} worksheet PDFs against {len(page_owners)} collision-safe landing pages.")
    if 'data-region="USA"' in result:
        raise SystemExit("ERROR: USA Common Core resources must remain in the separate USA collection")
    if "readQueryFromUrl" not in result or "URLSearchParams" not in result:
        raise SystemExit("ERROR: URL query handler missing from generated page")
    if "searchDebounce" not in result:
        raise SystemExit("ERROR: debounced search scroll missing from generated page")
    if "worksheet-search-button" not in result:
        raise SystemExit("ERROR: Search Worksheets button missing from generated page")
    if "headerOffset" not in result:
        raise SystemExit("ERROR: header-offset scroll missing from generated page")
    if "worksheet-year-filter" in result:
        raise SystemExit("ERROR: dead filter IDs still present")
    print(f"Generated worksheets.html catalogue for {len(paths)} PDFs")


if __name__ == "__main__":
    main()
