# Workwise API Reference

## How these endpoints were found

Workwise's `workwise.io/jobsuche` page is a client-rendered Next.js SPA - fetching it
directly returns only shell HTML with untranslated i18n placeholders (e.g. a page
`<title>` of literally `"footer.heartAlt"`), no job data. Static analysis of the
JS bundles (`static.workwise.io/candidates/_next/static/chunks/*.js`) didn't reveal
the API shape either - blind guesses at `api.workwise.io/jobs`, `/v1/jobs`, `/v2/jobs`,
`/jobs/search`, and `/graphql` all returned a blanket `405 Method Not Allowed` with no
`Allow` header, which isn't informative enough to reverse-engineer from.

**These endpoints were instead identified from a real browser DevTools Network-tab
capture** (the user ran a search on the live site and copied the relevant requests as
`curl` commands), then verified live with the session cookies stripped out entirely -
both work with no cookies/session and a plain browser User-Agent.

## Search

```
POST https://search.workwise.io/v2/searches?size=<n>&withMatchings=true
Content-Type: application/json
```

Body (all fields other than `description` and `searchesEnquiryTypes` were left at the
defaults observed in the captured request - not individually re-verified, but the
whole shape works as-is):

```json
{
  "description": "<query text>",
  "end": null, "hoursEnd": null, "hoursStart": null,
  "languageLevels": [],
  "leadershipExperience": "does_not_matter",
  "locationLevels": [],
  "mobileWork": null,
  "occupations": [],
  "ongoing": true,
  "remoteWork": "does_not_matter",
  "salary": null, "salaryFlexible": true, "salaryType": null,
  "searchCompanyLevels": [], "searchCompanyTagLevels": [],
  "searchesEnquiryTypes": [{ "enquiryTypeId": 1 }],
  "start": null,
  "workExperience": "does_not_matter",
  "worldwide": false
}
```

`searchesEnquiryTypes` filters by employment type - `enquiryTypeId: 1` is confirmed
(the response's own `type.name` for id-1 results is `"Werkstudententätigkeit"`,
matching the German term for working-student roles). No other IDs were tested;
passing an empty array (or omitting the field) returns all employment types mixed
together, verified by checking that results returned this way include entries with
different `type` values.

**`locationLevels: []` in the request produces unfiltered results across all of
Germany** (verified: a query with no location filter returned jobs from München,
Karlsruhe, Frankfurt, Stuttgart, Regensburg, and Grünwald in a single response) - this
confirms location filtering requires actually populating `locationLevels` with a
structured object, not just a city name string. The real object shape (seen on a
result's own location) is:

```json
{ "city": "München", "zip": "80336", "state": "Bayern", "stateCode": "BY", "country": "Deutschland", "countryCode": "DE", "lat": 48.13, "lon": 11.57, "googlePlaceId": "ChIJ...", "limiter": "zip" }
```

Populating this correctly would need a places/geocoding autocomplete call this CLI
doesn't have access to (there is a sibling `query-suggestions?q=<text>` endpoint
observed in the same capture, but it returns job-title suggestions, not locations - no
equivalent location-suggestion endpoint was found in the capture).

### Response shape

```json
{
  "data": {
    "search": { "id": 218363313, "description": "...", "..." : "..." },
    "matchingResult": {
      "data": {
        "matchings": [
          { "enquiries": { "id": 125882, "name": "...", "shortDescription": "...", "hoursStart": 20, "hoursEnd": 20, "minSalary": "16.00", "maxSalary": "18.00", "locationLevels": [...], "company": { "name": "..." }, "type": { "id": 1, "name": "Werkstudententätigkeit" }, "..." : "..." } }
        ]
      }
    }
  }
}
```

`search.id` is a **new** search record ID created by this very request (distinct from
any `parentId` you might pass) - the captured browser request included a `parentId`
referencing a *previous* search (implying the site chains searches as the user
refines their query), but this was verified unnecessary: omitting `parentId` entirely
still returns a fresh, valid search with real matches.

No `page`/`offset` parameter was observed anywhere in the capture - pagination beyond
the first `size` results is unverified.

## Detail

```
GET https://candidates.workwise.io/v2/enquiries/<id>
```

Returns the full posting under a top-level `data` key: `description` (a single HTML
blob) and `descriptionParts` (the same content pre-split into labeled sections like
`{"title": "Was erwartet dich?", "text": "<ul>...</ul>"}`) - `descriptionParts` is
preferred when present since it preserves the section structure. Also includes
`firstPublished`/`lastPublished` (ISO timestamps, absent from `search` results),
`company` (full profile including Kununu rating), and the same `hoursStart`/`hoursEnd`/
`minSalary`/`maxSalary`/`locationLevels` fields as a search result.

## Canonical job URL

There is no dedicated `/jobs/<slug>` page - the site's own browsing pattern (seen in
the capture's `Referer` header) is `https://www.workwise.io/jobsuche?search_id=<search
id>&id=<job id>&page=1`. Since `search_id` is session/request-specific and not needed
to view a job, this CLI builds a simpler, still-valid URL:
`https://www.workwise.io/jobsuche?id=<job id>`.

## Notes

- No authentication required for either endpoint.
- The CLI backs off on 429/5xx with the same exponential-backoff pattern as the other portal skills in this repo.
- A separate `/_next/data/<build-commit-hash>/de/jobsuche.json` route also exists (the Next.js page's own SSR data route) but was deliberately **not** used - the URL embeds a specific deployment's commit hash that changes on every Workwise redeploy, making it fragile. The two REST endpoints above are the stable foundation.
