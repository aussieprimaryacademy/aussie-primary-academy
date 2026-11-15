import tempfile
import unittest
from pathlib import Path

from worksheet_page_paths import page_matches_pdf, page_is_indexable, resolve_page_path


class WorksheetPagePathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.worksheets = self.root / "worksheets"
        self.pages = self.root / "pages"
        self.worksheets.mkdir()
        self.pages.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def make_pdf(self, relative, content):
        path = self.worksheets / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def base_page(self, name, pdf):
        page = self.pages / name
        page.write_text(
            '<html><a class="download" href="../' + pdf.relative_to(self.root).as_posix()
            + '" download>Download</a></html>',
            encoding="utf-8",
        )
        return page

    def test_existing_owner_keeps_legacy_url(self):
        pdf = self.make_pdf("year-2/maths/year-2-counting.pdf", b"year 2")
        page = self.base_page("counting.html", pdf)
        resolved = resolve_page_path(pdf, page, self.root, self.worksheets, self.pages)
        self.assertEqual(resolved, page)
        self.assertTrue(page_matches_pdf(resolved, pdf, self.root))

    def test_different_pdf_gets_unique_year_and_subject_path(self):
        owner = self.make_pdf("year-2/maths/year-2-counting.pdf", b"year 2")
        other = self.make_pdf("year-1/maths/year-1-counting.pdf", b"year 1")
        page = self.base_page("counting.html", owner)
        resolved = resolve_page_path(other, page, self.root, self.worksheets, self.pages)
        self.assertNotEqual(resolved, page)
        self.assertIn("year-1-maths", resolved.name)
        self.assertFalse(resolved.exists())

    def test_identical_duplicate_pdf_can_share_existing_page(self):
        owner = self.make_pdf("foundation/english/letter-formation.pdf", b"same worksheet")
        duplicate = self.make_pdf("foundation/writing/letter-formation.pdf", b"same worksheet")
        page = self.base_page("letter-formation.html", owner)
        resolved = resolve_page_path(duplicate, page, self.root, self.worksheets, self.pages)
        self.assertEqual(resolved, page)


    def test_noindex_alias_resolves_to_its_indexable_canonical_page(self):
        pdf = self.make_pdf("foundation/maths/part-whole.pdf", b"part whole")
        alias = self.pages / "legacy-part-whole.html"
        canonical = self.pages / "foundation-part-whole.html"
        download = '<a class="download" href="../' + pdf.relative_to(self.root).as_posix() + '" download>Download</a>'
        canonical.write_text('<html>' + download + '</html>', encoding="utf-8")
        alias.write_text(
            '<html><meta name="robots" content="noindex, follow">'
            '<link rel="canonical" href="https://aussieprimaryacademy.github.io/aussie-primary-academy/pages/foundation-part-whole.html">'
            + download + '</html>',
            encoding="utf-8",
        )
        resolved = resolve_page_path(pdf, alias, self.root, self.worksheets, self.pages)
        self.assertEqual(resolved, canonical)
        self.assertFalse(page_is_indexable(alias, self.root))
        self.assertTrue(page_is_indexable(canonical, self.root))

    def test_new_unclaimed_pdf_keeps_legacy_slug(self):
        pdf = self.make_pdf("year-3/science/new-topic.pdf", b"new")
        page = self.pages / "new-topic.html"
        resolved = resolve_page_path(pdf, page, self.root, self.worksheets, self.pages)
        self.assertEqual(resolved, page)


if __name__ == "__main__":
    unittest.main()
