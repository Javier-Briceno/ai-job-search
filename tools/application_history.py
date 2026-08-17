#!/usr/bin/env python3
"""Record append-only job-application events for later funnel analysis.

The existing ``job_search_tracker.csv`` remains the mutable current-state view.
This module owns a separate, gitignored event stream whose rows are immutable.
It uses only the Python standard library and writes files atomically.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


CONFIG_NAME = ".job-search-profile.json"
EVENTS_NAME = "application_events.csv"
EVENT_HEADER = (
    "event_id",
    "application_id",
    "timestamp",
    "profile_id",
    "event",
    "company",
    "role",
    "status",
    "channel",
    "fit_score",
    "workflow_commit",
    "experiment_id",
    "reason_or_feedback",
    "metadata",
)
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
EVENT_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class HistoryError(ValueError):
    """Raised when history input or existing state is invalid."""


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="")
    temporary.replace(path)


def _validate_id(value: str, label: str) -> str:
    value = value.strip().casefold()
    if not ID_PATTERN.fullmatch(value):
        raise HistoryError(
            f"{label} must be 1-64 lowercase letters, numbers, underscores, or hyphens"
        )
    return value


def _validate_event(value: str) -> str:
    value = value.strip().casefold()
    if not EVENT_PATTERN.fullmatch(value):
        raise HistoryError(
            "event must start with a lowercase letter and contain only lowercase "
            "letters, numbers, or underscores"
        )
    return value


def _validate_timestamp(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    candidate = value.strip()
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryError("timestamp must be an ISO-8601 date or datetime") from exc
    return candidate


def _validate_fit_score(value: str | int | float | None) -> str:
    if value is None or str(value).strip() == "":
        return ""
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise HistoryError("fit_score must be a number from 0 to 100") from exc
    if not 0 <= score <= 100:
        raise HistoryError("fit_score must be a number from 0 to 100")
    return str(int(score)) if score.is_integer() else str(score)


def _canonical_metadata(value: str | dict[str, Any] | None) -> str:
    if value is None or value == "":
        data: dict[str, Any] = {}
    elif isinstance(value, dict):
        data = value
    else:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise HistoryError("metadata must be a JSON object") from exc
        if not isinstance(parsed, dict):
            raise HistoryError("metadata must be a JSON object")
        data = parsed
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_config(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise HistoryError(
            f"tracking config not found: {path}. Run application_history.py init first"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoryError(f"tracking config is unreadable or invalid: {path}") from exc
    if not isinstance(data, dict):
        raise HistoryError("tracking config must be a JSON object")
    profile_id = _validate_id(str(data.get("profile_id", "")), "profile_id")
    experiment_id = _validate_id(
        str(data.get("experiment_id", "baseline")), "experiment_id"
    )
    return {"profile_id": profile_id, "experiment_id": experiment_id}


def initialize_config(
    path: Path,
    profile_id: str,
    experiment_id: str = "baseline",
    *,
    force: bool = False,
) -> dict[str, str | int]:
    profile_id = _validate_id(profile_id, "profile_id")
    experiment_id = _validate_id(experiment_id, "experiment_id")
    if path.exists() and not force:
        current = load_config(path)
        if current["profile_id"] != profile_id:
            raise HistoryError(
                f"tracking config already belongs to profile {current['profile_id']!r}; "
                "use --force only after verifying the worktree"
            )
    config: dict[str, str | int] = {
        "schema_version": 1,
        "profile_id": profile_id,
        "experiment_id": experiment_id,
    }
    _atomic_write_text(path, json.dumps(config, indent=2, ensure_ascii=False) + "\n")
    return config


def set_experiment(path: Path, experiment_id: str) -> dict[str, str | int]:
    current = load_config(path)
    return initialize_config(
        path,
        current["profile_id"],
        experiment_id,
        force=True,
    )


def _workflow_commit(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    commit = result.stdout.strip()
    if result.returncode != 0 or not commit:
        return "unknown"
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if dirty.returncode != 0:
        return f"{commit}+status-unknown"
    return f"{commit}+dirty" if dirty.stdout.strip() else commit


def load_events(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != EVENT_HEADER:
            raise HistoryError(
                f"{path} has an incompatible header; expected {','.join(EVENT_HEADER)}"
            )
        return list(reader)


def _write_events(path: Path, rows: list[dict[str, str]]) -> None:
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=EVENT_HEADER, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    _atomic_write_text(path, buffer.getvalue())


def _same_identity(row: dict[str, str], profile_id: str, company: str, role: str) -> bool:
    return (
        row.get("profile_id", "").casefold() == profile_id.casefold()
        and row.get("company", "").strip().casefold() == company.strip().casefold()
        and row.get("role", "").strip().casefold() == role.strip().casefold()
    )


def record_event(
    *,
    repo: Path,
    config_path: Path,
    events_path: Path,
    event: str,
    company: str,
    role: str,
    timestamp: str | None = None,
    application_id: str | None = None,
    new_application: bool = False,
    status: str = "",
    channel: str = "",
    fit_score: str | int | float | None = None,
    workflow_commit: str | None = None,
    experiment_id: str | None = None,
    reason_or_feedback: str = "",
    metadata: str | dict[str, Any] | None = None,
) -> tuple[dict[str, str], bool]:
    config = load_config(config_path)
    profile_id = config["profile_id"]
    selected_experiment = _validate_id(
        experiment_id or config["experiment_id"], "experiment_id"
    )
    event = _validate_event(event)
    company = company.strip()
    role = role.strip()
    if not company or not role:
        raise HistoryError("company and role are required")
    if application_id and new_application:
        raise HistoryError("--application-id and --new-application cannot be combined")

    rows = load_events(events_path)
    if application_id:
        selected_application = application_id.strip()
        if not selected_application:
            raise HistoryError("application_id cannot be empty")
    elif new_application:
        selected_application = f"app_{uuid4().hex}"
    else:
        matches = [
            row
            for row in rows
            if _same_identity(row, profile_id, company, role)
        ]
        selected_application = (
            matches[-1]["application_id"] if matches else f"app_{uuid4().hex}"
        )

    row = {
        "event_id": f"evt_{uuid4().hex}",
        "application_id": selected_application,
        "timestamp": _validate_timestamp(timestamp),
        "profile_id": profile_id,
        "event": event,
        "company": company,
        "role": role,
        "status": status.strip().casefold(),
        "channel": channel.strip().casefold(),
        "fit_score": _validate_fit_score(fit_score),
        "workflow_commit": (workflow_commit or _workflow_commit(repo)).strip() or "unknown",
        "experiment_id": selected_experiment,
        "reason_or_feedback": reason_or_feedback.strip(),
        "metadata": _canonical_metadata(metadata),
    }

    # Re-running a command with the same factual event must not create history.
    # workflow_commit and event_id are provenance, not part of factual identity.
    dedupe_fields = tuple(
        field for field in EVENT_HEADER if field not in {"event_id", "workflow_commit"}
    )
    for existing in rows:
        if all(existing.get(field, "") == row[field] for field in dedupe_fields):
            return existing, False

    rows.append(row)
    _write_events(events_path, rows)
    return row, True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=CONFIG_NAME, help="tracking config path")
    parser.add_argument("--events", default=EVENTS_NAME, help="event CSV path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create or update profile tracking config")
    init.add_argument("--profile-id", required=True)
    init.add_argument("--experiment-id", default="baseline")
    init.add_argument("--force", action="store_true")

    experiment = subparsers.add_parser("experiment", help="select the active experiment")
    experiment.add_argument("--id", required=True, dest="experiment_id")

    show = subparsers.add_parser("show-config", help="print the active tracking identity")
    show.set_defaults(show=True)

    record = subparsers.add_parser("record", help="append one application event")
    record.add_argument("--event", required=True)
    record.add_argument("--company", required=True)
    record.add_argument("--role", required=True)
    record.add_argument("--timestamp")
    record.add_argument("--application-id")
    record.add_argument("--new-application", action="store_true")
    record.add_argument("--status", default="")
    record.add_argument("--channel", default="")
    record.add_argument("--fit-score")
    record.add_argument("--workflow-commit")
    record.add_argument("--experiment-id")
    record.add_argument("--reason-or-feedback", default="")
    record.add_argument("--metadata", default="{}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    repo = Path.cwd().resolve()
    config_path = (repo / args.config).resolve()
    events_path = (repo / args.events).resolve()
    try:
        if args.command == "init":
            config = initialize_config(
                config_path,
                args.profile_id,
                args.experiment_id,
                force=args.force,
            )
            print(json.dumps(config, ensure_ascii=False, sort_keys=True))
        elif args.command == "experiment":
            config = set_experiment(config_path, args.experiment_id)
            print(json.dumps(config, ensure_ascii=False, sort_keys=True))
        elif args.command == "show-config":
            print(json.dumps(load_config(config_path), ensure_ascii=False, sort_keys=True))
        else:
            row, created = record_event(
                repo=repo,
                config_path=config_path,
                events_path=events_path,
                event=args.event,
                company=args.company,
                role=args.role,
                timestamp=args.timestamp,
                application_id=args.application_id,
                new_application=args.new_application,
                status=args.status,
                channel=args.channel,
                fit_score=args.fit_score,
                workflow_commit=args.workflow_commit,
                experiment_id=args.experiment_id,
                reason_or_feedback=args.reason_or_feedback,
                metadata=args.metadata,
            )
            result = {
                "created": created,
                "event_id": row["event_id"],
                "application_id": row["application_id"],
            }
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except HistoryError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
