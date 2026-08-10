// Data source: Absolventa's public job-listing pages (www.absolventa.de/jobs and
// /stellenangebote/<id>-p-<slug>). robots.txt only blocks one unrelated abuse-report
// path, so this is not a ToS-restricted scrape like some of the other portal skills
// in this repo. Search results are parsed from the rendered HTML (chunked by job
// "teaser" card); job detail is parsed from the page's embedded schema.org
// JobPosting JSON-LD block, which is clean structured data rather than scraped markup.

export const BASE_URL = "https://www.absolventa.de"
export const SEARCH_URL = `${BASE_URL}/jobs`

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

export interface FetchResult {
  html: string
  finalUrl: string
}

/** Fetch HTML with exponential backoff on 429/5xx. Returns "" on a 404. Follows redirects. */
export async function htmlFetch(url: string): Promise<FetchResult> {
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
      signal: AbortSignal.timeout(15000),
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
    if (response.status === 404) return { html: "", finalUrl: response.url }
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return { html: await response.text(), finalUrl: response.url }
  }
  throw new Error("Request failed after max retries")
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  date: string | null
  url: string
}

function numericEntity(cp: number): string {
  return cp >= 0 && cp <= 0x10ffff ? String.fromCodePoint(cp) : ""
}

export function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
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
 * Parse job "teaser" cards out of a /jobs (or /jobs/channel/<x>, /werkstudentenjobs)
 * results page. Each card is split on its id="teaser_job_offer_<id>" marker and
 * parsed independently so one malformed card cannot break the rest.
 */
export function parseJobCards(html: string): JobCard[] {
  const results: JobCard[] = []
  const chunks = html.split(/id="teaser_job_offer_/).slice(1)

  for (const chunk of chunks) {
    const idMatch = chunk.match(/^(\d+)/)
    if (!idMatch) continue
    const id = idMatch[1]

    // The href lives in the same opening <a> tag the split point falls inside.
    const tagEnd = chunk.indexOf(">")
    const openTag = tagEnd >= 0 ? chunk.slice(0, tagEnd) : chunk
    const hrefMatch = openTag.match(/href="([^"]+)"/)
    if (!hrefMatch) continue
    const url = BASE_URL + hrefMatch[1]

    const h2 = chunk.match(/<h2[^>]*>([\s\S]*?)<\/h2>/i)
    if (!h2) continue
    const title = clean(h2[1])

    const companyMatch = chunk.match(
      /<span class="text-secondary break-words hyphens-auto leading-\[160%\] tracking-tight text-\[0\.875rem\]">([\s\S]*?)<\/span>/i,
    )
    const company = companyMatch ? clean(companyMatch[1]) || null : null

    let location: string | null = null
    const locIdx = chunk.indexOf("Standort</title>")
    if (locIdx !== -1) {
      const liEnd = chunk.indexOf("</li>", locIdx)
      if (liEnd !== -1) {
        location = clean(chunk.slice(locIdx + "Standort</title>".length, liEnd)) || null
      }
    }

    results.push({ id, title, company, location, date: null, url })
  }

  return results
}

export interface JobDetail extends JobCard {
  description: string | null
  employmentType: string | null
  industry: string | null
  applyUrl: string | null
}

/** Find and parse the schema.org JobPosting block among a page's JSON-LD scripts. */
export function extractJobPostingJsonLd(html: string): Record<string, unknown> | null {
  const scriptRe = /<script type="application\/ld\+json">([\s\S]*?)<\/script>/gi
  let m: RegExpExecArray | null
  while ((m = scriptRe.exec(html)) !== null) {
    try {
      const parsed = JSON.parse(m[1].trim())
      if (parsed && parsed["@type"] === "JobPosting") return parsed
    } catch {
      continue
    }
  }
  return null
}

/** The description field is HTML, itself HTML-entity-encoded inside the JSON string. */
export function richTextToPlain(raw: string): string {
  const unescaped = decodeHtmlEntities(raw)
  const withBreaks = unescaped
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|li|ul|ol|div|h\d)>/gi, "\n")
  const stripped = withBreaks.replace(/<[^>]+>/g, "")
  const decoded = decodeHtmlEntities(stripped)
  return decoded.replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim()
}

export function normalizeDetail(raw: Record<string, any>, canonicalUrl: string): JobDetail {
  const idMatch = canonicalUrl.match(/\/stellenangebote\/(\d+)/)
  const address = raw.jobLocation?.[0]?.address
  const location = address ? [address.postalCode, address.addressLocality].filter(Boolean).join(" ") || null : null
  const employmentType = typeof raw.employmentType === "string" ? raw.employmentType.replace(/[[\]]/g, "") : null

  return {
    id: idMatch ? idMatch[1] : canonicalUrl,
    title: raw.title ?? "(untitled)",
    company: raw.hiringOrganization?.name ?? null,
    location,
    date: raw.datePosted ?? null,
    url: canonicalUrl,
    description: raw.description ? richTextToPlain(raw.description) : null,
    employmentType,
    industry: raw.industry ?? null,
    applyUrl: `${canonicalUrl.replace(/\/$/, "")}/apply`,
  }
}
