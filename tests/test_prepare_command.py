"""Regression guards for the bounded /prepare batch command."""

import subprocess
import sys
import unittest
from pathlib import Path

try:
    import yaml  # noqa: F401
    _HAVE_YAML = True
except ImportError:
    _HAVE_YAML = False

REPO = Path(__file__).resolve().parent.parent
PREPARE = REPO / ".claude" / "commands" / "prepare.md"
APPLY = REPO / ".claude" / "commands" / "apply.md"
GITIGNORE = REPO / ".gitignore"


class PrepareCommandSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PREPARE.read_text(encoding="utf-8")

    def test_command_exists_with_lint_header(self):
        self.assertTrue(PREPARE.is_file())
        self.assertTrue(self.text.startswith("# /prepare"))

    def test_batch_is_quota_bounded(self):
        self.assertIn("default 3", self.text)
        self.assertIn("1 to 5", self.text)
        self.assertIn("Hard cap: at most 5", self.text)
        self.assertIn("refuse", self.text.lower())

    def test_selection_requires_ranked_and_excludes_every_tracker_row(self):
        self.assertIn("`status` is exactly `ranked`", self.text)
        self.assertIn("including `drafted`", self.text)
        self.assertIn("company+role exclusion set", self.text)
        self.assertIn("neither `location` nor `language_gate` is `FAIL`", self.text)

    def test_workers_are_fresh_and_sequential(self):
        self.assertIn("sequentially, never in parallel", self.text)
        self.assertIn("exactly one fresh `general-purpose`", self.text)
        self.assertIn("Never pass other selected jobs", self.text)

    def test_batch_review_tradeoff_is_honest(self):
        self.assertIn("Do not spawn a nested reviewer agent", self.text)
        self.assertIn("`batch self-review`", self.text)
        self.assertIn("independent drafter-reviewer workflow remains available", self.text)

    def test_apply_remains_single_source_of_truth(self):
        self.assertIn("Read `.claude/commands/apply.md` and follow it end-to-end", self.text)
        self.assertIn("Follow `/apply` Step 6b exactly", self.text)
        self.assertIn("Do not modify `job_scraper/seen_jobs.json`", self.text)

    def test_parent_verifies_worker_claims(self):
        self.assertIn("verify read-only", self.text)
        self.assertIn("both delivery PDFs", self.text)
        self.assertIn("tracker contains the matching company+role row", self.text)
        self.assertIn("Never fabricate success", self.text)

    @unittest.skipUnless(_HAVE_YAML, "PyYAML not installed")
    def test_lint_skills_passes(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "lint_skills.py")],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class DeliveryPaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apply = APPLY.read_text(encoding="utf-8")

    def test_apply_exports_to_job_specific_dated_folder(self):
        expected = "deliveries/YYYY-MM-DD/<company>_<role>"
        self.assertIn(expected, self.apply)
        self.assertIn("Never export to shared root-level names", self.apply)

    def test_tracker_points_at_deliverables(self):
        step6 = self.apply.split("## Step 6: Present Final Output", 1)[1]
        self.assertIn("deliveries/YYYY-MM-DD/<company>_<role>/Vorname-Nachname-Lebenslauf.pdf", step6)
        self.assertIn("deliveries/YYYY-MM-DD/<company>_<role>/Vorname-Nachname-Anschreiben.pdf", step6)

    def test_private_deliveries_are_ignored(self):
        rules = {line.strip() for line in GITIGNORE.read_text(encoding="utf-8").splitlines()}
        self.assertIn("deliveries/", rules)


if __name__ == "__main__":
    unittest.main()
