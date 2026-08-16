// Data source: Bundesagentur für Arbeit's public Jobsuche REST API
// (rest.arbeitsagentur.de/jobboerse/jobsuche-service). No account/registration
// required - authentication is a single well-known static client key.
// robots.txt on arbeitsagentur.de is fully open (Allow: /), and this is an
// official government API, not scraped HTML, so there are no ToS concerns.

export const SEARCH_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs"
export const DETAIL_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobdetails"
export const API_KEY = "jobboerse-jobsuche"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

/** Fetch JSON with exponential backoff on 429/5xx. Returns null on a 404. */
export async function apiFetch<T>(url: string): Promise<T | null> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Accept: "application/json",
        "X-API-Key": API_KEY,
      },
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
    if (response.status === 404) return null
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return (await response.json()) as T
  }
  throw new Error("Request failed after max retries")
}

/** The detail endpoint expects the standard-Base64 encoding of the search result's refnr. */
export function encodeRefnr(refnr: string): string {
  return Buffer.from(refnr, "utf-8").toString("base64")
}

/** Reverse of encodeRefnr, so `detail` also accepts an already-encoded ID or a raw refnr. */
export function looksBase64(id: string): boolean {
  return /^[A-Za-z0-9+/]+=*$/.test(id) && !id.includes("-")
}

export interface RawJobLocation {
  plz?: string | null
  ort?: string | null
  region?: string | null
  land?: string | null
}

export interface RawJobCard {
  stellenangebotsTitel: string
  referenznummer: string
  firma?: string | null
  stellenlokationen?: Array<{ adresse?: RawJobLocation | null }>
  veroeffentlichungszeitraum?: { von?: string | null }
  externeURL?: string | null
}

export interface RawSearchResponse {
  ergebnisliste?: RawJobCard[]
  maxErgebnisse?: number
  page?: number
  size?: number
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

/** The API returns some titles/employers with literal HTML entities (e.g. "&amp;"). */
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

function formatLocation(loc?: RawJobLocation | null): string | null {
  if (!loc) return null
  const parts = [loc.plz, loc.ort].filter(Boolean)
  return parts.length > 0 ? parts.join(" ") : (loc.region ? decodeHtmlEntities(loc.region) : null)
}

export function detailPageUrl(refnr: string): string {
  return `https://www.arbeitsagentur.de/jobsuche/jobdetail/${encodeURIComponent(refnr)}`
}

export function normalizeCard(raw: RawJobCard): JobCard {
  return {
    id: raw.referenznummer,
    title: decodeHtmlEntities(raw.stellenangebotsTitel),
    company: raw.firma ? decodeHtmlEntities(raw.firma) : null,
    location: formatLocation(raw.stellenlokationen?.[0]?.adresse),
    date: raw.veroeffentlichungszeitraum?.von ?? null,
    url: detailPageUrl(raw.referenznummer),
  }
}

export interface RawJobDetail {
  stellenangebotsTitel: string
  referenznummer: string
  firma?: string | null
  stellenangebotsBeschreibung?: string | null
  stellenlokationen?: Array<{ adresse?: RawJobLocation & { strasse?: string | null } }>
  veroeffentlichungszeitraum?: { von?: string | null }
  eintrittszeitraum?: { von?: string | null }
  vertragsdauer?: string | null
  arbeitszeitVollzeit?: boolean
  externeURL?: string | null
}

export interface JobDetail extends JobCard {
  description: string | null
  employmentType: string | null
  entryDate: string | null
  applyUrl: string | null
}

export function normalizeDetail(raw: RawJobDetail): JobDetail {
  const loc = raw.stellenlokationen?.[0]?.adresse ?? null
  return {
    id: raw.referenznummer,
    title: decodeHtmlEntities(raw.stellenangebotsTitel),
    company: raw.firma ? decodeHtmlEntities(raw.firma) : null,
    location: formatLocation(loc),
    date: raw.veroeffentlichungszeitraum?.von ?? null,
    url: detailPageUrl(raw.referenznummer),
    description: raw.stellenangebotsBeschreibung ? decodeHtmlEntities(raw.stellenangebotsBeschreibung) : null,
    employmentType: raw.vertragsdauer ?? null,
    entryDate: raw.eintrittszeitraum?.von ?? null,
    applyUrl: raw.externeURL ?? null,
  }
}
