import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
DAILY = REPO / ".claude" / "commands" / "daily.md"
RUNNER = REPO / "tools" / "run_daily.ps1"
INSTALLER = REPO / "tools" / "install_daily_task.ps1"


class DailyCommandSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = DAILY.read_text(encoding="utf-8")

    def test_command_delegates_to_canonical_specs(self):
        self.assertTrue(self.text.startswith("# /daily"))
        self.assertIn(".claude/skills/job-scraper/SKILL.md", self.text)
        self.assertIn(".claude/commands/rank.md", self.text)
        self.assertIn(".claude/commands/prepare.md", self.text)

    def test_daily_never_reranks_all_or_submits(self):
        self.assertIn("Do not use `--all`", self.text)
        self.assertIn("Never send an application", self.text)
        self.assertIn("five-job cap", self.text)

    def test_report_is_always_rebuilt(self):
        self.assertIn("Always run this deterministic command", self.text)
        self.assertIn("python tools/build_delivery_report.py", self.text)


class PowerShellRunnerSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = RUNNER.read_text(encoding="utf-8")
        cls.installer = INSTALLER.read_text(encoding="utf-8")

    def test_runner_has_cost_context_and_batch_bounds(self):
        self.assertIn("[ValidateRange(1, 5)]", self.runner)
        self.assertIn("--max-budget-usd", self.runner)
        self.assertIn("--max-turns", self.runner)
        self.assertIn("--no-session-persistence", self.runner)
        self.assertIn("--permission-mode', 'auto", self.runner)
        self.assertIn("ClaudePath", self.runner)
        self.assertIn("CLAUDE_CODE_CLI", self.runner)
        self.assertIn("Anthropic.ClaudeCode_", self.runner)
        self.assertIn("The VS Code extension alone", self.runner)

    def test_report_runs_even_after_claude_returns_failure(self):
        claude = self.runner.index("$claudeExit = $LASTEXITCODE")
        report = self.runner.index("tools/build_delivery_report.py")
        failure = self.runner.index("if ($claudeExit -ne 0)")
        self.assertLess(claude, report)
        self.assertLess(report, failure)

    def test_publish_is_copy_only_not_mirror_or_delete(self):
        self.assertIn("Copy-Item", self.runner)
        self.assertNotIn("Remove-Item", self.runner)
        self.assertNotIn("/MIR", self.runner.upper())
        self.assertIn("Refusing to publish directly into a drive root", self.runner)

    def test_installer_is_opt_in_and_non_admin(self):
        self.assertIn("SupportsShouldProcess", self.installer)
        self.assertIn("-LogonType Interactive", self.installer)
        self.assertIn("-RunLevel Limited", self.installer)
        self.assertIn("Register-ScheduledTask", self.installer)
        self.assertIn("ClaudePath", self.installer)
        self.assertIn("Anthropic.ClaudeCode_", self.installer)
        self.assertIn("claude --version", self.installer)
        self.assertIn("-ExecutionPolicy Bypass", self.installer)


if __name__ == "__main__":
    unittest.main()
