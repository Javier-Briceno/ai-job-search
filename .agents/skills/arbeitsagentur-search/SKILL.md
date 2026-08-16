---
name: arbeitsagentur-search
version: 1.0.1
description: >
  Use this skill for job searches in Germany via the Bundesagentur für Arbeit
  (German Federal Employment Agency) official Jobbörse. This is the largest
  German job database and is free for employers to post to, so it captures
  Mittelstand and public-sector postings absent from paid boards like Stepstone
  or Indeed. Trigger phrases: german jobs, jobs in germany, bundesagentur für
  arbeit, arbeitsagentur, jobbörse, jobsuche deutschland, stellenangebote,
  stellensuche, werkstudent jobs germany, german job search, find a job in
  germany, offene stellen, stellenanzeigen, minijob, werkstudent, praktikum
  deutschland.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts *)
---

# Arbeitsagentur-Search Skill

Search live job listings from the Bundesagentur für Arbeit's official public Jobsuche
API. No authentication beyond a public, well-known static client key, and **zero runtime
dependencies** - it runs with just `bun`.

This is an **official government API**, not scraped HTML: `arbeitsagentur.de`'s
`robots.txt` is fully open (`Allow: /`), so unlike some of the other portal skills in
this repo, there are no ToS or personal-use caveats here.

## When to use this skill

- Search for job openings anywhere in Germany, by keyword/title and city/region
- Filter by recency (published within N days), radius around a location, or part-time
- Get the full description, contract type, and application link for a specific posting

## Commands

### Search job listings

```bash
bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — job title or keyword, e.g. `"Werkstudent Controlling"`
- `--location <text>` / `-l <text>` — city, region, or postal code, e.g. `"Köln"`, `"Frankfurt am Main"`, `"50667"`
- `--jobage <days>` — only postings published within the last N days (0-100). Omit for all.
- `--radius <km>` — search radius around `--location` (portal default is roughly 25km)
- `--parttime` — filter to part-time/Werkstudent-style postings
- `--page <n>` — 1-indexed page (25 results per page)
- `--limit <n>` / `-n <n>` — cap total results emitted (client-side)
- `--format json|table|plain` — default `json`

### Fetch full job detail

```bash
bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts detail <refnr> [--format json|plain]
```

`refnr` is the job's reference number from `search` results (e.g. `12811-2300109-S`). Returns
the full description, contract type (`vertragsdauer`), entry date, and (where available) a
direct application URL.

## Usage examples

```bash
# Werkstudent Controlling roles in Köln
bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table

# Same, but only postings from the last 14 days
bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt am Main" --jobage 14 --format table

# Broader Controlling net within 25km of Köln, part-time only
bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts search -q "Controlling" -l "Köln" --radius 25 --parttime --format table

# Full details for a specific posting
bun run .agents/skills/arbeitsagentur-search/cli/src/cli.ts detail 12811-2300109-S --format plain
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, passing IDs to `detail` |
| `table` | Quick human-readable scanning |
| `plain` | Reading a single job's full detail (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- Data is from `rest.arbeitsagentur.de/jobboerse/jobsuche-service` (search: `pc/v6/jobs`, detail: `pc/v4/jobdetails/<encoded refnr>`). Authentication is a single public, well-known `X-API-Key` value (`jobboerse-jobsuche`) - there is no registration or personal credential involved.
- The detail endpoint expects the **standard-Base64 encoding of the refnr**, not the raw refnr. The CLI does this encoding automatically; you can pass either the raw refnr or an already-encoded ID to `detail`.
- Some postings are cross-posted from third-party boards (`externeUrl`/`externeURL` in the raw response) - the CLI's `url` field always points at the stable Bundesagentur detail page (`arbeitsagentur.de/jobsuche/jobdetail/<refnr>`) regardless, and `detail`'s `applyUrl` surfaces the external apply link when the posting has one.
- No rate-limit issues observed in testing, but the CLI still backs off on 429/5xx like the other skills in this repo.
- Result location strings combine postal code + city (e.g. `"50667 Köln"`) since that's how the API returns `arbeitsort`.
