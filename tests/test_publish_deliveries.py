import csv
import tempfile
import unittest
from pathlib import Path

from tools.publish_deliveries import publish, safe_component, validate_destination


HEADER = [
    "date", "company", "sector", "role", "role_type", "channel", "status",
    "contact_person", "fit_rating", "notes", "cv_file", "cover_letter_file", "source",
]


class PublishDeliveriesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        source = self.repo / "deliveries" / "2026-08-13" / "acme_gmbh_finance_analyst"
        source.mkdir(parents=True)
        (source / "Candidate-CV.pdf").write_bytes(b"%PDF-cv")
        (source / "Candidate-Cover-Letter.pdf").write_bytes(b"%PDF-cover")
        self.tracker = self.repo / "job_search_tracker.csv"
        with self.tracker.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADER)
            writer.writeheader()
            writer.writerow({
                "date": "2026-08-13", "company": "Acme: GmbH", "role": "Finance/Analyst",
                "status": "drafted", "fit_rating": "90", "source": "https://example.com/job",
                "cv_file": "cv/main_acme.tex", "cover_letter_file": "cover_letters/acme.tex",
            })
            writer.writerow({"date": "2026-08-12", "company": "Old", "role": "Role", "status": "applied"})
        self.destination = self.root / "Applications"

    def tearDown(self):
        self.temp.cleanup()

    def test_company_position_layout_and_index(self):
        drafts, copied = publish(self.repo, self.tracker, self.destination, "2026-08-13")
        folder = self.destination / "Acme- GmbH" / "Finance-Analyst"
        self.assertEqual((drafts, copied), (1, 2))
        self.assertTrue((folder / "Candidate-CV.pdf").is_file())
        self.assertTrue((folder / "Candidate-Cover-Letter.pdf").is_file())
        page = (self.destination / "index.html").read_text(encoding="utf-8")
        self.assertIn("Acme-%20GmbH/Finance-Analyst/Candidate-CV.pdf", page)
        self.assertNotIn("Old", page)

    def test_existing_company_and_position_folders_are_reused_without_deletion(self):
        folder = self.destination / "Acme- GmbH" / "Finance-Analyst"
        folder.mkdir(parents=True)
        marker = folder / "my-note.txt"
        marker.write_text("keep", encoding="utf-8")
        publish(self.repo, self.tracker, self.destination, "2026-08-13")
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_windows_names_are_sanitized(self):
        self.assertEqual(safe_component('A<B>:C"D/E\\F|G?H*', "fallback"), "A-B--C-D-E-F-G-H-")
        self.assertEqual(safe_component("CON", "fallback"), "_CON")

    def test_repository_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_destination(self.repo, self.repo / "shared")


if __name__ == "__main__":
    unittest.main()
