import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verify_pdf import (
    FAIL,
    PASS,
    SKIP,
    ToolUnavailable,
    VerificationError,
    find_disallowed_symbols,
    find_fused_terms,
    find_glyph_name_leaks,
    find_hyphen_splits,
    find_missing_profile_urls,
    find_orphan_list_markers,
    find_placeholders,
    is_disallowed_char,
    parse_page_count,
    run_check_suite,
    run_tool,
    suite_exit_code,
    verify_pdf,
)


class ParsePageCountTests(unittest.TestCase):
    def test_parses_pdfinfo_page_count(self):
        self.assertEqual(parse_page_count("Title: Example\nPages:          2\n"), 2)

    def test_rejects_output_without_page_count(self):
        with self.assertRaisesRegex(VerificationError, "did not contain a page count"):
            parse_page_count("Title: Example\n")


class CharacterPolicyTests(unittest.TestCase):
    """Pins the allowlist. A pure-ASCII rule fails correct German output.

    If someone tightens this back to ASCII, these tests fail loudly rather
    than the CV silently failing verification once real content lands.
    """

    def test_german_umlauts_and_sz_are_allowed(self):
        for char in "äöüÄÖÜßéèà":
            with self.subTest(char=char):
                self.assertFalse(is_disallowed_char(char))

    def test_german_quotes_and_dashes_are_allowed(self):
        for char in "„“–—‐":
            with self.subTest(char=char):
                self.assertFalse(is_disallowed_char(char))

    def test_currency_and_legal_symbols_are_allowed(self):
        # A Controlling CV quotes budgets in euros and cites German law by
        # section sign. Both are real content, not extraction defects.
        for char in "€§":
            with self.subTest(char=char):
                self.assertFalse(is_disallowed_char(char))

    def test_budget_line_passes(self):
        text = "Verantwortung für ein Budget von 2 Mio. € nach § 8b KStG."
        self.assertEqual(find_disallowed_symbols(text), [])

    def test_replacement_character_is_disallowed(self):
        # What moderncv's 0xB7 separator becomes after a failed UTF-8 decode.
        self.assertTrue(is_disallowed_char("�"))

    def test_list_marker_glyphs_are_disallowed(self):
        for char in "○\U0001f7e4\U0001f582":
            with self.subTest(char=char):
                self.assertTrue(is_disallowed_char(char))

    def test_real_german_sentence_passes(self):
        text = (
            "Universität Hamburg, Betriebswirtschaftslehre. "
            "Verantwortlich für die Soll-Ist-Abweichungsanalyse. "
            "Beispiel: „Informatikstudent im vierten Semester.“"
        )
        self.assertEqual(find_disallowed_symbols(text), [])

    def test_emoji_fails(self):
        self.assertEqual(find_disallowed_symbols("Kompetenzen \U0001f7e4 Python"), ["\U0001f7e4"])

    def test_fontawesome_glyph_name_fails(self):
        text = "MOBILE-ANDROID-ALT +49 1573 4631391"
        self.assertEqual(find_glyph_name_leaks(text), ["MOBILE-ANDROID-ALT"])

    def test_german_prose_has_no_glyph_name_leak(self):
        self.assertEqual(find_glyph_name_leaks("Universität Hamburg, für Controlling"), [])


class HyphenationCheckTests(unittest.TestCase):
    def test_detects_split_compound(self):
        layout = "Verantwortlich fuer die Kosten-\n    stellenrechnung im Team."
        self.assertEqual(find_hyphen_splits(layout), ["Kosten-|stellenrechnung"])

    def test_clean_text_has_no_splits(self):
        self.assertEqual(find_hyphen_splits("Kostenstellenrechnung im Team."), [])

    def test_detects_fused_term(self):
        layout = "Die Soll-\nIst-Abweichung wurde geprueft."
        raw = "Die SollIst-Abweichung wurde geprueft."
        self.assertEqual(find_fused_terms(raw, layout), ["SollIst"])

    def test_no_fusion_when_raw_keeps_the_hyphen(self):
        layout = "Die Soll-\nIst-Abweichung wurde geprueft."
        raw = "Die Soll-Ist-Abweichung wurde geprueft."
        self.assertEqual(find_fused_terms(raw, layout), [])


class OrphanMarkerTests(unittest.TestCase):
    def test_detects_marker_on_its_own_line(self):
        raw = "Berufserfahrung\n○\n[Unternehmen]\n[Position]\n"
        self.assertEqual(find_orphan_list_markers(raw), ["○"])

    def test_ignores_blank_lines_and_content(self):
        raw = "Berufserfahrung\n\n- Aufgabe oder Erfolg 1\n"
        self.assertEqual(find_orphan_list_markers(raw), [])


class ProfileUrlTests(unittest.TestCase):
    def test_flags_anchor_text_without_url(self):
        self.assertEqual(
            find_missing_profile_urls("LinkedIn, GitHub"),
            [
                "LinkedIn named but no URL in the text layer",
                "GitHub named but no URL in the text layer",
            ],
        )

    def test_accepts_visible_urls(self):
        raw = "linkedin.com/in/jane-doe | github.com/janedoe"
        self.assertEqual(find_missing_profile_urls(raw), [])

    def test_silent_when_profile_not_mentioned(self):
        self.assertEqual(find_missing_profile_urls("Kernkompetenzen: Python, SQL"), [])


class PlaceholderTests(unittest.TestCase):
    def test_detects_unreplaced_placeholder(self):
        self.assertEqual(find_placeholders("[Unternehmen], [Position]"), ["[Unternehmen]", "[Position]"])

    def test_real_content_has_none(self):
        self.assertEqual(find_placeholders("ACME GmbH, Werkstudent Controlling"), [])


CLEAN_RAW = (
    "Jane Doe\n"
    "Musterstraße 1, 20095 Hamburg | +49 1573 4631391 | jane.doe@example.com\n"
    "linkedin.com/in/jane-doe | github.com/janedoe\n"
    "Berufserfahrung\n"
    "ACME GmbH, Werkstudentin Controlling\n"
    "03/2024-heute | Hamburg\n"
    "- Verantwortlich für die Soll-Ist-Abweichungsanalyse.\n"
)


class RunCheckSuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf = Path(self.temp_dir.name) / "example.pdf"
        self.pdf.touch()

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("tools.verify_pdf.run_tool")
    def test_clean_german_document_passes_everything(self, mock_run_tool):
        mock_run_tool.side_effect = ["Pages:          1\n", CLEAN_RAW, CLEAN_RAW]

        results = run_check_suite(self.pdf, expected_pages=1)

        self.assertTrue(all(r.status == PASS for r in results), format_failures(results))
        self.assertEqual(suite_exit_code(results), 0)

    @patch("tools.verify_pdf.run_tool")
    def test_placeholders_ignored_unless_requested(self, mock_run_tool):
        raw = CLEAN_RAW + "[Aufgabe oder Erfolg 2]\n"
        mock_run_tool.side_effect = [raw, raw]

        results = run_check_suite(self.pdf)

        self.assertNotIn("no placeholders", [r.name for r in results])
        self.assertEqual(suite_exit_code(results), 0)

    @patch("tools.verify_pdf.run_tool")
    def test_placeholders_fail_when_requested(self, mock_run_tool):
        raw = CLEAN_RAW + "[Aufgabe oder Erfolg 2]\n"
        mock_run_tool.side_effect = [raw, raw]

        results = run_check_suite(self.pdf, check_placeholders=True)

        placeholder = next(r for r in results if r.name == "no placeholders")
        self.assertEqual(placeholder.status, FAIL)
        self.assertEqual(suite_exit_code(results), 1)

    @patch("tools.verify_pdf.run_tool")
    def test_reports_wrong_page_count(self, mock_run_tool):
        mock_run_tool.side_effect = ["Pages:          2\n", CLEAN_RAW, CLEAN_RAW]

        results = run_check_suite(self.pdf, expected_pages=1)

        page_check = results[0]
        self.assertEqual(page_check.status, FAIL)
        self.assertIn("2 pages", page_check.details)

    @patch("tools.verify_pdf.run_tool")
    def test_detects_glyph_leak_and_marker(self, mock_run_tool):
        raw = "MOBILE-ANDROID-ALT +49 1573 4631391 jane.doe@example.com\n○\n"
        mock_run_tool.side_effect = [raw, raw]

        results = run_check_suite(self.pdf)
        by_name = {r.name: r for r in results}

        self.assertEqual(by_name["no glyph-name leak"].status, FAIL)
        self.assertEqual(by_name["no orphan list markers"].status, FAIL)
        self.assertEqual(by_name["no disallowed symbols"].status, FAIL)

    def test_rejects_missing_pdf(self):
        with self.assertRaisesRegex(VerificationError, "PDF does not exist"):
            run_check_suite(Path(self.temp_dir.name) / "missing.pdf")


class GracefulDegradationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf = Path(self.temp_dir.name) / "example.pdf"
        self.pdf.touch()

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("tools.verify_pdf.run_tool", side_effect=ToolUnavailable("pdftotext was not found"))
    def test_missing_poppler_skips_never_passes(self, _mock):
        results = run_check_suite(self.pdf)

        self.assertTrue(results)
        self.assertTrue(all(r.status == SKIP for r in results))
        self.assertFalse(any(r.status == PASS for r in results))

    @patch("tools.verify_pdf.run_tool", side_effect=ToolUnavailable("pdftotext was not found"))
    def test_skip_is_not_a_failure_by_default(self, _mock):
        results = run_check_suite(self.pdf)
        self.assertEqual(suite_exit_code(results, strict=False), 0)

    @patch("tools.verify_pdf.run_tool", side_effect=ToolUnavailable("pdftotext was not found"))
    def test_strict_mode_turns_skip_into_failure(self, _mock):
        results = run_check_suite(self.pdf)
        self.assertEqual(suite_exit_code(results, strict=True), 1)

    @patch("tools.verify_pdf.run_tool", side_effect=ToolUnavailable("pdfinfo was not found"))
    def test_page_count_skips_when_pdfinfo_missing(self, _mock):
        results = run_check_suite(self.pdf, expected_pages=1)
        self.assertEqual(results[0].status, SKIP)
        self.assertIn("pdfinfo", results[0].reason)

    @patch("tools.verify_pdf.run_tool", side_effect=VerificationError("pdftotext could not read the PDF"))
    def test_unreadable_pdf_fails_rather_than_skips(self, _mock):
        results = run_check_suite(self.pdf)
        self.assertTrue(all(r.status == FAIL for r in results))


class LegacyVerifyPdfTests(unittest.TestCase):
    """The exception-raising helper other callers still use."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pdf = Path(self.temp_dir.name) / "example.pdf"
        self.pdf.touch()

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("tools.verify_pdf.run_tool")
    def test_accepts_expected_pages_and_text(self, mock_run_tool):
        mock_run_tool.side_effect = [
            "Pages:          2\n",
            "Professional\nExperience   [your.email@example.com]\n",
        ]

        verify_pdf(
            self.pdf,
            expected_pages=2,
            min_chars=20,
            required_text=("Professional Experience", "[your.email@example.com]"),
        )

    @patch("tools.verify_pdf.run_tool")
    def test_rejects_wrong_page_count(self, mock_run_tool):
        mock_run_tool.return_value = "Pages:          3\n"

        with self.assertRaisesRegex(VerificationError, "expected 2 page.*found 3"):
            verify_pdf(self.pdf, expected_pages=2)

    @patch("tools.verify_pdf.run_tool")
    def test_rejects_too_little_extractable_text(self, mock_run_tool):
        mock_run_tool.return_value = "short"

        with self.assertRaisesRegex(VerificationError, "expected at least 20"):
            verify_pdf(self.pdf, min_chars=20)

    @patch("tools.verify_pdf.run_tool")
    def test_rejects_missing_required_text(self, mock_run_tool):
        mock_run_tool.return_value = "Readable text, but not the expected section."

        with self.assertRaisesRegex(VerificationError, "Professional Experience"):
            verify_pdf(self.pdf, required_text=("Professional Experience",))

    def test_rejects_missing_pdf(self):
        with self.assertRaisesRegex(VerificationError, "PDF does not exist"):
            verify_pdf(Path(self.temp_dir.name) / "missing.pdf")


class RunToolTests(unittest.TestCase):
    @patch("tools.verify_pdf.subprocess.run", side_effect=FileNotFoundError)
    def test_reports_missing_poppler_command(self, _mock_run):
        with self.assertRaisesRegex(VerificationError, "install poppler-utils"):
            run_tool(["pdftotext", "example.pdf", "-"])

    @patch("tools.verify_pdf.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_command_raises_tool_unavailable(self, _mock_run):
        with self.assertRaises(ToolUnavailable):
            run_tool(["pdftotext", "example.pdf", "-"])

    @patch("tools.verify_pdf.subprocess.run")
    def test_decodes_as_utf8_not_the_locale_codepage(self, mock_run):
        # Regression: with a bare text=True, Windows decodes pdftotext's UTF-8
        # with cp1252, so "„" (E2 80 9E) arrives as "â€ž" and the stray U+20AC
        # fails "no disallowed symbols" for every German CV - on Windows only.
        # Verify the symptom is real, then pin the fix.
        self.assertIn("€", "„".encode("utf-8").decode("cp1252"))

        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        run_tool(["pdftotext", "example.pdf", "-"])

        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs.get("encoding"), "utf-8")
        self.assertEqual(kwargs.get("errors"), "replace")

    @patch("tools.verify_pdf.subprocess.run")
    def test_reports_unreadable_pdf(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["pdfinfo", "example.pdf"], stderr="invalid PDF"
        )

        with self.assertRaisesRegex(VerificationError, "invalid PDF"):
            run_tool(["pdfinfo", "example.pdf"])

    @patch("tools.verify_pdf.subprocess.run")
    def test_unreadable_pdf_is_not_tool_unavailable(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["pdfinfo", "example.pdf"], stderr="invalid PDF"
        )

        with self.assertRaises(VerificationError) as ctx:
            run_tool(["pdfinfo", "example.pdf"])
        self.assertNotIsInstance(ctx.exception, ToolUnavailable)


def format_failures(results):
    return "\n".join(
        "{}: {} {}".format(r.name, r.status, r.details) for r in results if r.status != PASS
    )


if __name__ == "__main__":
    unittest.main()
