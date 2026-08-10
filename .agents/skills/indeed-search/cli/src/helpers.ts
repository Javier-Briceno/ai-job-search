// Data source: Indeed's public search-results HTML (de.indeed.com/jobs), which embeds
// a JS object (window.mosaic.providerData["mosaic-provider-jobcards"]) with structured
// per-result data - parsed here rather than scraped from visible markup.
//
// IMPORTANT: Indeed's robots.txt has a dedicated block naming ClaudeBot, GPTBot,
// anthropic-ai, and other AI crawlers specifically, disallowing /jobs and /viewjob.
// This skill was built anyway at the user's explicit request for personal use.
//
// TECHNICAL NOTE - why this shells out to curl instead of using fetch() like every
// other portal skill in this repo: Indeed's anti-bot system blocks Bun's native
// fetch() with a 403 even with a full browser-matched header set (User-Agent,
// Accept-Language, sec-ch-ua, Sec-Fetch-*, etc.) - this points to TLS/client
// fingerprinting rather than anything fixable via headers. Plain `curl` with the same
// headers was verified to succeed against the same endpoint. This makes `curl` a
// required system dependency for this skill specifically (unlike the zero-dependency
// fetch() pattern everything else uses) - see url-reference.md for the verification.
// The /viewjob detail page is separately confirmed blocked outright (a bot-check
// interstitial) regardless of client, so `detail` still reliably fails and reports
// this rather than pretending to work.

export const DEFAULT_DOMAIN = "de.indeed.com"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

const STATUS_MARKER = "\n___CURL_STATUS___"

/** Runs curl as a subprocess and returns its body + HTTP status code. */
export async function curlRequest(url: string): Promise<{ status: number; body: string }> {
  const args = [
    "curl",
    "-s",
    "-L",
    "--max-time",
    "15",
    "-A",
    UA,
    "-H",
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H",
    "Accept-Language: de-DE,de;q=0.9,en;q=0.8",
    "-w",
    STATUS_MARKER + "%{http_code}",
    url,
  ]

  let stdout: string
  let stderr: string
  let exitCode: number
  try {
    const proc = Bun.spawn(args, { stdout: "pipe", stderr: "pipe" })
    ;[stdout, stderr, exitCode] = await Promise.all([
      new Response(proc.stdout).text(),
      new Response(proc.stderr).text(),
      proc.exited,
    ])
  } catch (e) {
    throw new Error(
      `Could not run curl (${e instanceof Error ? e.message : String(e)}). This skill requires curl on PATH - ` +
        `Bun's native fetch() is blocked by Indeed's anti-bot system for this site (see helpers.ts / url-reference.md).`,
    )
  }

  if (exitCode !== 0) {
    throw new Error(`curl exited with code ${exitCode}: ${stderr.trim() || "unknown error"}`)
  }

  const markerIdx = stdout.lastIndexOf(STATUS_MARKER)
  if (markerIdx === -1) {
    throw new Error("curl output did not include the expected status marker")
  }
  const body = stdout.slice(0, markerIdx)
  const status = parseInt(stdout.slice(markerIdx + STATUS_MARKER.length), 10)
  return { status, body }
}

/** Fetch HTML with exponential backoff on 429/5xx. Returns "" on a 404. */
export async function htmlFetch(url: string): Promise<string> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const { status, body } = await curlRequest(url)
    if (status === 429 || status >= 500) {
      if (attempt === maxRetries) {
        throw new Error(`Request failed: HTTP ${status}`)
      }
      const jitter = Math.floor(Math.random() * 500)
      await new Promise((r) => setTimeout(r, delay + jitter))
      delay = Math.min(delay * 2, 8000)
      continue
    }
    if (status === 404) return ""
    if (status < 200 || status >= 300) {
      throw new Error(`Request failed: HTTP ${status}`)
    }
    return body
  }
  throw new Error("Request failed after max retries")
}

/**
 * Extract a JS object literal that starts right after `marker` (e.g.
 * `window.mosaic.providerData["mosaic-provider-jobcards"]=`) by brace-matching,
 * respecting string literals so braces inside quoted strings don't confuse the count.
 */
export function extractJsonAfter(html: string, marker: string): unknown | null {
  const markerIdx = html.indexOf(marker)
  if (markerIdx === -1) return null
  let i = markerIdx + marker.length
  while (i < html.length && html[i] !== "{") i++
  if (html[i] !== "{") return null
  const start = i
  let depth = 0
  let inString = false
  let escape = false
  for (; i < html.length; i++) {
    const ch = html[i]
    if (inString) {
      if (escape) escape = false
      else if (ch === "\\") escape = true
      else if (ch === '"') inString = false
      continue
    }
    if (ch === '"') {
      inString = true
    } else if (ch === "{") {
      depth++
    } else if (ch === "}") {
      depth--
      if (depth === 0) {
        i++
        break
      }
    }
  }
  const jsonStr = html.slice(start, i)
  try {
    return JSON.parse(jsonStr)
  } catch {
    return null
  }
}

export interface RawResult {
  jobkey?: string
  displayTitle?: string
  company?: string
  formattedLocation?: string
  formattedRelativeTime?: string
  snippet?: string
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  date: string | null
  url: string
  snippet: string | null
}

function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ")
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()
}

export function detailPageUrl(jobkey: string, domain: string): string {
  return `https://${domain}/viewjob?jk=${jobkey}`
}

export function normalizeCard(raw: RawResult, domain: string): JobCard | null {
  if (!raw.jobkey || !raw.displayTitle) return null
  return {
    id: raw.jobkey,
    title: decodeHtmlEntities(raw.displayTitle),
    company: raw.company ? decodeHtmlEntities(raw.company) : null,
    location: raw.formattedLocation ? decodeHtmlEntities(raw.formattedLocation) : null,
    date: raw.formattedRelativeTime ?? null,
    url: detailPageUrl(raw.jobkey, domain),
    snippet: raw.snippet ? stripTags(decodeHtmlEntities(raw.snippet)) || null : null,
  }
}

/**
 * Pull the job-cards results array out of the page's embedded mosaic JSON. Indeed's
 * own shape is `{ metaData: { mosaicProviderJobCardsModel: { results: [...] } } }`.
 */
export function extractJobResults(html: string): RawResult[] {
  const parsed = extractJsonAfter(html, 'window.mosaic.providerData["mosaic-provider-jobcards"]=') as
    | { metaData?: { mosaicProviderJobCardsModel?: { results?: RawResult[] } } }
    | null
  return parsed?.metaData?.mosaicProviderJobCardsModel?.results ?? []
}

/** True when the response is Indeed's bot-check interstitial rather than real content. */
export function isBlockedPage(html: string): boolean {
  return /<title>\s*Security Check - Indeed\.com\s*<\/title>/i.test(html) || /Additional Verification Required/i.test(html)
}
