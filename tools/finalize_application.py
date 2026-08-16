#!/usr/bin/env python3
"""Compile, verify, preview, and safely export one tailored application.

The command deliberately separates mechanical checking from visual approval:

    python tools/finalize_application.py check ...
    python tools/finalize_application.py export ... --visual-approved

``export`` only accepts the exact source/PDF hashes recorded by a successful
``check``. This prevents a draft from being copied to ``deliveries/`` after it
was edited without being compiled and reviewed again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    from tools.verify_pdf import (
        FAIL,
        SKIP,
        WARN,
        VerificationError,
        extract_text,
        run_check_suite,
    )
except ModuleNotFoundError:  # Direct execution puts tools/ on sys.path.
    from verify_pdf import (  # type: ignore
        FAIL,
        SKIP,
        WARN,
        VerificationError,
        extract_text,
        run_check_suite,
    )


RECEIPT_VERSION = 1
ATTEMPT_LEDGER_VERSION = 1
BUILD_DIR = ".application-build"
MAX_STANDARD_CHECK_ATTEMPTS = 3
MAX_HUMAN_OVERRIDE_ATTEMPTS = 1
LATEX_ARTIFACT_SUFFIXES = (
    ".aux",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".out",
    ".synctex.gz",
    ".xdv",
)
SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class FinalizationError(RuntimeError):
    """The application could not be finalized safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_to_repo(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_recorded_path(value: str, repo: Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (repo / path).resolve()


def validate_slug(slug: str) -> str:
    if not SAFE_SLUG.fullmatch(slug) or slug in {".", ".."}:
        raise FinalizationError(
            "slug must contain only letters, numbers, dots, underscores, and hyphens"
        )
    return slug


def validate_date(value: str) -> str:
    if not ISO_DATE.fullmatch(value):
        raise FinalizationError("date must use YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise FinalizationError("date must be a real calendar date") from exc
    return value


def safe_filename_component(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value)
    value = " ".join(value.split()).strip(" .")
    if not value:
        raise FinalizationError("candidate name cannot be empty")
    return value[:100].rstrip(" .")


def run_command(command: list[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise FinalizationError(f"required command was not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        output = "\n".join(part for part in (exc.stdout, exc.stderr) if part).strip()
        tail = "\n".join(output.splitlines()[-30:])
        raise FinalizationError(
            f"{command[0]} failed while compiling in {cwd}:\n{tail or 'no output'}"
        ) from exc
    return "\n".join(part for part in (completed.stdout, completed.stderr) if part)


def compile_document(source: Path, engine: str) -> tuple[Path, list[str]]:
    source = source.resolve()
    if not source.is_file():
        raise FinalizationError(f"LaTeX source does not exist: {source}")
    if source.suffix.casefold() != ".tex":
        raise FinalizationError(f"expected a .tex source: {source}")

    command = [engine, "-interaction=nonstopmode", "-halt-on-error", source.name]
    for _ in range(2):
        run_command(command, source.parent)

    pdf = source.with_suffix(".pdf")
    if not pdf.is_file():
        raise FinalizationError(f"compiler did not create the expected PDF: {pdf}")

    log = source.with_suffix(".log")
    warnings = []
    if log.is_file():
        warnings = [
            line.strip()
            for line in log.read_text(encoding="utf-8", errors="replace").splitlines()
            if "Font shape" in line
        ]
    return pdf, warnings


def cleanup_latex_artifacts(source: Path) -> None:
    base = source.with_suffix("")
    for suffix in LATEX_ARTIFACT_SUFFIXES:
        artifact = Path(str(base) + suffix)
        if artifact.is_file():
            artifact.unlink()


def serialize_results(results) -> list[dict]:
    return [
        {
            "name": result.name,
            "status": result.status,
            "details": result.details,
            "reason": result.reason,
        }
        for result in results
    ]


def render_previews(pdf: Path, build_dir: Path, label: str) -> tuple[list[Path], str | None]:
    executable = shutil.which("pdftoppm")
    if not executable:
        return [], "pdftoppm not found; open the PDF itself for visual review"

    prefix = build_dir / f"{label}-page"
    try:
        run_command(
            [executable, "-png", "-r", "120", str(pdf), str(prefix)],
            build_dir,
        )
    except FinalizationError as exc:
        return [], str(exc)
    return sorted(build_dir.glob(f"{label}-page-*.png")), None


def check_document(
    *,
    label: str,
    source: Path,
    engine: str,
    repo: Path,
    build_dir: Path,
) -> dict:
    pdf, font_warnings = compile_document(source, engine)
    try:
        kwargs = {
            "expected_pages": 1,
            "min_chars": 300,
            "check_placeholders": True,
        }
        if label == "cv":
            kwargs = {
                "max_pages": 2,
                "min_chars": 500,
                "check_placeholders": True,
                "check_layout_quality": True,
            }
        results = run_check_suite(pdf, **kwargs)
        raw_text = extract_text(pdf, layout=False)
        layout_text = extract_text(pdf, layout=True)
        (build_dir / f"{label}-raw.txt").write_text(raw_text, encoding="utf-8")
        (build_dir / f"{label}-layout.txt").write_text(layout_text, encoding="utf-8")
        previews, preview_warning = render_previews(pdf, build_dir, label)
    except VerificationError as exc:
        raise FinalizationError(str(exc)) from exc
    finally:
        cleanup_latex_artifacts(source)

    mechanical_failure = any(result.status in {FAIL, SKIP} for result in results)
    # The CV template currently emits known bold/italic substitutions. Record
    # them for review, but do not fail a document already proven ATS-readable.
    # A cover letter should not need substitutions, so fail it if they appear.
    font_failure = label == "cover" and bool(font_warnings)
    return {
        "source": relative_to_repo(source, repo),
        "source_sha256": sha256(source),
        "pdf": relative_to_repo(pdf, repo),
        "pdf_sha256": sha256(pdf),
        "engine": engine,
        "checks": serialize_results(results),
        "font_shape_warnings": font_warnings,
        "previews": [relative_to_repo(path, repo) for path in previews],
        "preview_warning": preview_warning,
        "clean": not mechanical_failure and not font_failure,
    }


def receipt_path(repo: Path, slug: str) -> Path:
    return repo / BUILD_DIR / validate_slug(slug) / "receipt.json"


def attempt_ledger_path(repo: Path, slug: str) -> Path:
    return repo / BUILD_DIR / validate_slug(slug) / "attempts.json"


def _new_attempt_ledger(slug: str) -> dict:
    return {
        "version": ATTEMPT_LEDGER_VERSION,
        "slug": slug,
        "status": "active",
        "human_override_used": False,
        "checks": [],
    }


def _load_attempt_ledger(path: Path, slug: str) -> dict:
    if not path.is_file():
        return _new_attempt_ledger(slug)
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalizationError(f"could not read check-attempt ledger: {path}") from exc
    if ledger.get("version") != ATTEMPT_LEDGER_VERSION:
        raise FinalizationError("unsupported check-attempt ledger version")
    if ledger.get("slug") != slug:
        raise FinalizationError("check-attempt ledger belongs to another application")
    if ledger.get("status") not in {"active", "closed"}:
        raise FinalizationError("check-attempt ledger has an invalid status")
    if not isinstance(ledger.get("checks"), list):
        raise FinalizationError("check-attempt ledger has an invalid checks list")
    return ledger


def begin_check_attempt(
    repo: Path,
    slug: str,
    *,
    human_override: bool = False,
) -> dict:
    """Reserve one bounded check attempt before invoking either compiler.

    An exported application closes its ledger. The next check for the same slug
    starts a new drafting run. An unfinished run gets three ordinary checks and
    exactly one user-authorized final check; there is no fifth attempt.
    """

    path = attempt_ledger_path(repo, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger = _load_attempt_ledger(path, slug)
    if ledger["status"] == "closed":
        ledger = _new_attempt_ledger(slug)

    completed_or_started = len(ledger["checks"])
    next_number = completed_or_started + 1
    if next_number <= MAX_STANDARD_CHECK_ATTEMPTS:
        if human_override:
            raise FinalizationError(
                "--human-override is valid only after all three standard checks"
            )
        override_used = False
    elif next_number == MAX_STANDARD_CHECK_ATTEMPTS + MAX_HUMAN_OVERRIDE_ATTEMPTS:
        if not human_override:
            raise FinalizationError(
                "three checks are already recorded for this application. Stop and "
                "report the latest receipt. Only after the user explicitly authorizes "
                "one final correction may you rerun with --human-override; do not run "
                "xelatex, lualatex, pdftotext, pdfinfo, or diagnostic TeX copies"
            )
        if ledger.get("human_override_used"):
            raise FinalizationError("the one human-authorized check was already used")
        ledger["human_override_used"] = True
        override_used = True
    else:
        raise FinalizationError(
            "the four-check hard limit has been reached. Stop; no compiler or "
            "diagnostic command is authorized for this application"
        )

    attempt = {
        "number": next_number,
        "started_at": utc_now(),
        "finished_at": None,
        "status": "running",
        "human_override": override_used,
    }
    ledger["checks"].append(attempt)
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return attempt


def finish_check_attempt(repo: Path, slug: str, number: int, status: str) -> None:
    path = attempt_ledger_path(repo, slug)
    ledger = _load_attempt_ledger(path, slug)
    checks = ledger["checks"]
    if not checks or checks[-1].get("number") != number:
        raise FinalizationError("check-attempt ledger is out of sequence")
    checks[-1]["finished_at"] = utc_now()
    checks[-1]["status"] = status
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def close_attempt_ledger(repo: Path, slug: str) -> None:
    path = attempt_ledger_path(repo, slug)
    if not path.is_file():
        return
    ledger = _load_attempt_ledger(path, slug)
    ledger["status"] = "closed"
    ledger["closed_at"] = utc_now()
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_check(args) -> int:
    repo = Path.cwd().resolve()
    slug = validate_slug(args.slug)
    build_dir = receipt_path(repo, slug).parent
    build_dir.mkdir(parents=True, exist_ok=True)
    attempt = begin_check_attempt(
        repo,
        slug,
        human_override=getattr(args, "human_override", False),
    )
    for stale in build_dir.glob("*-page-*.png"):
        stale.unlink()

    receipt = {
        "version": RECEIPT_VERSION,
        "slug": slug,
        "checked_at": utc_now(),
        "check_attempt": attempt["number"],
        "human_override": attempt["human_override"],
        "status": "failed",
        "visual_approved": False,
        "documents": {},
    }
    path = build_dir / "receipt.json"
    try:
        receipt["documents"]["cv"] = check_document(
            label="cv",
            source=(repo / args.cv_source).resolve(),
            engine=args.cv_engine,
            repo=repo,
            build_dir=build_dir,
        )
        receipt["documents"]["cover"] = check_document(
            label="cover",
            source=(repo / args.cover_source).resolve(),
            engine=args.cover_engine,
            repo=repo,
            build_dir=build_dir,
        )
        if all(document["clean"] for document in receipt["documents"].values()):
            receipt["status"] = "clean"
    except FinalizationError as exc:
        receipt["error"] = str(exc)

    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    finish_check_attempt(repo, slug, attempt["number"], receipt["status"])
    limit = MAX_STANDARD_CHECK_ATTEMPTS + int(attempt["human_override"])
    suffix = " (human override)" if attempt["human_override"] else ""
    print(f"Check attempt: {attempt['number']}/{limit}{suffix}")
    print(f"Receipt: {relative_to_repo(path, repo)}")
    for label, document in receipt["documents"].items():
        print(f"\n{label.upper()}: {document['pdf']}")
        for result in document["checks"]:
            suffix = f" {result['details']}" if result["details"] else ""
            print(f"  {result['status']:<5} {result['name']}{suffix}")
        if document["font_shape_warnings"]:
            print(f"  NOTE  font-shape warnings: {len(document['font_shape_warnings'])}")
        if document["preview_warning"]:
            print(f"  NOTE  {document['preview_warning']}")

    if receipt["status"] != "clean":
        print(f"\nFAILED: {receipt.get('error', 'one or more checks failed')}", file=sys.stderr)
        return 1
    has_advisories = any(
        result["status"] == WARN
        for document in receipt["documents"].values()
        for result in document["checks"]
    )
    if has_advisories:
        print(
            "\nCLEAN WITH ADVISORIES: hard checks passed. Judge every WARN during "
            "visual review, then run export with --visual-approved."
        )
    else:
        print("\nCLEAN: inspect every preview/PDF, then run export with --visual-approved.")
    return 0


def load_clean_receipt(path: Path) -> dict:
    if not path.is_file():
        raise FinalizationError(f"check receipt does not exist: {path}")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FinalizationError(f"could not read check receipt: {path}") from exc
    if receipt.get("version") != RECEIPT_VERSION:
        raise FinalizationError("unsupported receipt version; run check again")
    if receipt.get("status") != "clean":
        raise FinalizationError("the latest check did not pass cleanly")
    return receipt


def verify_receipt_hashes(receipt: dict, repo: Path) -> dict[str, tuple[Path, Path]]:
    paths = {}
    for label in ("cv", "cover"):
        document = receipt.get("documents", {}).get(label)
        if not document:
            raise FinalizationError(f"receipt is missing the {label} document")
        source = resolve_recorded_path(document["source"], repo)
        pdf = resolve_recorded_path(document["pdf"], repo)
        for path, hash_key in ((source, "source_sha256"), (pdf, "pdf_sha256")):
            if not path.is_file() or sha256(path) != document.get(hash_key):
                raise FinalizationError(
                    f"{label} {path.name} changed after check; run check again"
                )
        paths[label] = (source, pdf)
    return paths


def run_export(args) -> int:
    if not args.visual_approved:
        raise FinalizationError(
            "visual approval is required; inspect every page, then pass --visual-approved"
        )
    repo = Path.cwd().resolve()
    slug = validate_slug(args.slug)
    path = receipt_path(repo, slug)
    receipt = load_clean_receipt(path)
    documents = verify_receipt_hashes(receipt, repo)

    candidate = safe_filename_component(args.candidate_name)
    delivery_root = (repo / args.delivery_root).resolve()
    destination = delivery_root / validate_date(args.date) / slug
    destination.mkdir(parents=True, exist_ok=True)
    suffixes = (
        {"cv": "CV", "cover": "Cover-Letter"}
        if args.document_language == "en"
        else {"cv": "Lebenslauf", "cover": "Anschreiben"}
    )
    targets = {
        label: destination / f"{candidate}-{suffix}.pdf"
        for label, suffix in suffixes.items()
    }
    for label, (_, pdf) in documents.items():
        shutil.copy2(pdf, targets[label])

    receipt["visual_approved"] = True
    receipt["exported_at"] = utc_now()
    receipt["exports"] = {
        label: relative_to_repo(target, repo) for label, target in targets.items()
    }
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    close_attempt_ledger(repo, slug)
    print(f"Exported checked application to: {relative_to_repo(destination, repo)}")
    for target in targets.values():
        print(f"  {target.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="compile twice and run mechanical checks")
    check.add_argument("--slug", required=True)
    check.add_argument("--cv-source", required=True, type=Path)
    check.add_argument("--cover-source", required=True, type=Path)
    check.add_argument("--cv-engine", default="lualatex")
    check.add_argument("--cover-engine", default="xelatex")
    check.add_argument(
        "--human-override",
        action="store_true",
        help="allow the one final check after three recorded attempts",
    )
    check.set_defaults(handler=run_check)

    export = subparsers.add_parser("export", help="export an unchanged, visually approved build")
    export.add_argument("--slug", required=True)
    export.add_argument("--candidate-name", required=True)
    export.add_argument("--date", default=date.today().isoformat())
    export.add_argument("--delivery-root", default="deliveries")
    export.add_argument("--document-language", choices=("de", "en"), default="de")
    export.add_argument("--visual-approved", action="store_true")
    export.set_defaults(handler=run_export)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except FinalizationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
