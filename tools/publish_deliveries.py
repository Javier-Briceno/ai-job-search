#!/usr/bin/env python3
"""Publish outstanding drafts as Company/Position folders plus an HTML index."""

from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

try:
    from tools.build_delivery_report import delivery_pdf_path, load_drafts, render_report
except ModuleNotFoundError:  # Direct execution puts tools/ rather than the repo on sys.path.
    from build_delivery_report import delivery_pdf_path, load_drafts, render_report


WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def safe_component(value: str, fallback: str) -> str:
    cleaned = "".join("-" if character in '<>:"/\\|?*' or ord(character) < 32 else character for character in value)
    cleaned = " ".join(cleaned.split()).strip(" .")
    if not cleaned:
        cleaned = fallback
    if cleaned.upper() in WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned[:100].rstrip(" .") or fallback


def validate_destination(repo: Path, destination: Path) -> Path:
    destination = destination.expanduser().resolve()
    if destination == Path(destination.anchor):
        raise ValueError(f"refusing to publish directly into a drive root: {destination}")
    if destination == repo or repo in destination.parents:
        raise ValueError("destination must be outside the repository")
    return destination


def publish(repo: Path, tracker: Path, destination: Path, today: str) -> tuple[int, int]:
    destination = validate_destination(repo, destination)
    destination.mkdir(parents=True, exist_ok=True)
    rows = load_drafts(tracker)
    copied = 0

    for row in rows:
        company = safe_component(row.get("company", ""), "Unknown company")
        position = safe_component(row.get("role", ""), "Unknown position")
        application_dir = destination / company / position
        application_dir.mkdir(parents=True, exist_ok=True)

        for field, kind in (("cv_file", "cv"), ("cover_letter_file", "cover")):
            source = delivery_pdf_path(repo, row, kind)
            if not source:
                row[field] = ""
                continue
            target = application_dir / source.name
            shutil.copy2(source, target)
            row[field] = str(target)
            copied += 1

    output = destination / "index.html"
    document = render_report(rows, repo, output, today)
    temporary = destination / "index.html.tmp"
    temporary.write_text(document, encoding="utf-8")
    temporary.replace(output)
    return len(rows), copied


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--tracker", default="job_search_tracker.csv")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    repo = Path.cwd().resolve()
    tracker = (repo / args.tracker).resolve()
    try:
        drafts, copied = publish(repo, tracker, Path(args.destination), args.date)
    except ValueError as error:
        parser.error(str(error))
    print(f"Published {drafts} draft(s), {copied} PDF(s) to: {Path(args.destination).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
