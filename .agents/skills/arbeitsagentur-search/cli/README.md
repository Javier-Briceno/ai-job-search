# arbeitsagentur-cli

CLI for searching jobs on the Bundesagentur für Arbeit (German Federal Employment Agency)
official Jobsuche API, across all of Germany.

**Data source**: `rest.arbeitsagentur.de/jobboerse/jobsuche-service` (`pc/v6/jobs`, `pc/v4/jobdetails/<encoded refnr>`).
**Authentication**: A single public, well-known static `X-API-Key` value. No account or registration.
**Dependencies**: None (plain `bun` + `fetch`). `bun install` is optional and only pulls dev type defs.

> This is an **official government API**, not scraped HTML - `arbeitsagentur.de`'s `robots.txt`
> is fully open (`Allow: /`). Unlike some of the other portal skills in this repo, there is
> no ToS or personal-use restriction here.

## Installation

```bash
cd .agents/skills/arbeitsagentur-search/cli
bun install   # optional — only installs TypeScript dev types
```

The CLI runs without any install because it has zero runtime dependencies.

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search for job listings by keyword/title and location |
| `detail` | Fetch full detail for a single posting by its `refnr` |

`search` accepts `--format json|table|plain` (default `json`); `detail` accepts `--format json|plain`.
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` with exit code `1`.

## Quick examples

```bash
# Werkstudent Controlling roles in Köln
bun run src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table

# Same, last 14 days only
bun run src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt am Main" --jobage 14 --format table

# Full detail for one posting
bun run src/cli.ts detail 12811-2300109-S --format plain
```

See `../SKILL.md` for the full flag reference and API notes.

## Search flags

| Flag | Alias | Description |
|------|-------|-------------|
| `--query` | `-q` | Job title / keyword, e.g. `"Werkstudent Controlling"`. |
| `--location` | `-l` | City, region, or postal code, e.g. `"Köln"`, `"50667"`. |
| `--jobage` | | Only postings published within N days (0-100). |
| `--radius` | | Search radius in km around `--location`. |
| `--parttime` | | Filter to part-time/Werkstudent-style postings. |
| `--page` | | 1-indexed page (25 results/page). |
| `--limit` | `-n` | Cap results emitted. |
| `--format` | | `json` \| `table` \| `plain`. |

## Tests

```bash
bun run typecheck   # tsc --noEmit
bun run test        # unit tests + a live smoke test against the real API
```
