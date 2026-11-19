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


if __name__ == "__main__":
    unittest.main()
