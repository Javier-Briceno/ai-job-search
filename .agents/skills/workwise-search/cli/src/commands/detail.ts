import { DETAIL_URL, getJson, normalizeDetail, writeError, type RawDetail } from "../helpers.js"

export interface DetailOpts {
  id: string
  format: "json" | "plain"
}

export async function runDetail(opts: DetailOpts): Promise<number> {
  try {
    const data = await getJson<{ data: RawDetail }>(`${DETAIL_URL}/${opts.id}`)
    if (!data) {
      writeError("Job posting not found", "NOT_FOUND")
      return 1
    }
    const detail = normalizeDetail(data.data)

    if (opts.format === "plain") {
      const lines = [
        `Title: ${detail.title}`,
        `Employer: ${detail.company || "—"}`,
        `Location: ${detail.location || "—"}`,
        `Hours: ${detail.hoursPerWeek || "—"}`,
        `Salary: ${detail.salaryPerHour || "—"}`,
        `Published: ${detail.firstPublished || "—"}`,
        `URL: ${detail.url}`,
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
