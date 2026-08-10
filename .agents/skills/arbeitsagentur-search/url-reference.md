# Bundesagentur für Arbeit Jobsuche API Reference

Public, unauthenticated (beyond a static client key) REST API operated by the German
Federal Employment Agency. Official government data - `arbeitsagentur.de`'s `robots.txt`
is fully open (`Allow: /`), so this is not a ToS-restricted scrape like some of the other
portal skills in this repo.

## Authentication

Every request needs the header:

```
X-API-Key: jobboerse-jobsuche
```

This is a single, well-known static value used by the Bundesagentur's own public frontend
(`arbeitsagentur.de/jobsuche`) - not a personal or registered credential.

## Search

```
GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs
```

(A `pc/v6/jobs` variant also exists and is the API's currently "recommended" version per
third-party documentation, but returns a different, more deeply-nested response shape.
`pc/v4` was used here because it was directly verified end-to-end, including the detail
endpoint below, and returns the same substantive data.)

Query params:

| Param | Meaning | Example |
|-------|---------|---------|
| `was` | Free-text job title/keyword | `Werkstudent Controlling` |
| `wo` | Location - city, region, or postal code | `Köln`, `50667`, `Frankfurt am Main` |
| `umkreis` | Search radius in km around `wo` | `25` |
| `veroeffentlichtseit` | Only postings published within N days (0-100) | `14` |
| `arbeitszeit` | Work-time type | `vz` (full-time), `tz` (part-time), `snw` (shift/night/weekend), `ho` (home office), `mj` (Minijob) |
| `page` | 1-indexed page | `1` |
| `size` | Results per page | `25` |

Response shape (top-level `stellenangebote` array):

```json
{
  "stellenangebote": [
    {
      "beruf": "Betriebswirt/in (Hochschule) - Rechnungswesen und Controlling",
      "titel": "Werkstudent Controlling / Sales Controlling (m/w/d)",
      "refnr": "12811-2300109-S",
      "arbeitsort": { "plz": "51149", "ort": "Köln", "region": "Nordrhein-Westfalen", "land": "Deutschland" },
      "arbeitgeber": "plusserver GmbH",
      "aktuelleVeroeffentlichungsdatum": "2026-07-21",
      "externeUrl": "https://www.finest-jobs.com/stellenanzeige/..."
    }
  ],
  "maxErgebnisse": 10,
  "page": 1,
  "size": 25
}
```

`externeUrl` is only present when the posting is cross-posted from a third-party board;
absent for postings native to the Bundesagentur portal.

## Detail

```
GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails/<encodedRefnr>
```

`<encodedRefnr>` is the **standard-Base64 encoding of the search result's `refnr`**, e.g.
`refnr = "12811-2300109-S"` encodes to `MTI4MTEtMjMwMDEwOS1T`. This was verified against a
documented worked example (`10001-1002716922-S` → `MTAwMDEtMTAwMjcxNjkyMi1T`) and against a
live request.

Returns the full posting: `stellenangebotsTitel`, `stellenangebotsBeschreibung` (full
description, plain text with no HTML), `firma` (employer), `stellenlokationen[0].adresse`
(street/postal/city), `vertragsdauer` (`BEFRISTET`/`UNBEFRISTET`), `eintrittszeitraum.von`
(start date), and `externeURL` (direct application link, when present).

## Notes

- No authentication beyond the static `X-API-Key` shown above.
- Own frontend detail page (used as the CLI's stable `url` field, regardless of any
  external cross-posting): `https://www.arbeitsagentur.de/jobsuche/jobdetail/<refnr>`
  (raw refnr, not encoded, in this URL).
- A `403 "No match found for request"` from the `jobdetails` endpoint almost always means
  the refnr was not Base64-encoded (or was encoded incorrectly) - it is not an auth error.
- No rate limiting encountered during testing; the CLI still backs off on 429/5xx defensively.
