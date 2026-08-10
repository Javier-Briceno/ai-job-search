// Data source: Stepstone's public /jobs/<keyword-slug>/in-<city-slug> search-results
// pages (HTML, parsed via job-card markers - no structured JSON-LD job list is
// embedded). This URL form is the one path robots.txt still allows for /jobs/* without
// a query string (or with only ?q=... in the disallowed set) - see url-reference.md.
//
// Individual job detail pages (/stellenangebote--...-inline.html) are actively
// defended: both curl and Bun's fetch() were verified to hang/reset the TLS connection
// entirely (not even a clean HTTP error) against real detail URLs during development.
// `detail` therefore uses a hard timeout and reports this reliably rather than hanging
// or pretending to work - see url-reference.md for the verification.

export const BASE_URL = "https://www.stepstone.de"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

/** Fetch HTML with exponential backoff on 429/5xx. Returns "" on a 404. */
export async function htmlFetch(url: string, timeoutMs = 15000): Promise<string> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
      },
      redirect: "follow",
      signal: AbortSignal.timeout(timeoutMs),
    })
    if (response.status === 429 || response.status >= 500) {
      if (attempt === maxRetries) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`)
      }
      const jitter = Math.floor(Math.random() * 500)
      await new Promise((r) => setTimeout(r, delay + jitter))
      delay = Math.min(delay * 2, 8000)
      continue
    }
    if (response.status === 404) return ""
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return response.text()
  }
  throw new Error("Request failed after max retries")
}

/** German-locale slugify matching Stepstone's own URL scheme (ö→oe, spaces→hyphens, etc.). */
export function slugify(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

function numericEntity(cp: number): string {
  return cp >= 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : ""
}

function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#(\d+);/g, (_, dec) => numericEntity(parseInt(dec, 10)))
    .replace(/&#[xX]([0-9a-fA-F]+);/g, (_, hex) => numericEntity(parseInt(hex, 16)))
    .replace(/&nbsp;/g, " ")
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
}

function clean(html: string): string {
  return decodeHtmlEntities(stripTags(html))
}

/**
 * Extract the visible text between a `data-at="..."` marker and the next such marker.
 * The marker sits mid-attribute inside its element's opening tag, so this first skips
 * past that tag's closing `>` (otherwise the tag's remaining attributes leak in as
 * plain text - there's no matching `<` in the slice for the tag-strip regex to catch).
 * It also trims the window back to the last complete `<` before the next marker, for
 * the same reason on the far end (a slice ending mid-tag leaves an unclosed fragment).
 */
function extractField(chunk: string, marker: string): string | null {
  const idx = chunk.indexOf(marker)
  if (idx === -1) return null
  let start = idx + marker.length
  const tagEnd = chunk.indexOf(">", start)
  if (tagEnd !== -1) start = tagEnd + 1

  const nextMarkerIdx = chunk.indexOf('data-at="', start)
  let end = nextMarkerIdx === -1 ? chunk.length : nextMarkerIdx
  const lastOpenBracket = chunk.lastIndexOf("<", end)
  if (lastOpenBracket > start) end = lastOpenBracket

  return clean(chunk.slice(start, end)) || null
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  date: string | null
  url: string
}

/**
 * Parse job cards out of a /jobs/<keyword>/in-<city> results page. Cards are split on
 * `data-testid="job-item"` (the closing quote makes this distinct from
 * `data-testid="job-item-title"` and similar sub-element markers, so no false splits)
 * and parsed independently so one malformed card cannot break the rest.
 */
export function parseJobCards(rawHtml: string): JobCard[] {
  const results: JobCard[] = []
  // Stepstone's markup is heavy with inline emotion-CSS <style> blocks scattered
  // between and inside elements (CSS-in-JS). These carry no visible text but badly
  // inflate the distance between a data-at="..." marker and its real text, breaking
  // a naive "capture up to the next marker" window. Stripped once, up front.
  const html = rawHtml.replace(/<style[^>]*>[\s\S]*?<\/style>/g, "")
  const chunks = html.split('data-testid="job-item"').slice(1)

  for (const chunk of chunks) {
    const hrefMatch = chunk.match(/href="(\/stellenangebote--[^"]+)"/)
    if (!hrefMatch) continue
    const href = hrefMatch[1]
    const idMatch = href.match(/--(\d+)-inline\.html$/)
    if (!idMatch) continue
    const id = idMatch[1]

    const title = extractField(chunk, 'data-at="job-item-title"')
    if (!title) continue
    const company = extractField(chunk, 'data-at="job-item-company-name"')
    const location = extractField(chunk, 'data-at="job-item-location"')
    // Stepstone's own text, e.g. "vor 16 Stunden" / "vor 1 Woche" - not an ISO date.
    const date = extractField(chunk, 'data-at="job-item-timeago"')

    results.push({ id, title, company, location, date, url: BASE_URL + href })
  }

  return results
}
