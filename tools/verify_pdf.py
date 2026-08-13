#!/usr/bin/env python3
"""Verify a generated PDF: page count, and the text-layer defects an ATS sees.

Most of these faults survive visual inspection - the PDF looks correct on screen
and extracts as something a parser cannot use. Run this after every compile.

Two groups of checks:

* **Always on** - glyph-name leaks, disallowed symbols, hyphenation splits,
  fused terms, orphan list markers, profile-URL visibility, email, phone, and
  (when ``--pages`` is given) page count.
* **Tailored documents only**, behind ``--check-placeholders`` - unreplaced
  ``[Placeholder]`` text. Templates are *supposed* to be full of placeholders,
  so this would fail every template if it ran by default.

``pdftotext`` and ``pdfinfo`` come from poppler, which is **not** part of MiKTeX
or TeX Live. When they are missing the checks that need them report ``SKIP``
with the reason - never a pass, never a crash. ``--strict`` turns a SKIP into a
failure for CI, and is off by default.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


class VerificationError(Exception):
    """Raised when a generated PDF does not satisfy its checks."""


class ToolUnavailable(VerificationError):
    """Raised when a poppler binary is not installed.

    Subclasses VerificationError so existing callers that only know about
    VerificationError keep working; the suite catches it separately to
    downgrade the affected checks to SKIP rather than failing them.
    """


# --------------------------------------------------------------------------
# Character policy
# --------------------------------------------------------------------------
# The old rule demanded a pure-ASCII text layer. That was wrong the moment real
# content replaced the placeholders: "Universitaet" is a placeholder, but
# "Universität" is the correct output, and so are "für", "Straße" and the German
# quotation marks the template emits via \glqq/\grqq.
#
# Flag anything above U+024F, then allow back the ranges a correct German CV
# legitimately contains. That still catches every defect this was written for:
# the U+FFFD fallback from moderncv's 0xB7 separator, FontAwesome glyph
# fallbacks, the circle list marker (U+25CB / U+1F7E4), and U+1F582.

DISALLOWED_THRESHOLD = 0x24F

ALLOWED_RANGES = (
    # Latin-1 letters: umlauts, accented vowels, sz. Below the threshold
    # already - listed explicitly so the policy is readable on its own.
    (0x00C0, 0x00FF),
    # Hyphens, dashes and quotation marks, including U+201E and U+201C.
    (0x2010, 0x2027),
)

# Individual characters above the threshold that legitimate content contains.
#   „ “  the German quotes produced by \glqq and \grqq
#   €    a Controlling or finance CV quotes budgets and savings in euros
#        ("Verantwortung fuer ein Budget von 2 Mio. €")
# § is legitimate too (German legal references) but sits at U+00A7, already
# below the threshold, so it needs no entry here.
ALLOWED_CHARS = frozenset("„“€")

# Characters that may legitimately stand alone on a line as a list marker is
# NOT a thing - a line holding only a marker means the marker was orphaned
# from its content.
_MARKER_ONLY = re.compile(r"^[\s\-*·–—•○◦▪]+$")

_GLYPH_NAME = re.compile(r"\b[A-Z]{3,}(?:-[A-Z]{3,})+\b")
_HYPHEN_SPLIT = re.compile(r"(\w+)-\n\s*(\w+)")
_LOWER_UPPER = re.compile(r"[a-zäöüß][A-ZÄÖÜ]")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.\w+")
_PHONE = re.compile(r"(?:\+\d[\d\s/()-]{7,}|\b0\d[\d\s/()-]{7,})")
_PLACEHOLDER = re.compile(r"\[[A-Za-z][^\]\n]{2,40}\]")


def is_disallowed_char(char: str) -> bool:
    """True if `char` has no business in a generated CV's text layer."""
    codepoint = ord(char)
    if codepoint <= DISALLOWED_THRESHOLD:
        return False
    if char in ALLOWED_CHARS:
        return False
    for low, high in ALLOWED_RANGES:
        if low <= codepoint <= high:
            return False
    return True


# --------------------------------------------------------------------------
# Individual checks - pure functions over extracted text
# --------------------------------------------------------------------------


def find_glyph_name_leaks(raw_text):
    """FontAwesome icons with no Unicode mapping extract as their glyph name."""
    return _GLYPH_NAME.findall(raw_text)


def find_disallowed_symbols(raw_text):
    """Characters outside the allowed policy, deduplicated and sorted."""
    return sorted({c for c in raw_text if is_disallowed_char(c)})


def find_hyphen_splits(layout_text):
    """Words broken across a line by hyphenation - the keyword becomes unfindable."""
    return ["{}-|{}".format(head, tail) for head, tail in _HYPHEN_SPLIT.findall(layout_text)]


def find_fused_terms(raw_text, layout_text):
    """Worst case: a real hyphen is swallowed and two words fuse.

    "Soll-Ist-Abweichungsanalyse" broken across a line can heal in raw mode as
    "SollIst...", which matches nothing.
    """
    fused = []
    for head, tail in _HYPHEN_SPLIT.findall(layout_text):
        candidate = head + tail
        if candidate in raw_text and _LOWER_UPPER.search(candidate):
            fused.append(candidate)
    return fused


def find_orphan_list_markers(raw_text):
    """Lines holding a bullet marker and nothing else.

    Produced by wrapping a \\cventry in an itemize: the marker lands on its own
    line and separates the section heading from the employer name.
    """
    orphans = []
    for line in raw_text.splitlines():
        if not line.strip():
            continue
        if _MARKER_ONLY.match(line):
            orphans.append(line)
    return orphans


def find_missing_profile_urls(raw_text):
    """A profile named in the CV must carry a readable URL.

    \\href{...}{LinkedIn} stores the address in a PDF annotation most parsers
    never read. Only checked for profiles the CV actually mentions.
    """
    missing = []
    for label, pattern in (("LinkedIn", r"linkedin\.com/\S+"), ("GitHub", r"github\.com/\S+")):
        mentioned = re.search(label, raw_text, re.IGNORECASE)
        if mentioned and not re.search(pattern, raw_text, re.IGNORECASE):
            missing.append("{} named but no URL in the text layer".format(label))
    return missing


def find_placeholders(raw_text):
    """Unreplaced [Placeholder] text. Tailored documents only."""
    return _PLACEHOLDER.findall(raw_text)


def parse_page_count(pdfinfo_output):
    match = re.search(r"^Pages:\s+(\d+)\s*$", pdfinfo_output, re.MULTILINE)
    if not match:
        raise VerificationError("pdfinfo output did not contain a page count")
    return int(match.group(1))


# --------------------------------------------------------------------------
# Result model
# --------------------------------------------------------------------------

PASS = "ok"
FAIL = "FAIL"
SKIP = "SKIP"


class CheckResult:
    def __init__(self, name, status, details=(), reason=None):
        self.name = name
        self.status = status
        self.details = list(details)
        self.reason = reason

    def __repr__(self):  # pragma: no cover - debugging aid
        return "CheckResult({!r}, {!r})".format(self.name, self.status)


def _result(name, offenders):
    return CheckResult(name, FAIL if offenders else PASS, offenders)


def format_results(results, max_details=8):
    """Render results in the order they were run."""
    lines = []
    for result in results:
        if result.status == SKIP:
            lines.append("SKIP  {} ({})".format(result.name, result.reason))
            continue
        lines.append("{:<5} {}".format(result.status, result.name))
        for detail in result.details[:max_details]:
            lines.append("        {!r}".format(detail))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------


def run_tool(command):
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            # pdftotext emits UTF-8. Without an explicit encoding, text=True
            # decodes with locale.getpreferredencoding(), which on Windows is
            # the ANSI codepage (cp1252) - and cp1252 turns the UTF-8 bytes of
            # "„" (E2 80 9E) into "â€ž", injecting a spurious U+20AC. Every
            # German CV would then fail "no disallowed symbols" on Windows and
            # pass on Linux, for a defect that exists in neither PDF.
            #
            # errors="replace" is deliberate, not defensive: genuinely invalid
            # UTF-8 (moderncv's bare 0xB7 separator) becomes U+FFFD, which the
            # character policy flags. Real defects still surface; the decoder
            # just stops inventing new ones.
            encoding="utf-8",
            errors="replace",
        ).stdout
    except FileNotFoundError as exc:
        raise ToolUnavailable(
            f"required command '{command[0]}' was not found. "
            "Install poppler-utils (macOS: brew install poppler, "
            "Debian/Ubuntu: apt install poppler-utils, Windows: choco install poppler)"
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or (exc.stdout or "").strip()
        detail = detail or "command failed"
        raise VerificationError(f"{command[0]} could not read the PDF: {detail}") from exc


def extract_text(pdf_path, layout=False):
    command = ["pdftotext"]
    if layout:
        command.append("-layout")
    command += [str(pdf_path), "-"]
    return run_tool(command)


def normalize_text(text):
    return " ".join(text.split())


# --------------------------------------------------------------------------
# Legacy helper - kept so existing callers and tests keep working
# --------------------------------------------------------------------------


def verify_pdf(pdf_path, expected_pages=None, min_chars=1, required_text=()):
    """Strict, exception-raising subset. Prefer run_check_suite for new code."""
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise VerificationError(f"PDF does not exist: {pdf_path}")

    if expected_pages is not None:
        actual_pages = parse_page_count(run_tool(["pdfinfo", str(pdf_path)]))
        if actual_pages != expected_pages:
            raise VerificationError(
                f"expected {expected_pages} page(s), found {actual_pages}"
            )

    extracted_text = normalize_text(run_tool(["pdftotext", "-layout", str(pdf_path), "-"]))
    if len(extracted_text) < min_chars:
        raise VerificationError(
            f"text layer has {len(extracted_text)} character(s); expected at least {min_chars}"
        )

    for required in required_text:
        if normalize_text(required) not in extracted_text:
            raise VerificationError(f"text layer is missing required text: {required!r}")


# --------------------------------------------------------------------------
# Check suite
# --------------------------------------------------------------------------

EXTRACTION_CHECKS = (
    "no glyph-name leak",
    "no disallowed symbols",
    "no hyphen splits",
    "no fused terms",
    "no orphan list markers",
    "profile urls visible",
    "email in text",
    "phone in text",
)


def run_check_suite(
    pdf_path,
    expected_pages=None,
    min_chars=None,
    required_text=(),
    check_placeholders=False,
):
    """Run every check and return a list of CheckResult. Never raises for a
    check failure - inspect the results. Raises only if the PDF is absent."""
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise VerificationError(f"PDF does not exist: {pdf_path}")

    results = []

    if expected_pages is not None:
        name = "page count == {}".format(expected_pages)
        try:
            actual = parse_page_count(run_tool(["pdfinfo", str(pdf_path)]))
        except ToolUnavailable as exc:
            results.append(CheckResult(name, SKIP, reason=str(exc)))
        except VerificationError as exc:
            results.append(CheckResult(name, FAIL, [str(exc)]))
        else:
            results.append(
                CheckResult(
                    name,
                    PASS if actual == expected_pages else FAIL,
                    [] if actual == expected_pages else ["{} pages".format(actual)],
                )
            )

    checks_needing_text = list(EXTRACTION_CHECKS)
    if min_chars is not None:
        checks_needing_text.append("minimum text length")
    if required_text:
        checks_needing_text.append("required text present")
    if check_placeholders:
        checks_needing_text.append("no placeholders")

    try:
        raw = extract_text(pdf_path, layout=False)
        layout = extract_text(pdf_path, layout=True)
    except ToolUnavailable as exc:
        results.extend(CheckResult(name, SKIP, reason=str(exc)) for name in checks_needing_text)
        return results
    except VerificationError as exc:
        results.extend(CheckResult(name, FAIL, [str(exc)]) for name in checks_needing_text)
        return results

    results.append(_result("no glyph-name leak", find_glyph_name_leaks(raw)))
    results.append(_result("no disallowed symbols", find_disallowed_symbols(raw)))
    results.append(_result("no hyphen splits", find_hyphen_splits(layout)))
    results.append(_result("no fused terms", find_fused_terms(raw, layout)))
    results.append(_result("no orphan list markers", find_orphan_list_markers(raw)))
    results.append(_result("profile urls visible", find_missing_profile_urls(raw)))
    results.append(
        _result("email in text", [] if _EMAIL.search(raw) else ["no email address found"])
    )
    results.append(
        _result("phone in text", [] if _PHONE.search(raw) else ["no phone number found"])
    )

    if min_chars is not None:
        normalized = normalize_text(layout)
        results.append(
            _result(
                "minimum text length",
                []
                if len(normalized) >= min_chars
                else ["{} characters, expected {}".format(len(normalized), min_chars)],
            )
        )

    if required_text:
        normalized = normalize_text(layout)
        missing = [t for t in required_text if normalize_text(t) not in normalized]
        results.append(_result("required text present", missing))

    if check_placeholders:
        results.append(_result("no placeholders", find_placeholders(raw)))

    return results


def suite_exit_code(results, strict=False):
    if any(r.status == FAIL for r in results):
        return 1
    if strict and any(r.status == SKIP for r in results):
        return 1
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        description="Verify a PDF's page count and ATS-readable text layer."
    )
    parser.add_argument("pdf", type=Path, help="PDF file to verify")
    parser.add_argument("--pages", type=int, help="required exact page count")
    parser.add_argument(
        "--min-chars",
        type=int,
        help="minimum non-whitespace text-layer characters",
    )
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        help="text that must appear after whitespace normalization; repeatable",
    )
    parser.add_argument(
        "--check-placeholders",
        action="store_true",
        help="fail on unreplaced [Placeholder] text; for tailored documents, not templates",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat SKIP (poppler missing) as a failure",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        results = run_check_suite(
            args.pdf,
            expected_pages=args.pages,
            min_chars=args.min_chars,
            required_text=args.contains,
            check_placeholders=args.check_placeholders,
        )
    except VerificationError as exc:
        print(f"Error: {args.pdf}: {exc}", file=sys.stderr)
        return 1

    print(format_results(results))

    exit_code = suite_exit_code(results, strict=args.strict)
    failed = sum(1 for r in results if r.status == FAIL)
    skipped = sum(1 for r in results if r.status == SKIP)
    summary = "\n{} check(s) failed, {} skipped".format(failed, skipped)
    if skipped and not args.strict:
        summary += " (skipped checks are not passes; use --strict to fail on them)"
    print(summary)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
