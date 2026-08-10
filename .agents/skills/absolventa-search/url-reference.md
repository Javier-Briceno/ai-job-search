# Absolventa URL Reference

Public HTML pages of Absolventa, a German student/working-student/graduate job board.
`robots.txt` only disallows `/p/formular-zur-meldung-von-rechtswidrigen-inhalten` (an
abuse-report form) - no ToS restriction on the paths this skill uses.

## Search

```
GET https://www.absolventa.de/jobs
```

Verified, reliable query params (both repeatable arrays):

| Param | Meaning | Example |
|-------|---------|---------|
| `fields[]` | Field/industry category slug | `finance`, `controlling`, `rechnungswesen` |
| `positions[]` | Job type | `werkstudent`, `praktikum`, `trainee`, `festanstellung`, `abschlussarbeit` |
| `page` | Page number | `2` |

Combining `fields[]` and `positions[]` correctly narrows results (verified live: `fields[]=finance&positions[]=werkstudent` returns only Werkstudent postings tagged Finance).

**Not reliable, deliberately not used by this CLI:**
- `text=<keyword>` - canonicalizes server-side. A single keyword that matches a known
  channel redirects (302) to `/jobs/channel/<slug>` (e.g. `text=Controlling` →
  `/jobs/channel/controlling`). A keyword that matches a known landing page redirects
  elsewhere (e.g. `text=Werkstudent` → `/werkstudentenjobs`). Multi-word or unrecognized
  text returns 200 but with an empty or unfiltered result set. There is no way to combine
  freeform text reliably with `positions[]`/`fields[]` via a single request.
- `location=<text>` - redirects to a different results page, and in testing the redirect's
  `Location` header corrupted a non-ASCII character (`Köln` became `K%EF%BF%BD ln`,
  i.e. a UTF-8 replacement character). The site's location box normally resolves through
  a JS autocomplete widget to a specific place ID, which raw query text does not replicate.
- `/jobs/channel/<slug>?positions[]=werkstudent` - the channel path variant of the
  position filter is **cosmetically broken**: the checkbox renders as checked and the
  request succeeds, but the returned jobs are not actually filtered by position (verified
  by checking a returned job's own `employmentType` in its JobPosting JSON-LD, which
  did not match the requested filter). Use `fields[]` on the plain `/jobs` path instead,
  which was verified to filter correctly.

### Response shape

Each result is an `<li>` "teaser" card whose opening `<a>` tag has `id="teaser_job_offer_<id>"`
and `href="/stellenangebote/<id>-p-<slug>"`. Within the card:
- Title: first `<h2 class="text-secondary ...">` (there are two duplicate `<h2>`s for
  responsive layout - both contain identical text, so the CLI takes the first)
- Company: the `<span>` immediately following the title with the class combination
  `text-secondary break-words hyphens-auto leading-[160%] tracking-tight text-[0.875rem]`
- Location: inside a `<li>` containing an SVG whose `<title>` reads "Standort", followed
  by `<span>PLZ <span>City</span></span>`
- No posting date is shown on the search-results card - `date` is always `null` from
  `search`; use `detail` for the `datePosted` field

### Example category slugs (`fields[]`)

Full alphabetical list has ~90 entries; the ones most relevant to finance/Controlling
searches: `controlling`, `finance`, `rechnungswesen`, `buchhaltung`, `bankwesen`,
`versicherungswesen`, `steuerwesen`, `wirtschaftspruefung`, `sap-erp`,
`business-development`, `consulting`, `management`. Others cover engineering, IT,
marketing, healthcare, and every other field the portal lists (e.g. `it`,
`softwareentwicklung`, `marketing`, `logistik`, `human-resources`, `jura-rechtswesen`).

## Detail

```
GET https://www.absolventa.de/stellenangebote/<id>-p-<slug>
```

A bare numeric ID (`GET /stellenangebote/<id>`) 301-redirects to the full slugged URL -
the CLI's `fetch` follows this automatically and uses the resolved URL as the canonical
`url` field.

The page embeds several `<script type="application/ld+json">` blocks; the one with
`"@type": "JobPosting"` (schema.org) has the full structured data:

```json
{
  "@type": "JobPosting",
  "title": "...",
  "datePosted": "2026-07-29",
  "validThrough": "2026-08-07T23:59:59+02:00",
  "employmentType": "[OTHER]",
  "industry": "finance",
  "description": "&lt;p&gt;... HTML, itself HTML-entity-encoded ...&lt;/p&gt;",
  "jobLocation": [{ "address": { "postalCode": "...", "addressLocality": "...", "streetAddress": "..." } }],
  "hiringOrganization": { "name": "...", "url": "...", "logo": "..." }
}
```

Notes on parsing this block:
- `employmentType` comes wrapped in literal brackets (e.g. `"[OTHER]"`) - the CLI strips them.
- `description` is HTML markup that has itself been HTML-entity-encoded before being placed
  in the JSON string (so the raw JSON value contains literal `&lt;p&gt;` text, not `<p>`).
  Decoding entities once turns this into real HTML tags; converting `<br>`/`<li>`/`<p>`
  etc. to newlines and stripping remaining tags, then decoding entities a second time
  (for things like `&amp;nbsp;` which only becomes real `&nbsp;` after the first pass),
  produces clean plain text.
- There is no direct external application URL in the JSON-LD - applications happen on
  Absolventa itself at `<canonical detail url>/apply` (verified against the page's own
  "Jetzt bewerben" button).

## Notes

- No authentication required for any of the above.
- No rate limiting encountered during testing; the CLI still backs off on 429/5xx defensively.
- Company logos are served from `uno-production.imgix.net`, not used by this CLI.
