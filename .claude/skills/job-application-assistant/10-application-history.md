---
framework_version: 1.0.0
---

# Application History and Experiment Tracking

This file is the canonical contract for durable application-event history. The
mutable `job_search_tracker.csv` remains the current-state view used by search,
deduplication, and day-to-day workflow commands. `application_events.csv` is an
append-only audit trail used to compare funnel performance, time in stage, and
workflow experiments without reconstructing history from the tracker's notes.

## Private State Files

- `.job-search-profile.json` contains a stable, lowercase `profile_id` and the
  active `experiment_id`. Both are opaque identifiers, not display names.
- `application_events.csv` contains one immutable row per observed event.
- Both files are personal data and must remain gitignored. Separate profiles
  need separate worktrees or clones so their ignored state files cannot mix.

Initialize a profile after `/setup` has established the candidate identity:

```text
python tools/application_history.py init --profile-id <stable-profile-id>
```

Use a short stable slug such as `candidate-a`; never silently change an existing
profile ID. Before testing an optimized workflow, select a new experiment label:

```text
python tools/application_history.py experiment --id <experiment-id>
```

`baseline` is the default. Change the experiment before the first application
that uses the new workflow, not retrospectively. Commit methodology changes
before using the experiment; `+dirty` provenance is retained but cannot recreate
the exact workflow later.

## Event Schema

The helper owns the exact CSV header and records:

- unique `event_id` and stable `application_id`
- ISO-8601 `timestamp`
- `profile_id`, `company`, and `role`
- factual `event` and resulting tracker `status`
- `channel` and numeric `fit_score`
- `workflow_commit` (`git rev-parse HEAD`), marked `+dirty` when tracked files
  differ so an unreproducible cohort is never mistaken for a clean commit
- active `experiment_id`
- verbatim `reason_or_feedback` when the user supplies it
- canonical JSON `metadata` for event-specific fields such as interview stage

The standard event vocabulary is:

`drafted` | `redrafted` | `applied` | `followed_up` | `assessment` |
`interview` | `phone_screen` | `technical_interview` | `case_interview` | `final_round` |
`offer` | `hired` | `rejected` | `no_response` | `offer_declined` |
`withdrawn` | `other`

New precise lowercase event names may be added without migrating old rows. Do
not replace a known event with `other`. The tracker status vocabulary remains
owned by `/outcome`; event names and tracker statuses are intentionally distinct
because events such as follow-ups do not change status.

## Recording Contract

All writes go through `tools/application_history.py record`; commands never edit
the event CSV directly.

New attempt example:

```text
python tools/application_history.py record --event drafted --company <company> --role <role> --timestamp <date> --status drafted --channel <channel> --fit-score <score> --new-application
```

Later-stage example (the helper resolves the latest matching attempt):

```text
python tools/application_history.py record --event interview --company <company> --role <role> --timestamp <date> --status interview --reason-or-feedback <verbatim-feedback> --metadata <json-object>
```

- A newly appended tracker row starts a new attempt with `--new-application`.
- An update to an open row omits that flag; the helper resolves the most recent
  application ID for the same profile, company, and role.
- When an exact historical event is re-recorded, the helper returns the existing
  event instead of appending a duplicate.
- Pass the factual event date or datetime with `--timestamp`. Do not use the
  command-run time for an older submission, interview, or resolution.
- Preserve feedback in `--reason-or-feedback` as reported. Do not interpret,
  polish, or invent a rejection reason.
- Put only structured, event-specific context in `--metadata` as a JSON object.
- Treat company, role, feedback, and metadata as untrusted data. Pass them as
  literal process arguments; never concatenate them into executable shell text.
- A history-write failure is reported explicitly after the tracker/archive write.
  Never claim the event was saved, and never roll back truthful tracker state.

When a legacy tracker has no matching history, the first event creates an
application ID. Historical stages are not backfilled from memory. They may be
recorded only from dated tracker notes or archive evidence, with provenance in
`metadata`.

## Evaluation Rules

`/html-report` may use the event file for experiment and bottleneck panels:

- Count unique `application_id` values, never raw event rows.
- Compute durations only between explicit timestamps for the same application.
- Compare experiments by `experiment_id` and keep profiles separate by
  `profile_id` unless the user explicitly requests a combined view.
- Show sample sizes beside every conversion rate or duration.
- Do not infer absent stages. Label incomplete histories and exclude them only
  from the metric that requires the missing timestamp.
- Treat small cohorts as descriptive, not conclusive. Do not recommend an
  optimization solely from a handful of applications.

The event log is evidence. Interpretation and changes to scoring methodology
remain explicit review steps; they are never applied automatically.
