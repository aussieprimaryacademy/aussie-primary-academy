import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

VALIDATOR_PATH = Path(__file__).with_name("validate-sitemap-transition.py")
SPEC = importlib.util.spec_from_file_location("sitemap_transition_validator", VALIDATOR_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class SitemapTransitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def run_validator(self, previous_urls, approved_urls=""):
        previous_file = self.root / "previous-urls.txt"
        previous_file.write_text("\n".join(previous_urls), encoding="utf-8")
        allowlist = self.root / "scripts" / "expected-sitemap-removals.txt"
        allowlist.write_text(approved_urls, encoding="utf-8")
        output = io.StringIO()
        with (
            patch.object(VALIDATOR, "ROOT", self.root),
            patch.object(VALIDATOR, "sitemap_urls", return_value=set()),
            patch.object(VALIDATOR.sys, "argv", ["validate-sitemap-transition.py", str(previous_file)]),
            contextlib.redirect_stdout(output),
        ):
            VALIDATOR.main()
        return output.getvalue()

    def test_exact_approved_missing_source_passes(self):
        approved_url = (
            VALIDATOR.GENERATOR.BASE
            + "pages/foundation-science-grouping-living-things.html"
        )
        output = self.run_validator([approved_url], approved_url + "\n")
        self.assertIn("Sitemap URL comparison passed", output)

    def test_unapproved_missing_source_fails_with_nonzero_exit(self):
        unapproved_url = (
            VALIDATOR.GENERATOR.BASE
            + "pages/unreviewed-deleted-page.html"
        )
        with self.assertRaisesRegex(
            SystemExit, "ERROR: unexplained sitemap removals require manual review."
        ) as raised:
            self.run_validator([unapproved_url])
        self.assertEqual(raised.exception.code, "ERROR: unexplained sitemap removals require manual review.")

    def _page(self, name, canonical=None, noindex=False):
        pages = self.root / "pages"
        pages.mkdir(exist_ok=True)
        head = ""
        if canonical:
            head += f'<link rel="canonical" href="{VALIDATOR.GENERATOR.BASE}{canonical}">'
        if noindex:
            head += '<meta name="robots" content="noindex">'
        (pages / name).write_text(f"<html><head>{head}</head><body><p>x</p></body></html>", encoding="utf-8")
        return pages / name

    def test_canonical_elsewhere_removal_is_expected(self):
        self._page("primary.html", canonical="pages/primary.html")
        self._page("duplicate.html", canonical="pages/primary.html")
        url = VALIDATOR.GENERATOR.BASE + "pages/duplicate.html"
        with patch.object(VALIDATOR.GENERATOR, "ROOT", self.root):
            output = self.run_validator([url])
        self.assertIn("Sitemap URL comparison passed", output)

    def test_self_canonical_removal_still_fails(self):
        self._page("primary.html", canonical="pages/primary.html")
        url = VALIDATOR.GENERATOR.BASE + "pages/primary.html"
        with patch.object(VALIDATOR.GENERATOR, "ROOT", self.root):
            with self.assertRaises(SystemExit):
                self.run_validator([url])

    def test_canonical_to_missing_or_noindex_target_still_fails(self):
        self._page("a.html", canonical="pages/missing.html")
        self._page("noidx.html", noindex=True)
        self._page("b.html", canonical="pages/noidx.html")
        for name in ("a.html", "b.html"):
            url = VALIDATOR.GENERATOR.BASE + "pages/" + name
            with patch.object(VALIDATOR.GENERATOR, "ROOT", self.root):
                with self.assertRaises(SystemExit):
                    self.run_validator([url])

    def test_canonical_chain_is_not_excluded(self):
        self._page("end.html", canonical="pages/end.html")
        self._page("mid.html", canonical="pages/end.html")
        self._page("start.html", canonical="pages/mid.html")
        with patch.object(VALIDATOR.GENERATOR, "ROOT", self.root):
            self.assertFalse(VALIDATOR.GENERATOR.canonical_elsewhere(self.root / "pages" / "start.html", root=self.root))
            self.assertTrue(VALIDATOR.GENERATOR.canonical_elsewhere(self.root / "pages" / "mid.html", root=self.root))


if __name__ == "__main__":
    unittest.main()
