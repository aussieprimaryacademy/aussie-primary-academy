"""Quality checks for curated End-of-Year pages and their integrations."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = [
    ("pages/free-printable-secondary-school-transition-workbook-worksheet.html", "worksheets/end-of-year-worksheets/year-6-secondary-school-transition-workbook-free-printable.pdf", "worksheets/end-of-year-worksheets/previews/year-6-secondary-school-transition-workbook-free-printable.png"),
    ("pages/free-printable-years-1-2-my-school-year-memory-book-worksheet.html", "worksheets/end-of-year-worksheets/years-1-2-my-school-year-memory-book-free-printable.pdf", "worksheets/end-of-year-worksheets/previews/years-1-2-my-school-year-memory-book-free-printable.png"),
    ("pages/free-printable-years-1-2-school-swimming-preparation-reflection-pack-worksheet.html", "worksheets/end-of-year-worksheets/years-1-2-school-swimming-preparation-reflection-pack-free-printable.pdf", "worksheets/end-of-year-worksheets/previews/years-1-2-school-swimming-preparation-reflection-pack-free-printable.png"),
    ("pages/free-printable-years-3-6-my-school-year-memory-book-worksheet.html", "worksheets/end-of-year-worksheets/years-3-6-my-school-year-memory-book-free-printable.pdf", "worksheets/end-of-year-worksheets/previews/years-3-6-my-school-year-memory-book-free-printable.png"),
    ("pages/free-printable-years-3-6-school-swimming-preparation-reflection-pack-worksheet.html", "worksheets/end-of-year-worksheets/years-3-6-school-swimming-preparation-reflection-pack-free-printable.pdf", "worksheets/end-of-year-worksheets/previews/years-3-6-school-swimming-preparation-reflection-pack-free-printable.png"),
]

class EndOfYearPageTests(unittest.TestCase):
    def test_curated_pages_have_editorial_sections_and_real_assets(self):
        for page_name, pdf, preview in RESOURCES:
            with self.subTest(page=page_name):
                page = ROOT / page_name
                self.assertTrue(page.is_file(), f"Missing curated page: {page_name}")
                self.assertTrue((ROOT / pdf).is_file(), f"Missing PDF: {pdf}")
                self.assertTrue((ROOT / preview).is_file(), f"Missing preview: {preview}")
                html = page.read_text(encoding="utf-8")
                self.assertIn('lang="en-AU"', html)
                self.assertIn('<link rel="canonical"', html)
                self.assertIn("<h1>", html)
                self.assertIn("How teachers can use it", html)
                self.assertIn("Guidance for parents and carers", html)
                self.assertIn("Inclusive ways to adapt the activities", html)
                self.assertIn("Frequently asked questions", html)
                self.assertIn('href="../' + pdf + '"', html)
                self.assertIn('src="../' + preview + '"', html)
                self.assertNotIn("ready-to-use printable worksheet", html.lower())
                self.assertNotIn("Not specified on the worksheet filename", html)

    def test_swimming_pages_include_clear_supervision_warning(self):
        for page_name, _, _ in (RESOURCES[2], RESOURCES[4]):
            html = (ROOT / page_name).read_text(encoding="utf-8")
            self.assertIn("Important water-safety reminder", html)
            self.assertIn("active, attentive adult supervision", html)
            self.assertIn("qualified swimming instruction", html)

    def test_memory_books_protect_student_privacy(self):
        for page_name, _, _ in (RESOURCES[1], RESOURCES[3]):
            html = (ROOT / page_name).read_text(encoding="utf-8").lower()
            self.assertIn("private", html)
            self.assertIn("choose", html)

    def test_catalogue_contains_all_five_resource_pages(self):
        html = (ROOT / "worksheets.html").read_text(encoding="utf-8")
        for page_name, _, _ in RESOURCES:
            self.assertIn(page_name, html)

    def test_catalogue_drops_removed_grouping_living_things_assets(self):
        html = (ROOT / "worksheets.html").read_text(encoding="utf-8")
        self.assertNotIn("free-printable-foundation-science-grouping-living-things-worksheet-ac9sfu01-free-printable-colour-worksheet.html", html)
        self.assertNotIn("foundation-science-grouping-living-things-worksheet-ac9sfu01-free-printable-colour.pdf", html)

    def test_sitemap_contains_all_five_resource_pages(self):
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        for page_name, _, _ in RESOURCES:
            canonical = "https://aussieprimaryacademy.github.io/aussie-primary-academy/" + page_name
            with self.subTest(page=page_name):
                self.assertEqual(sitemap.count(canonical), 1, f"Expected exactly one sitemap URL for {page_name}")
        self.assertNotIn("pages/foundation-science-grouping-living-things.html", sitemap)
        self.assertNotIn("pages/free-printable-foundation-science-grouping-living-things-worksheet-ac9sfu01-free-printable-colour-worksheet.html", sitemap)

    def test_beginning_sounds_pages_share_one_indexable_canonical(self):
        primary_name = "foundation-english-beginning-sounds.html"
        names = [
            primary_name,
            "free-printable-foundation-english-beginning-sounds-phonics-worksheet-ac9efly10-free-printable-colour-worksheet.html",
            "free-printable-foundation-english-foundation-english-beginning-sounds-phonics-worksheet-ac9efly10-free-printable-colour-worksheet.html",
            "free-printable-foundation-phonics-foundation-english-beginning-sounds-phonics-worksheet-ac9efly10-free-printable-colour-worksheet.html",
        ]
        primary_url = (
            "https://aussieprimaryacademy.github.io/aussie-primary-academy/pages/"
            + primary_name
        )
        titles = []
        for name in names:
            html = (ROOT / "pages" / name).read_text(encoding="utf-8")
            canonical = html.split('rel="canonical"', 1)[1].split(">", 1)[0]
            with self.subTest(page=name):
                self.assertIn(f'href="{primary_url}"', canonical)
            title = html.split("<title>", 1)[1].split("</title>", 1)[0]
            titles.append(title)

        self.assertEqual(len(titles), len(set(titles)))
        for name in names[2:]:
            html = (ROOT / "pages" / name).read_text(encoding="utf-8")
            self.assertIn('name="robots" content="noindex, follow"', html)
        for name in names[:2]:
            html = (ROOT / "pages" / name).read_text(encoding="utf-8")
            self.assertNotIn('name="robots" content="noindex, follow"', html)

        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count(primary_url), 1)
        for name in names[1:]:
            duplicate_url = (
                "https://aussieprimaryacademy.github.io/aussie-primary-academy/pages/"
                + name
            )
            self.assertNotIn(duplicate_url, sitemap)

    def test_year_pages_have_end_of_year_cards(self):
        for year in (1, 2, 3, 4, 5, 6):
            html = (ROOT / f"year-{year}.html").read_text(encoding="utf-8")
            self.assertIn("APA-END-OF-YEAR:START", html)
            self.assertIn("End-of-Year Resources", html)
        self.assertIn("Secondary School Transition Workbook", (ROOT / "year-6.html").read_text(encoding="utf-8"))
        for year in (1, 2):
            html = (ROOT / f"year-{year}.html").read_text(encoding="utf-8")
            self.assertIn("My School Year Memory Book", html)
            self.assertIn("School Swimming Preparation &amp; Reflection Pack", html)
        for year in (3, 4, 5, 6):
            html = (ROOT / f"year-{year}.html").read_text(encoding="utf-8")
            self.assertIn("Years 3–6", html)
            self.assertIn("My School Year Memory Book", html)
            self.assertIn("School Swimming Preparation &amp; Reflection Pack", html)


    def test_end_of_year_hub_and_discoverability(self):
        hub = (ROOT / "end-of-year.html").read_text(encoding="utf-8")
        self.assertIn("<title>End-of-Year Worksheets", hub)
        self.assertIn('rel="canonical"', hub)
        self.assertIn("Memories &amp; Reflection", hub)
        self.assertIn("Moving Up to High School", hub)
        self.assertIn("Swimming &amp; Water Safety", hub)
        self.assertIn("Summer Safety", hub)
        self.assertIn("Holiday Learning", hub)
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count("https://aussieprimaryacademy.github.io/aussie-primary-academy/end-of-year.html"), 1)
        self.assertIn("Finish the School Year Strong", (ROOT / "index.html").read_text(encoding="utf-8"))
        catalogue = (ROOT / "worksheets.html").read_text(encoding="utf-8")
        self.assertIn('id="end-of-year-filter"', catalogue)
        self.assertIn('data-end-of-year="true"', catalogue)

    def test_year_level_end_of_year_sections_are_near_top(self):
        for year in range(1, 7):
            html = (ROOT / f"year-{year}.html").read_text(encoding="utf-8")
            hero_end = html.index("</section>", html.index("<h1"))
            eoy_start = html.index("APA-END-OF-YEAR:START")
            self.assertGreater(eoy_start, hero_end)
            self.assertLess(eoy_start - hero_end, 120)

if __name__ == "__main__":
    unittest.main()
