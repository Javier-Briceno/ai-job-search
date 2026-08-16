import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from tools.finalize_application import (
    FinalizationError,
    load_clean_receipt,
    run_export,
    safe_filename_component,
    sha256,
    validate_date,
    validate_slug,
    verify_receipt_hashes,
)


class NamingTests(unittest.TestCase):
    def test_slug_accepts_delivery_safe_value(self):
        self.assertEqual(validate_slug("wisag_kaufmaennisch-2"), "wisag_kaufmaennisch-2")

    def test_slug_rejects_path_traversal(self):
        for value in ("../outside", "company/role", "..", " space"):
            with self.subTest(value=value), self.assertRaises(FinalizationError):
                validate_slug(value)

    def test_candidate_name_is_safe_for_windows(self):
        self.assertEqual(safe_filename_component('Sara: Smani?'), "Sara- Smani-")

    def test_date_rejects_traversal_and_impossible_calendar_value(self):
        for value in ("../outside", "2026-02-30", "15-08-2026"):
            with self.subTest(value=value), self.assertRaises(FinalizationError):
                validate_date(value)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        (self.repo / "cv").mkdir()
        (self.repo / "cover_letters").mkdir()
        self.cv_source = self.repo / "cv" / "main_test.tex"
        self.cv_pdf = self.repo / "cv" / "main_test.pdf"
        self.cover_source = self.repo / "cover_letters" / "cover_test.tex"
        self.cover_pdf = self.repo / "cover_letters" / "cover_test.pdf"
        for path, content in (
            (self.cv_source, b"cv source"),
            (self.cv_pdf, b"cv pdf"),
            (self.cover_source, b"cover source"),
            (self.cover_pdf, b"cover pdf"),
        ):
            path.write_bytes(content)
        self.receipt = {
            "version": 1,
            "slug": "test_role",
            "status": "clean",
            "documents": {
                "cv": {
                    "source": "cv/main_test.tex",
                    "source_sha256": sha256(self.cv_source),
                    "pdf": "cv/main_test.pdf",
                    "pdf_sha256": sha256(self.cv_pdf),
                },
                "cover": {
                    "source": "cover_letters/cover_test.tex",
                    "source_sha256": sha256(self.cover_source),
                    "pdf": "cover_letters/cover_test.pdf",
                    "pdf_sha256": sha256(self.cover_pdf),
                },
            },
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_hash_gate_accepts_unchanged_documents(self):
        paths = verify_receipt_hashes(self.receipt, self.repo)
        self.assertEqual(paths["cv"][1], self.cv_pdf)

    def test_hash_gate_rejects_source_edited_after_check(self):
        self.cv_source.write_bytes(b"edited")
        with self.assertRaisesRegex(FinalizationError, "changed after check"):
            verify_receipt_hashes(self.receipt, self.repo)

    def test_load_rejects_failed_receipt(self):
        path = self.repo / "receipt.json"
        path.write_text(json.dumps({"version": 1, "status": "failed"}), encoding="utf-8")
        with self.assertRaisesRegex(FinalizationError, "did not pass"):
            load_clean_receipt(path)

    def test_export_requires_explicit_visual_approval(self):
        args = Namespace(visual_approved=False)
        with self.assertRaisesRegex(FinalizationError, "visual approval"):
            run_export(args)

    def test_export_copies_only_checked_pdfs(self):
        build = self.repo / ".application-build" / "test_role"
        build.mkdir(parents=True)
        receipt_path = build / "receipt.json"
        receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        args = Namespace(
            visual_approved=True,
            slug="test_role",
            candidate_name="Sara Smani",
            date="2026-08-15",
            delivery_root="deliveries",
            document_language="de",
        )

        with patch("tools.finalize_application.Path.cwd", return_value=self.repo):
            exit_code = run_export(args)

        self.assertEqual(exit_code, 0)
        destination = self.repo / "deliveries" / "2026-08-15" / "test_role"
        self.assertEqual((destination / "Sara Smani-Lebenslauf.pdf").read_bytes(), b"cv pdf")
        self.assertEqual((destination / "Sara Smani-Anschreiben.pdf").read_bytes(), b"cover pdf")
        saved = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertTrue(saved["visual_approved"])

    def test_export_can_use_english_document_names(self):
        build = self.repo / ".application-build" / "test_role"
        build.mkdir(parents=True)
        (build / "receipt.json").write_text(json.dumps(self.receipt), encoding="utf-8")
        args = Namespace(
            visual_approved=True,
            slug="test_role",
            candidate_name="Sara-Smani",
            date="2026-08-15",
            delivery_root="deliveries",
            document_language="en",
        )

        with patch("tools.finalize_application.Path.cwd", return_value=self.repo):
            run_export(args)

        destination = self.repo / "deliveries" / "2026-08-15" / "test_role"
        self.assertTrue((destination / "Sara-Smani-CV.pdf").is_file())
        self.assertTrue((destination / "Sara-Smani-Cover-Letter.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
