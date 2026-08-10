import { SEARCH_URL, postJson, normalizeCard, writeError, type RawEnquiry, type JobCard } from "../helpers.js"

export interface SearchOpts {
  query: string
  enquiryTypeId?: number
  size: number
  limit?: number
  format: "json" | "table" | "plain"
}

interface SearchResponse {
  data: {
    matchingResult?: {
      data?: {
        matchings?: Array<{ enquiries: RawEnquiry }>
      }
    }
  }
}

/**
 * Body shape and defaults verified live against a real browser capture. `location`
 * filtering is deliberately not exposed - Workwise's search takes a structured
 * `locationLevels` object (city/zip/lat/lon/googlePlaceId), which needs a geocoding
 * lookup this CLI doesn't have access to (see url-reference.md, same class of problem
 * as absolventa-search's location field).
 */
function buildBody(opts: SearchOpts) {
  return {
    description: opts.query,
    end: null,
    hoursEnd: null,
    hoursStart: null,
    languageLevels: [],
    leadershipExperience: "does_not_matter",
    locationLevels: [],
    mobileWork: null,
    occupations: [],
    ongoing: true,
    remoteWork: "does_not_matter",
    salary: null,
    salaryFlexible: true,
    salaryType: null,
    searchCompanyLevels: [],
    searchCompanyTagLevels: [],
    searchesEnquiryTypes: opts.enquiryTypeId ? [{ enquiryTypeId: opts.enquiryTypeId }] : [],
    start: null,
    workExperience: "does_not_matter",
    worldwide: false,
  }
}

function renderTable(cards: JobCard[]): string {
  if (cards.length === 0) return "No results."
  const rows = cards.map((c) => {
    const title = (c.title || "").slice(0, 40).padEnd(40)
    const company = (c.company || "—").slice(0, 24).padEnd(24)
    const loc = (c.location || "—").slice(0, 18).padEnd(18)
    const hours = c.hoursPerWeek || "—"
    return `${c.id.padEnd(9)} ${title} ${company} ${loc} ${hours}`
  })
  const header = "ID".padEnd(9) + " " + "TITLE".padEnd(40) + " " + "COMPANY".padEnd(24) + " " + "LOCATION".padEnd(18) + " HOURS"
  return [header, "-".repeat(header.length), ...rows].join("\n")
}

export async function runSearch(opts: SearchOpts): Promise<number> {
  try {
    const url = `${SEARCH_URL}?size=${opts.size}&withMatchings=true`
    const data = await postJson<SearchResponse>(url, buildBody(opts))
    let cards = (data?.data.matchingResult?.data?.matchings ?? []).map((m) => normalizeCard(m.enquiries))
    if (opts.limit !== undefined && opts.limit >= 0) cards = cards.slice(0, opts.limit)

    if (opts.format === "table") {
      process.stdout.write(renderTable(cards) + "\n")
    } else if (opts.format === "plain") {
      process.stdout.write(
        cards
          .map(
            (c) =>
              `${c.title}\n  ${c.company || "—"} · ${c.location || "—"}${c.hoursPerWeek ? ` · ${c.hoursPerWeek}` : ""}${c.salaryPerHour ? ` · ${c.salaryPerHour}` : ""}\n  id: ${c.id}\n  ${c.url}`,
          )
          .join("\n\n") + "\n",
      )
    } else {
      process.stdout.write(JSON.stringify({ meta: { count: cards.length, size: opts.size }, results: cards }, null, 2) + "\n")
    }
    return 0
  } catch (e) {
    writeError(e instanceof Error ? e.message : String(e), "SEARCH_FAILED")
    return 1
  }
}
