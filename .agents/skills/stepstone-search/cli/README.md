# stepstone-cli

CLI for searching jobs on Stepstone, Germany's largest general job board.

**Data source**: `www.stepstone.de/jobs/<keyword>/in-<city>` search-results HTML.
**Authentication**: None required.
**Dependencies**: None (plain `bun` + `fetch`). `bun install` is optional and only pulls dev type defs.

> **⚠️ Personal use only.** Stepstone's `robots.txt` disallows `/search-results` and
> `/listing` (added within the last few months). This CLI uses a different,
> still-allowed path for search. Built anyway at explicit user request - keep volume
> low, no commercial or bulk use, run at your own responsibility.
>
> **`detail` is expected to fail** with a `BLOCKED` error - Stepstone's job-detail
> pages actively reset the connection (verified with both `curl` and `fetch()`
> during development). See `../url-reference.md`.

## Installation

```bash
cd .agents/skills/stepstone-search/cli
bun install   # optional — only installs TypeScript dev types
```

The CLI runs without any install because it has zero runtime dependencies.

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search for job listings (`--query` and `--location` both required) |
| `detail` | Attempts full detail for a posting - reliably reports `BLOCKED` (see warning above) |

`search` accepts `--format json|table|plain` (default `json`); `detail` accepts `--format json|plain`.
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` with exit code `1`.

## Quick examples

```bash
bun run src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table
bun run src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt am Main" --page 2 --format table
```

See `../SKILL.md` and `../url-reference.md` for the full flag reference and the
robots.txt / anti-bot notes on why this skill works the way it does.

## Search flags

| Flag | Alias | Description |
|------|-------|-------------|
| `--query` | `-q` | **Required.** Job title or keyword. |
| `--location` | `-l` | **Required.** City. |
| `--page` | | 1-indexed page. |
| `--limit` | `-n` | Cap results emitted. |
| `--format` | | `json` \| `table` \| `plain`. |

## Tests

```bash
bun run typecheck   # tsc --noEmit
bun run test        # unit tests + a live smoke test against the real site
```
