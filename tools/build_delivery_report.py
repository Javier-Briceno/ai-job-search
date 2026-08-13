#!/usr/bin/env python3
"""Build a private, self-contained HTML index for review-ready applications."""

from __future__ import annotations

import argparse
import csv
import html
import os
from datetime import date
from pathlib import Path
from urllib.parse import quote, urlparse


def _safe_source_url(value: str) -> str | None:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value
    return None


def _pdf_link(repo: Path, output_dir: Path, value: str) -> str | None:
    if not value.strip():
        return None
    candidate = (repo / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        candidate.relative_to(output_dir)
    except ValueError:
        return None
    if candidate.suffix.lower() != ".pdf" or not candidate.is_file():
        return None
    relative = os.path.relpath(candidate, output_dir).replace(os.sep, "/")
    return quote(relative, safe="/._-")


def _identity(value: str) -> str:
    """Match the workflow's lowercase/underscore folder convention defensively."""
    return "".join(character for character in value.casefold() if character.isalnum())


def _delivery_pdf(repo: Path, output_dir: Path, row: dict[str, str], kind: str) -> str | None:
    """Find the human-named PDF copy produced by /apply's export step."""
    day = row.get("date", "").strip()
    date_dir = repo / "deliveries" / day
    if not day or not date_dir.is_dir():
        return None
    wanted = _identity(f'{row.get("company", "")}_{row.get("role", "")}')
    folders = [path for path in date_dir.iterdir() if path.is_dir() and _identity(path.name) == wanted]
    keywords = {
        "cv": ("lebenslauf", "-cv", "_cv"),
        "cover": ("anschreiben", "cover-letter", "cover_letter", "-cover"),
    }[kind]
    for folder in sorted(folders):
        for candidate in sorted(folder.glob("*.pdf")):
            if any(keyword in candidate.stem.casefold() for keyword in keywords):
                return _pdf_link(repo, output_dir, str(candidate))
    return None


def load_drafts(tracker: Path) -> list[dict[str, str]]:
    if not tracker.is_file():
        return []
    with tracker.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    drafts = [row for row in rows if row.get("status", "").strip().lower() == "drafted"]
    return sorted(
        drafts,
        key=lambda row: (row.get("date", ""), row.get("company", ""), row.get("role", "")),
        reverse=True,
    )


def render_report(rows: list[dict[str, str]], repo: Path, output: Path, today: str) -> str:
    cards: list[str] = []
    for row in rows:
        company = html.escape(row.get("company", "").strip() or "Unknown company")
        role = html.escape(row.get("role", "").strip() or "Unknown role")
        drafted = html.escape(row.get("date", "").strip() or "Unknown date")
        score = html.escape(row.get("fit_rating", "").strip() or "-")
        cv = _pdf_link(repo, output.parent, row.get("cv_file", "")) or _delivery_pdf(
            repo, output.parent, row, "cv"
        )
        cover = _pdf_link(repo, output.parent, row.get("cover_letter_file", "")) or _delivery_pdf(
            repo, output.parent, row, "cover"
        )
        source = _safe_source_url(row.get("source", ""))
        badge = '<span class="badge">New today</span>' if row.get("date", "").strip() == today else ""
        actions = []
        if source:
            actions.append(
                f'<a class="primary" href="{html.escape(source, quote=True)}" target="_blank" rel="noopener noreferrer">Open application</a>'
            )
        if cv:
            actions.append(f'<a href="{html.escape(cv, quote=True)}" target="_blank">Download CV</a>')
        if cover:
            actions.append(f'<a href="{html.escape(cover, quote=True)}" target="_blank">Download cover letter</a>')
        missing = []
        if not cv:
            missing.append("CV")
        if not cover:
            missing.append("cover letter")
        warning = f'<p class="warning">Missing: {html.escape(" and ".join(missing))}</p>' if missing else ""
        cards.append(
            "\n".join(
                [
                    '<article class="card">',
                    f'<div class="card-head"><div><p class="company">{company}</p><h2>{role}</h2></div>{badge}</div>',
                    f'<p class="meta">Drafted {drafted} <span>Fit {score}/100</span></p>',
                    warning,
                    f'<div class="actions">{"".join(actions)}</div>',
                    '<p class="hint">After submitting, tell Javier the company name so he can record it as applied.</p>',
                    "</article>",
                ]
            )
        )

    content = "\n".join(cards) if cards else (
        '<section class="empty"><h2>No applications waiting</h2>'
        '<p>The next daily run will add newly prepared applications here.</p></section>'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Applications ready to submit</title>
<style>
:root{{--ink:#15202b;--muted:#65717d;--paper:#f6f4ef;--card:#fff;--accent:#155eef;--line:#ddd8ce;--warn:#9a3412}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,-apple-system,sans-serif}}
main{{max-width:900px;margin:auto;padding:48px 20px 72px}} header{{margin-bottom:28px}} h1{{font-size:clamp(2rem,6vw,3.4rem);line-height:1.05;margin:0 0 12px}}
.summary,.meta,.hint{{color:var(--muted)}} .grid{{display:grid;gap:18px}} .card,.empty{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:24px;box-shadow:0 8px 28px #1c19170d}}
.card-head{{display:flex;justify-content:space-between;gap:18px;align-items:start}} .company{{font-weight:700;margin:0 0 4px}} h2{{margin:0;font-size:1.35rem}}
.badge{{white-space:nowrap;background:#dcfce7;color:#166534;border-radius:999px;padding:5px 10px;font-size:.78rem;font-weight:700}} .meta span{{margin-left:12px;font-weight:700}}
.actions{{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 8px}} .actions a{{border:1px solid var(--line);border-radius:10px;padding:10px 14px;color:var(--ink);text-decoration:none;font-weight:650}}
.actions a.primary{{background:var(--accent);border-color:var(--accent);color:white}} .actions a:hover{{transform:translateY(-1px)}} .warning{{color:var(--warn);font-weight:700}} .hint{{font-size:.88rem;margin-bottom:0}}
@media(max-width:520px){{main{{padding-top:28px}}.card-head{{display:block}}.badge{{display:inline-block;margin-top:10px}}.actions a{{width:100%;text-align:center}}}}
</style>
</head>
<body><main>
<header><h1>Applications ready to submit</h1><p class="summary">{len(rows)} draft application(s) waiting. Generated {html.escape(today)}. Open the job, upload the two PDFs, and submit manually.</p></header>
<section class="grid">{content}</section>
</main></body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracker", default="job_search_tracker.csv")
    parser.add_argument("--output", default="deliveries/index.html")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    repo = Path.cwd().resolve()
    tracker = (repo / args.tracker).resolve()
    output = (repo / args.output).resolve()
    try:
        output.relative_to(repo)
    except ValueError:
        parser.error("--output must stay inside the repository")
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = load_drafts(tracker)
    document = render_report(rows, repo, output, args.date)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(document, encoding="utf-8")
    temporary.replace(output)
    print(f"Delivery report: {output} ({len(rows)} draft(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
