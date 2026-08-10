# workwise-cli

CLI for searching jobs on Workwise, a German student/SME-focused job board.

**Data source**: `search.workwise.io/v2/searches` (search, JSON POST) and `candidates.workwise.io/v2/enquiries/<id>` (detail, JSON GET) - reverse-engineered from a real browser network capture, see `../url-reference.md`.
**Authentication**: None required.
**Dependencies**: None (plain `bun` + `fetch`). `bun install` is optional and only pulls dev type defs.

## Installation

```bash
cd .agents/skills/workwise-search/cli
bun install   # optional — only installs TypeScript dev types
```

The CLI runs without any install because it has zero runtime dependencies.

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search for job listings by keyword, optionally filtered to Werkstudent roles (`--enquiry-type 1`) |
| `detail` | Fetch full detail for a single posting by its numeric ID |

`search` accepts `--format json|table|plain` (default `json`); `detail` accepts `--format json|plain`.
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` with exit code `1`.

## Quick examples

```bash
bun run src/cli.ts search -q "Werkstudent Controlling" --enquiry-type 1 --format table
bun run src/cli.ts detail 125882 --format plain
```

See `../SKILL.md` and `../url-reference.md` for the full flag reference and important
notes on the location-filtering and pagination limitations.

## Search flags

| Flag | Alias | Description |
|------|-------|-------------|
| `--query` | `-q` | **Required.** Job title or keyword. |
| `--enquiry-type` | | Employment-type ID. Only `1` (Werkstudent) is confirmed. |
| `--size` | | Results requested from the API. Default 14. |
| `--limit` | `-n` | Cap results emitted. |
| `--format` | | `json` \| `table` \| `plain`. |

## Tests

```bash
bun run typecheck   # tsc --noEmit
bun run test        # unit tests + a live smoke test against the real API
```
