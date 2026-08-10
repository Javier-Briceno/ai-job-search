// Data source: Workwise's public JSON APIs, reverse-engineered from a real browser
// network capture (the site itself is a client-rendered Next.js SPA with no data in
// its server-rendered HTML - see url-reference.md for how these were found).
//
// Search: POST https://search.workwise.io/v2/searches?size=14&withMatchings=true
// Detail: GET  https://candidates.workwise.io/v2/enquiries/<id>
//
// Both were verified to work with no cookies/session and a plain browser User-Agent.

export const SEARCH_URL = "https://search.workwise.io/v2/searches"
export const DETAIL_URL = "https://candidates.workwise.io/v2/enquiries"
export const SITE_URL = "https://www.workwise.io"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

/** Fetch JSON with exponential backoff on 429/5xx. Returns null on a 404. */
async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T | null> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        "User-Agent": UA,
        Origin: SITE_URL,
        Referer: `${SITE_URL}/`,
        ...(init?.headers ?? {}),
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

export async function postJson<T>(url: string, body: unknown): Promise<T | null> {
  return jsonFetch<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
}

export async function getJson<T>(url: string): Promise<T | null> {
  return jsonFetch<T>(url)
}

function stripHtml(html: string): string {
  return html
    .replace(/<\s*br\s*\/?>/gi, "\n")
    .replace(/<\/(p|li|ul|ol|div|h\d)>/gi, "\n")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
}

export interface RawLocation {
  city?: string | null
  zip?: string | null
  state?: string | null
  country?: string | null
}

export interface RawCompany {
  name?: string | null
}

export interface RawEnquiryType {
  id: number
  name: string
  shortName?: string
}

export interface RawEnquiry {
  id: number
  name: string
  shortDescription?: string | null
  company?: RawCompany | null
  locationLevels?: RawLocation[] | null
  hoursStart?: number | null
  hoursEnd?: number | null
  minSalary?: string | null
  maxSalary?: string | null
  type?: RawEnquiryType | null
  slug?: string | null
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  location: string | null
  date: string | null
  url: string
  hoursPerWeek: string | null
  salaryPerHour: string | null
}

function formatLocation(loc?: RawLocation[] | null): string | null {
  const l = loc?.[0]
  if (!l) return null
  const parts = [l.zip, l.city].filter(Boolean)
  return parts.length > 0 ? parts.join(" ") : (l.city ?? null)
}

function formatHours(start?: number | null, end?: number | null): string | null {
  if (start == null && end == null) return null
  if (start != null && end != null && start === end) return `${start}h/Woche`
  return `${start ?? "?"}-${end ?? "?"}h/Woche`
}

function formatSalary(min?: string | null, max?: string | null): string | null {
  if (!min && !max) return null
  if (min && max && min === max) return `${min} EUR/h`
  return `${min ?? "?"}-${max ?? "?"} EUR/h`
}

export function detailPageUrl(id: string | number): string {
  return `${SITE_URL}/jobsuche?id=${id}`
}

export function normalizeCard(raw: RawEnquiry): JobCard {
  return {
    id: String(raw.id),
    title: raw.name,
    company: raw.company?.name ?? null,
    location: formatLocation(raw.locationLevels),
    date: null,
    url: detailPageUrl(raw.id),
    hoursPerWeek: formatHours(raw.hoursStart, raw.hoursEnd),
    salaryPerHour: formatSalary(raw.minSalary, raw.maxSalary),
  }
}

export interface RawDescriptionPart {
  title?: string | null
  text?: string | null
}

export interface RawDetail extends RawEnquiry {
  description?: string | null
  descriptionParts?: RawDescriptionPart[] | null
  firstPublished?: string | null
  lastPublished?: string | null
}

export interface JobDetail extends JobCard {
  description: string | null
  firstPublished: string | null
}

export function normalizeDetail(raw: RawDetail): JobDetail {
  const card = normalizeCard(raw)

  let description: string | null = null
  if (raw.descriptionParts && raw.descriptionParts.length > 0) {
    description = raw.descriptionParts
      .map((p) => [p.title, p.text ? stripHtml(p.text) : null].filter(Boolean).join("\n"))
      .join("\n\n")
  } else if (raw.description) {
    description = stripHtml(raw.description)
  }

  return {
    ...card,
    description,
    firstPublished: raw.firstPublished ?? null,
  }
}
