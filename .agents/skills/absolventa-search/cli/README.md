# absolventa-cli

CLI for searching jobs on Absolventa, the German student/working-student/graduate job board.

**Data source**: `www.absolventa.de/jobs` (search, HTML) and `/stellenangebote/<id>-p-<slug>` (detail, schema.org JSON-LD).
**Authentication**: None required.
**Dependencies**: None (plain `bun` + `fetch`). `bun install` is optional and only pulls dev type defs.

> `robots.txt` only blocks one unrelated abuse-report path - no ToS restriction on the
> paths this CLI uses, unlike some of the other portal skills in this repo.

## Installation

```bash
cd .agents/skills/absolventa-search/cli
bun install   # optional — only installs TypeScript dev types
```

The CLI runs without any install because it has zero runtime dependencies.

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search for job listings by category/position (`--query` is a local title filter, not sent to the portal) |
| `detail` | Fetch full detail for a single posting by its numeric ID |

`search` accepts `--format json|table|plain` (default `json`); `detail` accepts `--format json|plain`.
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` with exit code `1`.

## Quick examples

```bash
# Werkstudent roles in Controlling
bun run src/cli.ts search --category controlling --position werkstudent --format table

# Full detail for one posting
bun run src/cli.ts detail 12720125 --format plain
```

See `../SKILL.md` and `../url-reference.md` for the full flag reference and important
notes on why `--query` and location filtering work the way they do.

## Search flags

| Flag | Alias | Description |
|------|-------|-------------|
| `--category` | | Field/industry slug, e.g. `"controlling"`, `"finance"`. Portal-side filter. |
| `--position` | | Job type: `werkstudent` \| `praktikum` \| `trainee` \| `festanstellung` \| `abschlussarbeit`. Portal-side filter. |
| `--query` | `-q` | Client-side substring match on title (not sent to the portal - see notes). |
| `--page` | | 1-indexed page. |
| `--limit` | `-n` | Cap results emitted. |
| `--format` | | `json` \| `table` \| `plain`. |

## Tests

```bash
bun run typecheck   # tsc --noEmit
bun run test        # unit tests + a live smoke test against the real site
```
