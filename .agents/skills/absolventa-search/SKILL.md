---
name: absolventa-search
version: 1.0.0
description: >
  Use this skill for student, working-student (Werkstudent), internship
  (Praktikum), and graduate-entry job searches in Germany via Absolventa, a job
  board specifically targeting students and recent graduates. Trigger phrases:
  absolventa, werkstudent jobs, werkstudentin, praktikum jobs germany, student
  job germany, graduate jobs germany, internship germany, trainee jobs germany,
  einstiegsjobs, studentenjobs, abschlussarbeit jobs, werkstudent controlling,
  werkstudent finance.
context: fork
enabled: true  # set to false to keep this portal installed but have /scrape skip it
allowed-tools: Bash(bun run .agents/skills/absolventa-search/cli/src/cli.ts *)
---

# Absolventa-Search Skill

Search live job listings from Absolventa, a German job board specifically for students,
working students, interns, and recent graduates. **Zero runtime dependencies** - it runs
with just `bun`. `absolventa.de`'s `robots.txt` only blocks one unrelated abuse-report
path, so unlike some of the other portal skills in this repo there are no ToS concerns.

## When to use this skill

- Search for Werkstudent, Praktikum, Trainee, or entry-level (`Festanstellung`) roles in Germany
- Filter by field/industry (e.g. Controlling, Finance, IT, Marketing)
- Get the full description, employer, and application link for a specific posting

## Commands

### Search job listings

```bash
bun run .agents/skills/absolventa-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--category <slug>` — field/industry. Examples relevant to finance/Controlling searches: `controlling`, `finance`, `rechnungswesen`, `buchhaltung`, `bankwesen`, `versicherungswesen`, `steuerwesen`, `sap-erp`, `wirtschaftspruefung`. See `url-reference.md` for the full list of ~90 category slugs.
- `--position <type>` — job type: `werkstudent` | `praktikum` | `trainee` | `festanstellung` | `abschlussarbeit`
- `--query <text>` / `-q <text>` — best-effort client-side title filter (see Notes below - **not** sent to the portal)
- `--page <n>` — 1-indexed page
- `--limit <n>` / `-n <n>` — cap results emitted (client-side)
- `--format json|table|plain` — default `json`

### Fetch full job detail

```bash
bun run .agents/skills/absolventa-search/cli/src/cli.ts detail <id|url> [--format json|plain]
```

`id` is the numeric job ID from `search` results (e.g. `12720125`). You may also pass the
full `/stellenangebote/<id>-p-<slug>` path or URL. Returns the full description, employer,
location, publish date, and a direct application link (`.../apply`).

## Usage examples

```bash
# Werkstudent roles in Controlling
bun run .agents/skills/absolventa-search/cli/src/cli.ts search --category controlling --position werkstudent --format table

# Werkstudent roles in Finance, further narrowed by title
bun run .agents/skills/absolventa-search/cli/src/cli.ts search --category finance --position werkstudent -q "Controlling" --format table

# All Werkstudent roles across every field (small, curated pool)
bun run .agents/skills/absolventa-search/cli/src/cli.ts search --position werkstudent --format table

# Full details for a specific posting
bun run .agents/skills/absolventa-search/cli/src/cli.ts detail 12720125 --format plain
```

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, passing IDs to `detail` |
| `table` | Quick human-readable scanning |
| `plain` | Reading a single job's full detail (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

## Notes

- **`--category` and `--position` are reliable, portal-side filters** (`fields[]` and `positions[]` on `absolventa.de/jobs`), verified live - combining them (e.g. `finance` + `werkstudent`) correctly narrows results.
- **`--query` is a client-side substring match on the title, not a portal query.** Absolventa's own free-text search box canonicalizes recognized single keywords into a "channel" page redirect (e.g. `text=Controlling` → `/jobs/channel/controlling`) and silently returns zero/unfiltered results for multi-word or unrecognized queries. Rather than rely on that unpredictable behavior, `--query` filters the already-fetched result titles locally.
- **Location filtering is not supported.** The portal's location box requires a JS-resolved place ID; passing raw place text (e.g. `location=Köln`) redirects to a different results page and in testing corrupted the umlaut in the redirect. Each result's `location` field (from the portal itself) still shows city/postal code, so location can be checked per-result instead.
- Job IDs are numeric (e.g. `12720125`); a bare ID 301-redirects to the full slugged detail URL, which the CLI follows automatically.
- `detail` parses the page's embedded schema.org `JobPosting` JSON-LD block rather than scraping visible markup - this is clean structured data, not fragile HTML scraping, for the detail command specifically. `search` results are still parsed from HTML job-teaser cards since no equivalent structured list exists for search.
