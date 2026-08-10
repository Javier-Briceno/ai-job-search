import { SEARCH_URL, htmlFetch, parseJobCards, writeError, type JobCard } from "../helpers.js"

export interface SearchOpts {
  query?: string
  category?: string
  position?: string
  page: number
  limit?: number
  format: "json" | "table" | "plain"
}

function buildUrl(opts: SearchOpts): string {
  const params = new URLSearchParams()
  if (opts.category) params.append("fields[]", opts.category)
  if (opts.position) params.append("positions[]", opts.position)
  if (opts.page > 1) params.set("page", String(opts.page))
  const qs = params.toString()
  return qs ? `${SEARCH_URL}?${qs}` : SEARCH_URL
}

/**
 * Absolventa's own `text=` keyword search redirects unpredictably (it canonicalizes
 * to a channel page or, for multi-word/unmatched queries, silently returns an
 * unfiltered or empty page) - see url-reference.md. So --query is applied here as a
 * simple client-side substring match on the title instead of being sent to the portal.
 */
function applyQueryFilter(cards: JobCard[], query?: string): JobCard[] {
  if (!query) return cards
  const needle = query.toLowerCase()
  return cards.filter((c) => c.title.toLowerCase().includes(needle))
}

function renderTable(cards: JobCard[]): string {
  if (cards.length === 0) return "No results."
  const rows = cards.map((c) => {
    const title = (c.title || "").slice(0, 42).padEnd(42)
    const company = (c.company || "—").slice(0, 26).padEnd(26)
    const loc = (c.location || "—").slice(0, 24).padEnd(24)
    return `${c.id.padEnd(9)} ${title} ${company} ${loc}`
  })
  const header = "ID".padEnd(9) + " " + "TITLE".padEnd(42) + " " + "COMPANY".padEnd(26) + " " + "LOCATION"
  return [header, "-".repeat(header.length), ...rows].join("\n")
}

export async function runSearch(opts: SearchOpts): Promise<number> {
  try {
    const { html } = await htmlFetch(buildUrl(opts))
    let cards = applyQueryFilter(parseJobCards(html), opts.query)
    if (opts.limit !== undefined && opts.limit >= 0) cards = cards.slice(0, opts.limit)

    if (opts.format === "table") {
      process.stdout.write(renderTable(cards) + "\n")
    } else if (opts.format === "plain") {
      process.stdout.write(
        cards
          .map((c) => `${c.title}\n  ${c.company || "—"} · ${c.location || "—"}\n  id: ${c.id}\n  ${c.url}`)
          .join("\n\n") + "\n",
      )
    } else {
      process.stdout.write(
        JSON.stringify({ meta: { count: cards.length, page: opts.page }, results: cards }, null, 2) + "\n",
      )
    }
    return 0
  } catch (e) {
    writeError(e instanceof Error ? e.message : String(e), "SEARCH_FAILED")
    return 1
  }
}
