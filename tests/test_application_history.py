"""Tests for append-only application history and its workflow contract."""

from __future__ import annotations

import csv
import re
import tempfile
import unittest
from pathlib import Path

from tools.application_history import (
    EVENT_HEADER,
    HistoryError,
    initialize_config,
    load_events,
    record_event,
    set_experiment,
)


REPO = Path(__file__).resolve().parent.parent
COMMANDS = REPO / ".claude" / "commands"
HISTORY_GUIDE = (
    REPO
    / ".claude"
    / "skills"
    / "job-application-assistant"
    / "10-application-history.md"
)


class ApplicationHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.config = self.root / ".job-search-profile.json"
        self.events = self.root / "application_events.csv"
        initialize_config(self.config, "candidate-a")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def record(self, **overrides):
        values = {
            "repo": REPO,
            "config_path": self.config,
            "events_path": self.events,
            "event": "drafted",
            "company": "Example GmbH",
            "role": "Data Analyst",
            "timestamp": "2026-08-17",
            "status": "drafted",
            "channel": "online",
            "fit_score": "78",
            "workflow_commit": "abc123",
            "metadata": {"source": "test"},
        }
        values.update(overrides)
        return record_event(**values)

    def test_new_attempt_writes_exact_schema_and_provenance(self):
        row, created = self.record(new_application=True)

        self.assertTrue(created)
        self.assertTrue(row["application_id"].startswith("app_"))
        self.assertTrue(row["event_id"].startswith("evt_"))
        self.assertEqual(row["profile_id"], "candidate-a")
        self.assertEqual(row["experiment_id"], "baseline")
        self.assertEqual(row["workflow_commit"], "abc123")
        with self.events.open("r", encoding="utf-8", newline="") as handle:
            self.assertEqual(tuple(csv.DictReader(handle).fieldnames or ()), EVENT_HEADER)

    def test_later_event_reuses_latest_application_id(self):
        first, _ = self.record(new_application=True)
        second, _ = self.record(
            event="applied",
            timestamp="2026-08-18",
            status="applied",
            new_application=False,
        )

        self.assertEqual(second["application_id"], first["application_id"])
        self.assertEqual(len(load_events(self.events)), 2)

    def test_reapplication_gets_a_new_application_id(self):
        first, _ = self.record(new_application=True)
        second, _ = self.record(
            timestamp="2026-09-01",
            new_application=True,
        )

        self.assertNotEqual(second["application_id"], first["application_id"])

    def test_exact_rerun_is_idempotent_even_if_commit_changes(self):
        first, created = self.record(new_application=True)
        duplicate, duplicate_created = self.record(
            application_id=first["application_id"],
            workflow_commit="different-commit",
        )

        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(duplicate["event_id"], first["event_id"])
        self.assertEqual(len(load_events(self.events)), 1)

    def test_experiment_changes_only_future_events(self):
        baseline, _ = self.record(new_application=True)
        set_experiment(self.config, "workflow-v2")
        optimized, _ = self.record(
            timestamp="2026-09-01",
            new_application=True,
        )

        self.assertEqual(baseline["experiment_id"], "baseline")
        self.assertEqual(optimized["experiment_id"], "workflow-v2")

    def test_workflow_commit_marks_dirty_state_without_losing_head(self):
        row, _ = self.record(new_application=True, workflow_commit=None)
        self.assertRegex(
            row["workflow_commit"],
            re.compile(r"^[0-9a-f]{40}(?:\+(?:dirty|status-unknown))?$"),
        )

    def test_invalid_fit_score_does_not_write(self):
        with self.assertRaises(HistoryError):
            self.record(new_application=True, fit_score="101")
        self.assertFalse(self.events.exists())

    def test_incompatible_existing_header_is_never_overwritten(self):
        self.events.write_text("wrong,header\nvalue,value\n", encoding="utf-8")
        with self.assertRaises(HistoryError):
            self.record(new_application=True)
        self.assertEqual(
            self.events.read_text(encoding="utf-8"),
            "wrong,header\nvalue,value\n",
        )


class ApplicationHistoryWorkflowTests(unittest.TestCase):
    def test_private_state_is_gitignored_and_guarded(self):
        rules = (REPO / ".gitignore").read_text(encoding="utf-8")
        guards = (REPO / "tools" / "security_guards.py").read_text(encoding="utf-8")
        for name in (".job-search-profile.json", "application_events.csv"):
            with self.subTest(name=name):
                self.assertIn(name, rules)
                self.assertIn(f'"{name}"', guards)

    def test_canonical_guide_is_referenced_by_every_writer_and_report(self):
        paths = [
            COMMANDS / "setup.md",
            COMMANDS / "apply.md",
            COMMANDS / "outcome.md",
            COMMANDS / "gmail-sync.md",
            COMMANDS / "html-report.md",
        ]
        for path in paths:
            with self.subTest(path=path.name):
                self.assertIn(
                    "10-application-history.md",
                    path.read_text(encoding="utf-8"),
                )

    def test_guide_requires_version_and_experiment_provenance(self):
        guide = HISTORY_GUIDE.read_text(encoding="utf-8")
        for fragment in (
            "workflow_commit",
            "experiment_id",
            "unique `application_id`",
            "explicit timestamps",
            "Separate profiles",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, guide)

    def test_tracker_header_remains_backward_compatible(self):
        legacy_header = (
            "date,company,sector,role,role_type,channel,status,contact_person,"
            "fit_rating,notes,cv_file,cover_letter_file,source"
        )
        self.assertIn(legacy_header, (COMMANDS / "apply.md").read_text(encoding="utf-8"))
        self.assertIn(legacy_header, (COMMANDS / "outcome.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
