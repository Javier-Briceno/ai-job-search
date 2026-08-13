import csv
import tempfile
import unittest
from pathlib import Path

from tools.build_delivery_report import load_drafts, render_report


HEADER = [
    "date", "company", "sector", "role", "role_type", "channel", "status",
    "contact_person", "fit_rating", "notes", "cv_file", "cover_letter_file", "source",
]


class DeliveryReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.output = self.repo / "deliveries" / "index.html"
        folder = self.repo / "deliveries" / "2026-08-13" / "acme_partners_analyst_finance"
        folder.mkdir(parents=True)
        self.cv_pdf = folder / "Candidate-CV.pdf"
        self.cover_pdf = folder / "Candidate-Cover-Letter.pdf"
        self.cv_pdf.write_bytes(b"%PDF-test")
        self.cover_pdf.write_bytes(b"%PDF-test")
        self.tracker = self.repo / "job_search_tracker.csv"
        with self.tracker.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=HEADER)
            writer.writeheader()
            writer.writerow({
                "date": "2026-08-13", "company": "Acme & Partners", "role": "Analyst <Finance>",
                "status": "drafted", "fit_rating": "82",
                # /apply intentionally records its editable sources in the tracker.
                "cv_file": "cv/main_acme_analyst.tex",
                "cover_letter_file": "cover_letters/cover_acme_analyst.tex",
                "source": "https://example.com/jobs/1?x=1&y=2",
            })
            writer.writerow({"date": "2026-08-12", "company": "Sent", "role": "Old", "status": "applied"})

    def tearDown(self):
        self.temp.cleanup()

    def test_only_drafts_are_loaded(self):
        rows = load_drafts(self.tracker)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "Acme & Partners")

    def test_html_escapes_data_and_links_existing_pdfs(self):
        page = render_report(load_drafts(self.tracker), self.repo, self.output, "2026-08-13")
        self.assertIn("Acme &amp; Partners", page)
        self.assertIn("Analyst &lt;Finance&gt;", page)
        self.assertNotIn("Analyst <Finance>", page)
        self.assertIn("2026-08-13/acme_partners_analyst_finance/Candidate-CV.pdf", page)
        self.assertIn("2026-08-13/acme_partners_analyst_finance/Candidate-Cover-Letter.pdf", page)
        self.assertIn("New today", page)
        self.assertIn("https://example.com/jobs/1?x=1&amp;y=2", page)

    def test_non_http_source_is_not_linked(self):
        rows = load_drafts(self.tracker)
        rows[0]["source"] = "javascript:alert(1)"
        page = render_report(rows, self.repo, self.output, "2026-08-13")
        self.assertNotIn("javascript:", page)

    def test_missing_pdf_is_reported_not_linked(self):
        rows = load_drafts(self.tracker)
        rows[0]["cv_file"] = "../../outside.pdf"
        self.cv_pdf.unlink()
        page = render_report(rows, self.repo, self.output, "2026-08-13")
        self.assertIn("Missing: CV", page)

    def test_missing_tracker_produces_empty_list(self):
        self.assertEqual(load_drafts(self.repo / "missing.csv"), [])


if __name__ == "__main__":
    unittest.main()
