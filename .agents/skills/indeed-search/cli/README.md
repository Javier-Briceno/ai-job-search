# indeed-cli

CLI for searching jobs on Indeed (default market: Germany).

**Data source**: `de.indeed.com/jobs` search-results HTML (embedded `mosaic-provider-jobcards` JS object).
**Authentication**: None required.
**Dependencies**: Requires `curl` on PATH (see warning below) - this is the one portal skill in this repo that isn't zero-dependency.

> **⚠️ Personal use only.** Indeed's `robots.txt` specifically names AI crawlers
> (ClaudeBot, GPTBot, anthropic-ai, etc.) and disallows `/jobs` and `/viewjob` for
> them. Built anyway at explicit user request - keep volume low, no commercial or
> bulk use, run at your own responsibility.
>
> **Why `curl` instead of `fetch()`**: Bun's native `fetch()` is blocked (403) by
> Indeed's anti-bot system even with a full browser-matched header set - this points
> to TLS/client fingerprinting. Plain `curl` gets through. See `../url-reference.md`.
>
> **`detail` is expected to fail** with a `BLOCKED` error - Indeed actively blocks
> `/viewjob` regardless of client. Use the `snippet` field from `search` instead.

## Installation

```bash
cd .agents/skills/indeed-search/cli
bun install   # optional — only installs TypeScript dev types
```

Requires `curl` on PATH at runtime (ships by default on macOS, Linux, and Windows 10+).

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search for job listings by keyword/title and location |
| `detail` | Attempts full detail for a posting - reliably reports `BLOCKED` (see warning above) |

`search` accepts `--format json|table|plain` (default `json`); `detail` accepts `--format json|plain`.
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` with exit code `1`.

## Quick examples

```bash
bun run src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table
```

See `../SKILL.md` and `../url-reference.md` for the full flag reference and the
technical/legal notes on why this skill works the way it does.

## Search flags

| Flag | Alias | Description |
|------|-------|-------------|
| `--query` | `-q` | Keywords (title, skill, role). |
| `--location` | `-l` | City or region. |
| `--domain` | | Indeed country domain. Default `de.indeed.com`. |
| `--page` | | 1-indexed page (15 results/page). |
| `--limit` | `-n` | Cap results emitted. |
| `--format` | | `json` \| `table` \| `plain`. |

## Tests

```bash
bun run typecheck   # tsc --noEmit
bun run test        # unit tests + a live smoke test against the real site
```
