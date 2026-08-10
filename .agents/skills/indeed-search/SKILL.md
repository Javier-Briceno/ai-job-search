---
name: indeed-search
version: 1.0.0
description: >
  Use this skill for job searches on Indeed (default market: Germany, de.indeed.com).
  Trigger phrases: indeed, indeed jobs, indeed.com, indeed.de, jobs on indeed.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/indeed-search/cli/src/cli.ts *)
---

# Indeed-Search Skill

Search live job listings from Indeed's public search-results pages (default market:
Germany).

## ⚠️ Personal use only - read before using

Indeed's `robots.txt` has a dedicated block that **specifically names AI crawlers**
(`ClaudeBot`, `GPTBot`, `anthropic-ai`, and others) and disallows `/jobs` (search) and
`/viewjob` (detail) for them. This is a stronger signal than a generic catch-all
disallow - Indeed deliberately excluded AI agents from these paths. This skill was
built anyway **at explicit user request, for personal use only.** Keep volume low,
never use it commercially or for bulk collection, and run it on your own responsibility.

**Additionally, this is the one portal skill in this repo that requires `curl` on
PATH.** Indeed's anti-bot system blocks Bun's native `fetch()` with a 403 even with a
full browser-matched header set - this points to TLS/client fingerprinting, not
anything fixable via headers. Plain `curl` was verified to get through. See
`url-reference.md` for the verification detail. If `curl` is not installed, `search`
and `detail` will both fail with a clear error explaining why.

**`detail` is expected to fail.** Indeed's `/viewjob` page is actively blocked
regardless of client (bare 403, or a "Security Check" interstitial) - this was verified
during development, not assumed. `detail` reports this with a clear `BLOCKED` error
rather than pretending to work. Use the `snippet` field `search` already returns for a
short preview instead.

## When to use this skill

- Search for job openings on Indeed by keyword and location (default market: Germany)
- Get a short preview (`snippet`) of each listing directly from search results

## Commands

### Search job listings

```bash
bun run .agents/skills/indeed-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keywords (title, skill, role), e.g. `"Werkstudent Controlling"`
- `--location <text>` / `-l <text>` — city or region, e.g. `"Köln"`
- `--domain <host>` — Indeed country domain. Default: `de.indeed.com`
- `--page <n>` — 1-indexed page (15 results/page)
- `--limit <n>` / `-n <n>` — cap results emitted (client-side)
- `--format json|table|plain` — default `json`

### Fetch full job detail (expected to fail - see warning above)

```bash
bun run .agents/skills/indeed-search/cli/src/cli.ts detail <jobkey> [--format json|plain]
```

## Usage examples

```bash
bun run .agents/skills/indeed-search/cli/src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table
bun run .agents/skills/indeed-search/cli/src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt" --format plain
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use |
| `table` | Quick human-readable scanning |
| `plain` | Reading results with their preview snippet |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- Search results include a `snippet` field (a short bullet-point preview parsed from Indeed's own embedded data) - since `detail` is blocked, this is the richest description available.
- `date` is Indeed's own relative text (e.g. `"vor 19 Tagen"`), not an ISO date.
- Requires `curl` on PATH (see the warning above) - this is a deliberate deviation from this repo's usual zero-dependency `fetch()` pattern, made necessary by Indeed's anti-bot system.
