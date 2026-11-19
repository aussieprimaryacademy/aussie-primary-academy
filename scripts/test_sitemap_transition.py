import importlib.util
import tempfile
import unittest
from pathlib import Path

VALIDATOR_PATH = Path(__file__).with_name("validate-sitemap-transition.py")
SPEC = importlib.util.spec_from_file_location("sitemap_transition_validator", VALIDATOR_PATH)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class SitemapTransitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_approved_missing_source_is_accepted(self):
        approved_url = (
            VALIDATOR.GENERATOR.BASE
            + "pages/foundation-science-grouping-living-things.html"
        )
        result = VALIDATOR.find_unexpected_removals(
            [approved_url],
            root=self.root,
            approved_missing_sources={approved_url},
        )
        self.assertEqual(result, [])

    def test_unapproved_missing_source_is_rejected(self):
        unapproved_url = (
            VALIDATOR.GENERATOR.BASE
            + "pages/unreviewed-deleted-page.html"
        )
        result = VALIDATOR.find_unexpected_removals(
            [unapproved_url],
            root=self.root,
            approved_missing_sources=set(),
        )
        self.assertEqual(
            result,
            [unapproved_url + " (source file missing; manual review required)"],
        )


if __name__ == "__main__":
    unittest.main()
