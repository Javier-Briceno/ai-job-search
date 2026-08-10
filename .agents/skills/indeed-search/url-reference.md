# Indeed URL Reference

Public HTML pages of Indeed (default market: Germany, `de.indeed.com`).

## ⚠️ robots.txt

Indeed's `robots.txt` has three relevant blocks:

1. A generic `User-agent: *` block disallowing `/viewjob?` among many other paths.
2. A block naming specific well-behaved crawlers (`Googlebot`, `Bingbot`, etc.) with similar disallows.
3. **A block naming AI crawlers specifically** - `GPTBot`, `CCBot`, `anthropic-ai`, `ClaudeBot`, `DeepSeekBot`, `GrokBot`, `Diffbot`, `AI2Bot`, and others - disallowing `/jobs` (search) and `/viewjob` (detail), among other paths.

Block 3 is a deliberate, specific exclusion of AI agents, not a generic catch-all. This
skill was built anyway at explicit user request, for personal use only.

## Technical finding: Bun's `fetch()` is blocked; `curl` is not

During development, Bun's native `fetch()` against `https://de.indeed.com/jobs?...`
returned `403 Forbidden` **even with a full browser-matched header set**:
`User-Agent`, `Accept`, `Accept-Language`, `Accept-Encoding`, `sec-ch-ua`,
`sec-ch-ua-mobile`, `sec-ch-ua-platform`, `Upgrade-Insecure-Requests`, and all three
`Sec-Fetch-*` headers. The identical request via plain `curl` (same `User-Agent`,
`Accept`, `Accept-Language`) succeeded with `200`.

This strongly suggests **TLS/client fingerprinting** (e.g. JA3-style detection, common
with Indeed's anti-bot vendor) rather than anything inspectable/fixable at the HTTP
header level - the block is on the connection's low-level signature, not its declared
identity. Because of this, `helpers.ts` shells out to `curl` as a subprocess instead of
using `fetch()`, unlike every other portal skill in this repo. This makes `curl` a
required system dependency for this skill specifically.

## Search

```
GET https://de.indeed.com/jobs?q=<query>&l=<location>&start=<offset>
```

| Param | Meaning | Example |
|-------|---------|---------|
| `q` | Keywords | `Werkstudent Controlling` |
| `l` | Location | `Köln` |
| `start` | Pagination offset (15/page) | `0`, `15`, `30`, ... |

The response HTML embeds a JS assignment:

```js
window.mosaic.providerData["mosaic-provider-jobcards"] = { metaData: { mosaicProviderJobCardsModel: { results: [ { jobkey, displayTitle, company, formattedLocation, formattedRelativeTime, snippet, ... }, ... ] } } }
```

This is extracted by brace-matching (respecting string literals) rather than regex
field-scraping, since the object is deeply nested and its exact key order/whitespace is
not stable. Relevant per-result fields:

| Field | Meaning |
|-------|---------|
| `jobkey` | Stable per-posting ID, used to build the detail URL and passed to `detail` |
| `displayTitle` | Job title |
| `company` | Employer name |
| `formattedLocation` | Location as shown on the card, e.g. `"50670 Köln"` |
| `formattedRelativeTime` | Relative posting age in German, e.g. `"vor 19 Tagen"` - **not an ISO date** |
| `snippet` | Short HTML bullet-point preview of the description - the CLI strips tags and decodes entities |

The `link` field present on each raw result is a tracked redirect
(`/pagead/clk?...` for sponsored results, `/rc/clk?jk=...` for organic ones) and is
**not used** - the CLI instead builds a stable canonical URL itself:
`https://de.indeed.com/viewjob?jk=<jobkey>`.

## Detail

```
GET https://de.indeed.com/viewjob?jk=<jobkey>
```

**Actively blocked, verified during development.** Depending on client/session this
returns either:
- A bare `403` (observed via `curl` in later testing), or
- A `200` response with the page title `Security Check - Indeed.com` (a bot-check
  interstitial, observed via Bun's `fetch()` earlier in testing)

Both are treated as `BLOCKED` by `isBlockedPage()` / the `detail` command's status
check. This is an active technical defense, not a robots.txt courtesy - there is no
header or client change found during investigation that reliably gets past it. Do not
attempt to "fix" this by adding more headers or retry logic; it was already tried.

## Notes

- No authentication required for `search`.
- The CLI backs off on 429/5xx with the same exponential-backoff pattern as the other
  portal skills in this repo, just via `curl` instead of `fetch()`.
- Other Indeed country domains follow the same `q`/`l`/`start` pattern and almost
  certainly embed the same `mosaic-provider-jobcards` structure, but only
  `de.indeed.com` was verified live.
