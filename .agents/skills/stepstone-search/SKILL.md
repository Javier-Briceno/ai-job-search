---
name: stepstone-search
version: 1.0.0
description: >
  Use this skill for job searches on Stepstone, Germany's largest general job
  board, with strong Mittelstand and Controlling/Finance coverage. Trigger
  phrases: stepstone, stepstone.de, jobs on stepstone.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/stepstone-search/cli/src/cli.ts *)
---

# Stepstone-Search Skill

Search live job listings from Stepstone, Germany's largest general job board.

## ⚠️ Personal use only - read before using

Stepstone's `robots.txt` disallows `/search-results` and `/listing` - both added
within the last few months per the file's own edit-date comments, and both look like
the site's current search-results and job-detail surface. This skill instead uses a
different, **still-allowed** path for search (`/jobs/<keyword>/in-<city>`, without a
disallowed query string - robots.txt only blocks `/jobs/*?*` beyond `?q=...`, and this
path needs no query string at all). It was built anyway, at explicit user request, for
**personal use only.** Keep volume low, never use it commercially or for bulk
collection, and run it on your own responsibility.

**`detail` is expected to fail.** Stepstone's job-detail pages
(`/stellenangebote--...-inline.html`) were verified during development to actively
reset the TLS connection - this happened with both `curl` and Bun's `fetch()`, is not
a transient network issue, and matches the robots.txt disallow of `/listing`. `detail`
uses a hard timeout and reports this with a clear `BLOCKED` error rather than hanging
indefinitely or pretending to work.

## When to use this skill

- Search for job openings on Stepstone by keyword and city

## Commands

### Search job listings

```bash
bun run .agents/skills/stepstone-search/cli/src/cli.ts search --query "<text>" --location "<city>" [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — **required.** Job title or keyword, e.g. `"Werkstudent Controlling"`
- `--location <text>` / `-l <text>` — **required.** City, e.g. `"Köln"`, `"Frankfurt am Main"`
- `--page <n>` — 1-indexed page. Default 1.
- `--limit <n>` / `-n <n>` — cap results emitted (client-side)
- `--format json|table|plain` — default `json`

### Fetch full job detail (expected to fail - see warning above)

```bash
bun run .agents/skills/stepstone-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

## Usage examples

```bash
bun run .agents/skills/stepstone-search/cli/src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table
bun run .agents/skills/stepstone-search/cli/src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt am Main" --page 2 --format table
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use |
| `table` | Quick human-readable scanning |
| `plain` | Reading a short summary per result |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- `date` is Stepstone's own relative text (e.g. `"vor 16 Stunden"`, `"vor 1 Woche"`), not an ISO date.
- Query and location are converted to Stepstone's own URL-slug scheme (lowercase, spaces→hyphens, `ö→oe`/`ü→ue`/`ä→ae`/`ß→ss`) - both are required since the search URL is built as `/jobs/<keyword-slug>/in-<city-slug>`.
- No structured JSON-LD job list is embedded on the results page - `search` parses job "cards" out of the HTML directly, with Stepstone's inline emotion-CSS `<style>` blocks stripped first (they carry no visible text but badly interfere with a naive field-boundary scan).
