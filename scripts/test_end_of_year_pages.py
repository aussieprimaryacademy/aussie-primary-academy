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

    def test_year_pages_have_end_of_year_cards(self):
        for year in (1, 2, 3, 4, 5, 6):
            html = (ROOT / f"year-{year}.html").read_text(encoding="utf-8")
            self.assertIn("APA-END-OF-YEAR:START", html)
            self.assertIn("End-of-Year Resources", html)
        self.assertIn("Secondary School Transition Workbook", (ROOT / "year-6.html").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
