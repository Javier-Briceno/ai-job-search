import { BASE_URL, htmlFetch, extractJobPostingJsonLd, normalizeDetail, writeError } from "../helpers.js"

export interface DetailOpts {
  id: string
  format: "json" | "plain"
}

function resolveUrl(id: string): string {
  // Accept a bare numeric ID, a full "/stellenangebote/<id>-p-<slug>" path, or a
  // full URL. The site itself 301s a bare numeric ID to the full slugged URL.
  if (/^\d+$/.test(id)) return `${BASE_URL}/stellenangebote/${id}`
  if (id.startsWith("http")) return id
  if (id.startsWith("/")) return `${BASE_URL}${id}`
  return `${BASE_URL}/stellenangebote/${id}`
}

export async function runDetail(opts: DetailOpts): Promise<number> {
  try {
    const { html, finalUrl } = await htmlFetch(resolveUrl(opts.id))
    if (!html) {
      writeError("Job posting not found", "NOT_FOUND")
      return 1
    }

    const raw = extractJobPostingJsonLd(html)
    if (!raw) {
      writeError("Could not find JobPosting data on the page", "PARSE_FAILED")
      return 1
    }

    const detail = normalizeDetail(raw, finalUrl)

    if (opts.format === "plain") {
      const lines = [
        `Title: ${detail.title}`,
        `Employer: ${detail.company || "—"}`,
        `Location: ${detail.location || "—"}`,
        `Published: ${detail.date || "—"}`,
        `Type: ${detail.employmentType || "—"}`,
        `Apply: ${detail.applyUrl || "—"}`,
        "",
        detail.description || "(no description)",
      ]
      process.stdout.write(lines.join("\n") + "\n")
    } else {
      process.stdout.write(JSON.stringify(detail, null, 2) + "\n")
    }
    return 0
  } catch (e) {
    writeError(e instanceof Error ? e.message : String(e), "DETAIL_FAILED")
    return 1
  }
}
