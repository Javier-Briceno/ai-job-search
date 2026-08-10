# Stepstone URL Reference

Public HTML pages of Stepstone (stepstone.de), Germany's largest general job board.

## ⚠️ robots.txt

Stepstone's `robots.txt` is unusually granular and actively maintained (each rule
carries an edit-date comment, e.g. `# 11/02/26 JM`). Two entries added within the last
few months are directly relevant:

```
Disallow: /search-results
Disallow: /search-results/*
...
Disallow: /listing
Disallow: /listing/*
```

These look like the site's current primary search-results and job-detail surface being
actively closed off to crawlers. Separately, the general `/jobs/*` rule is narrow:

```
Disallow: /jobs/*?*
Allow: /jobs/*?q=*
```

i.e. `/jobs/*` with **any** query string is disallowed **except** one whose query
string is exactly `?q=...`. A bare path with no query string at all - `/jobs/<keyword-slug>/in-<city-slug>` -
is not matched by either rule and remains allowed. This skill uses exactly that path
for `search`. **Adding `?page=N` for pagination does technically fall outside the
narrow `?q=*` allowance** - this is a further, smaller extension of the same
already-granted personal-use exception, not a separately-verified-safe pattern.

This skill (search only, using the path above) was built at explicit user request for
**personal use only**, given the wider signal that Stepstone is actively narrowing what
it wants crawled.

## Search

```
GET https://www.stepstone.de/jobs/<keyword-slug>/in-<city-slug>[?page=<n>]
```

Slugs follow Stepstone's own German-locale scheme: lowercase, spaces → hyphens,
`ä→ae`, `ö→oe`, `ü→ue`, `ß→ss` (verified against the site's own canonical URLs, e.g.
searching "Köln" resolves to `in-koeln`). `helpers.ts`'s `slugify()` implements this.

No JSON-LD job list is embedded (only `WebPage`/`BreadcrumbList`/`FAQPage` SEO
metadata) - results are parsed from HTML job "cards". Each card is a container with
`data-testid="job-item"` (note the closing quote - this string does **not** appear as
a substring of `data-testid="job-item-title"` etc., since those continue with `-title`
rather than `"`, so splitting on it doesn't false-match sub-elements). Within a card:

| Field | Marker | Notes |
|-------|--------|-------|
| id | `href="/stellenangebote--...--<id>-inline.html"` | Numeric ID at the end of the slug |
| title | `data-at="job-item-title"` | |
| company | `data-at="job-item-company-name"` | |
| location | `data-at="job-item-location"` | |
| date | `data-at="job-item-timeago"` | Relative German text, e.g. `"vor 16 Stunden"` - **not an ISO date** |

### Parsing pitfalls (both found and fixed during development)

1. **Inline `<style data-emotion="...">` blocks are pervasive** (Stepstone uses
   CSS-in-JS) and carry no visible text, but massively inflate the apparent distance
   between a `data-at="..."` marker and its real text if not removed first. `helpers.ts`
   strips all `<style>...</style>` blocks from the whole page once, up front, before
   splitting into cards.
2. **A marker sits mid-attribute inside its own opening tag** (e.g.
   `<a ... data-at="job-item-title" tabindex="-1">`), so a capture window that starts
   immediately after the marker string picks up the tag's remaining attributes
   (` tabindex="-1">`) as if they were plain text - there's no matching `<` in that
   slice for a tag-strip regex to catch. Fix: skip forward to the next `>` before
   starting the capture window.
3. **The same problem in reverse at the far end**: a window that runs "up to the next
   `data-at="` occurrence" can end mid-tag (inside the *next* field's opening tag,
   before its own `data-at=` attribute appears), again leaking an unclosed tag
   fragment. Fix: trim the window back to the last complete `<` before the cutoff.

## Detail (actively blocked - do not retry these findings)

```
GET https://www.stepstone.de/stellenangebote--<slug>--<id>-inline.html
```

**Verified during development: both a direct `curl` request and Bun's `fetch()`
against real detail URLs hung and then had their TLS connection reset**
(`curl` exit 56 / `CURLE_RECV_ERROR` mid-renegotiation; `fetch()` timed out
entirely). This happened consistently across multiple attempts on different postings,
not once as a fluke, and lines up with the `/listing` robots.txt disallow above - this
looks like the same Akamai-fronted defense actively protecting the detail/listing
surface specifically, distinct from the more tolerant `/jobs/<keyword>/in-<city>`
search path. `detail` in this CLI uses a hard timeout (12s) and reports `BLOCKED`
rather than hanging indefinitely.

## Notes

- No authentication required for search.
- The CLI backs off on 429/5xx with the same exponential-backoff pattern as the other
  portal skills in this repo.
- Page size was not established (pagination via `?page=N` was confirmed to exist as a
  link target on the results page, but the per-page count wasn't measured).
