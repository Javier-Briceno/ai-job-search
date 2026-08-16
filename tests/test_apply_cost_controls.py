import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
APPLY = REPO / ".claude" / "commands" / "apply.md"
REVIEWER = REPO / ".claude" / "agents" / "application-reviewer.md"
CV_GUIDE = REPO / ".claude" / "skills" / "job-application-assistant" / "05-cv-templates.md"
COVER_GUIDE = REPO / ".claude" / "skills" / "job-application-assistant" / "06-cover-letter-templates.md"
WEB_GUIDE = REPO / ".claude" / "skills" / "job-application-assistant" / "09-web-research.md"
COVER_TEMPLATE = REPO / "cover_letters" / "cover_example.tex"


class ApplyCostControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.apply = APPLY.read_text(encoding="utf-8")
        cls.reviewer = REVIEWER.read_text(encoding="utf-8")
        cls.cv_guide = CV_GUIDE.read_text(encoding="utf-8")
        cls.cover_guide = COVER_GUIDE.read_text(encoding="utf-8")
        cls.web_guide = WEB_GUIDE.read_text(encoding="utf-8")
        cls.cover_template = COVER_TEMPLATE.read_text(encoding="utf-8")
        cls.apply_flat = " ".join(cls.apply.split())
        cls.cv_guide_flat = " ".join(cls.cv_guide.split())

    def test_command_preserves_drafting_effort_and_manual_invocation(self):
        frontmatter = self.apply.split("---", 2)[1]
        self.assertIn("disable-model-invocation: true", frontmatter)
        self.assertIn("model: sonnet", frontmatter)
        self.assertIn("effort: high", frontmatter)

    def test_previous_tailored_documents_are_forbidden_as_references(self):
        self.assertIn("Never use a previous tailored CV or cover letter", self.apply)
        self.assertIn("cv/main_example.tex", self.apply)
        self.assertIn("cover_letters/cover_example.tex", self.apply)

    def test_fetch_research_and_verification_are_cached_or_one_shot(self):
        self.assertIn("Fetch the posting once, research the company once", self.apply)
        self.assertIn("## Verbatim posting", self.apply)
        self.assertIn("checked within 30 days", self.apply)
        self.assertIn("tools/finalize_application.py check", self.apply)
        self.assertIn("tools/finalize_application.py export", self.apply)

    def test_verbatim_cache_cannot_be_a_summary_with_a_heading(self):
        for rule in (
            "The heading alone does not make a cache valid",
            "translation, paraphrase, structured field summary",
            "without translating, summarizing, normalizing its bullets",
        ):
            self.assertIn(rule, self.apply)

    def test_layout_retries_are_bounded_and_balance_is_advisory(self):
        for rule in (
            "at most three times",
            "initial build plus at most two coherent correction batches",
            "page-balance `WARN` is visual evidence",
            "page-balance `WARN` alone is not a reason to revise",
        ):
            self.assertIn(rule, self.apply)
        self.assertIn("is the sole compile/check command", self.cv_guide)
        self.assertIn("This is never an open-ended loop", self.cv_guide_flat)
        self.assertIn("--human-override", self.apply)
        self.assertIn("attempts.json", self.apply)
        self.assertIn("rejects a fifth", self.apply)
        self.assertIn("sole compilation", self.cover_guide)
        self.assertIn("there is no fifth check", self.cover_guide)

    def test_arbeitsagentur_uses_one_native_detail_request(self):
        command = (
            "bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts "
            "detail <refnr> --format json"
        )
        self.assertIn(command, self.apply)
        self.assertIn(command, self.web_guide)
        self.assertIn("use the returned `description` unchanged", self.apply)
        self.assertIn("Do not call WebFetch, curl", self.apply)
        self.assertIn("reverse-engineer its JavaScript", self.web_guide)

    def test_web_fallback_uses_an_explicit_temporary_directory(self):
        self.assertIn('scratchpad_path="$(mktemp -d)"', self.web_guide)
        self.assertIn("Copy the exact printed path", self.web_guide)
        self.assertIn("never default an\nunset `$SCRATCHPAD`", self.web_guide)

    def test_cover_template_has_deterministic_closing_blocks(self):
        self.assertIn(r"\newcommand{\applicationclosing}", self.cover_template)
        self.assertIn(r"\newcommand{\applicationenclosures}", self.cover_template)
        self.assertIn(r"\noindent\enclname\\{}#1", self.cover_template)
        self.assertNotIn(r"\closing{Mit freundlichen", self.cover_template)
        self.assertNotIn(r"\encl{[Lebenslauf", self.cover_template)

    def test_company_packet_is_small_and_entity_specific(self):
        self.assertIn("must name the full legal entity", self.apply)
        self.assertIn("prune it locally to the three most useful without browsing", self.apply)
        self.assertIn("Save no more than three relevant facts", self.apply_flat)

    def test_reviewer_is_tool_free_and_turn_bounded(self):
        self.assertIn("name: application-reviewer", self.reviewer)
        self.assertIn("effort: medium", self.reviewer)
        self.assertIn("maxTurns: 2", self.reviewer)
        self.assertIn("tools: []", self.reviewer)
        self.assertIn("Use at most 12 edits", self.reviewer)

    def test_private_build_receipts_are_ignored(self):
        rules = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".application-build/", rules)


if __name__ == "__main__":
    unittest.main()
