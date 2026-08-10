---
name: workwise-search
version: 1.0.0
description: >
  Use this skill for job searches on Workwise, a German student/SME-focused job
  board with a coherent single search interface, particularly for Werkstudent
  (working-student) roles. Trigger phrases: workwise, workwise.io, werkstudent
  jobs germany.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/workwise-search/cli/src/cli.ts *)
---

# Workwise-Search Skill

Search live job listings from Workwise, a German job board focused on students,
working students (Werkstudenten), and SMEs. **Zero runtime dependencies** - it runs
with just `bun`.

Workwise's own site is a client-rendered Next.js SPA with no job data in its
server-rendered HTML. The JSON APIs this skill calls (`search.workwise.io` and
`candidates.workwise.io`) were found via a real browser network capture, not from any
public documentation - see `url-reference.md` for how they were identified and
verified. Both were confirmed to work with no cookies/session required.

## When to use this skill

- Search for job openings on Workwise by keyword, optionally filtered to Werkstudent roles
- Get the full description, employer, hours/week, and salary range for a specific posting

## Commands

### Search job listings

```bash
bun run .agents/skills/workwise-search/cli/src/cli.ts search --query "<text>" [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — **required.** Job title or keyword, e.g. `"Controlling"`
- `--enquiry-type <id>` — filter by employment type. Only `1` (Werkstudententätigkeit / working-student roles) is **confirmed** - other IDs are unverified guesses, not documented anywhere. Omit for all types.
- `--size <n>` — results requested from the API. Default 14.
- `--limit <n>` / `-n <n>` — cap results emitted (client-side)
- `--format json|table|plain` — default `json`

### Fetch full job detail

```bash
bun run .agents/skills/workwise-search/cli/src/cli.ts detail <id> [--format json|plain]
```

`id` is the numeric job ID from `search` results (e.g. `125882`). Returns the full
structured description (broken into labeled sections like "Was erwartet dich?" /
"Was bringst du mit?"), employer, hours/week, salary range, and publish date.

## Usage examples

```bash
# Werkstudent roles matching "Controlling"
bun run .agents/skills/workwise-search/cli/src/cli.ts search -q "Werkstudent Controlling" --enquiry-type 1 --format table

# All employment types matching "Controlling"
bun run .agents/skills/workwise-search/cli/src/cli.ts search -q "Controlling" --format table

# Full details for a specific posting
bun run .agents/skills/workwise-search/cli/src/cli.ts detail 125882 --format plain
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, passing IDs to `detail` |
| `table` | Quick human-readable scanning (includes weekly hours) |
| `plain` | Reading a single job's full detail (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- **Location filtering is not supported.** Workwise's search API takes a structured location object (city/zip/lat/lon/`googlePlaceId`), which needs a geocoding lookup this CLI doesn't have - same class of limitation as `absolventa-search`'s location field. Each result's own `location` field still shows city/postal code from the portal itself.
- **Pagination beyond the first `--size` results is unverified** - no offset/page parameter was observed in the captured request that created this integration. Only a single batch is supported for now.
- `hoursPerWeek` (e.g. `"20h/Woche"` or `"12-20h/Woche"`) is directly useful for checking a posting against an hours cap (e.g. a student visa's weekly work-hour limit).
- `search` results do not include a publish date (`date` is always `null`) - use `detail`'s `firstPublished` field instead.
