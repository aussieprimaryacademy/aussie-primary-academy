import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "related_worksheet_links", ROOT / "scripts" / "add-related-worksheet-links.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def metadata(page, title, level="Primary", subject="English"):
    return {
        "page": page,
        "title": title,
        "level": level,
        "subject": subject,
        "region": "Australia",
    }


class EndOfYearClassificationTests(unittest.TestCase):
    def classify(self, filename):
        return MODULE.apply_end_of_year_classification(
            metadata("pages/example.html", "Example"),
            Path("worksheets/end-of-year-worksheets") / filename,
        )

    def test_swimming_packs_are_hpe_and_keep_their_year_bands(self):
        cases = [
            ("years-1-2-school-swimming-preparation-reflection-pack-free-printable.pdf", "Years 1–2"),
            ("years-3-6-school-swimming-preparation-reflection-pack-free-printable.pdf", "Years 3–6"),
        ]
        for filename, level in cases:
            with self.subTest(filename=filename):
                result = self.classify(filename)
                self.assertEqual(result["subject"], "HPE")
                self.assertEqual(result["level"], level)

    def test_memory_books_are_wellbeing_and_keep_their_year_bands(self):
        cases = [
            ("years-1-2-my-school-year-memory-book-free-printable.pdf", "Years 1–2"),
            ("years-3-6-my-school-year-memory-book-free-printable.pdf", "Years 3–6"),
        ]
        for filename, level in cases:
            with self.subTest(filename=filename):
                result = self.classify(filename)
                self.assertEqual(result["subject"], "Wellbeing")
                self.assertEqual(result["level"], level)

    def test_secondary_transition_workbook_is_year_6_transition(self):
        result = self.classify("year-6-secondary-school-transition-workbook-free-printable.pdf")
        self.assertEqual(result["subject"], "Transition")
        self.assertEqual(result["level"], "Year 6")

    def test_hpe_resources_never_fall_back_to_unrelated_subjects(self):
        current = metadata("pages/swimming-1.html", "Swimming Preparation", "Years 1–2", "HPE")
        candidates = [
            current,
            metadata("pages/swimming-2.html", "Swimming Reflection", "Years 1–2", "HPE"),
            metadata("pages/english.html", "Phonics Practice", "Years 1–2", "English"),
        ]
        chosen = MODULE.select_related_candidates(current, candidates)
        self.assertEqual([item["subject"] for item in chosen], ["HPE"])

    def test_single_transition_resource_does_not_link_unrelated_year_6_subjects(self):
        current = metadata("pages/transition.html", "Secondary Transition", "Year 6", "Transition")
        candidates = [
            current,
            metadata("pages/english.html", "Grammar Practice", "Year 6", "English"),
            metadata("pages/maths.html", "Fractions", "Year 6", "Maths"),
        ]
        self.assertEqual(MODULE.select_related_candidates(current, candidates), [])


if __name__ == "__main__":
    unittest.main()
