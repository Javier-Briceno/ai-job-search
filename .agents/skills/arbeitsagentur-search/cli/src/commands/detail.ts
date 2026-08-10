import {
  DETAIL_URL,
  apiFetch,
  encodeRefnr,
  looksBase64,
  normalizeDetail,
  writeError,
  type RawJobDetail,
} from "../helpers.js"

export interface DetailOpts {
  id: string
  format: "json" | "plain"
}

export async function runDetail(opts: DetailOpts): Promise<number> {
  try {
    // Accept either the raw refnr (e.g. "12811-2300109-S") or an already
    // base64-encoded ID copy-pasted from a previous run.
    const encoded = looksBase64(opts.id) ? opts.id : encodeRefnr(opts.id)
    const data = await apiFetch<RawJobDetail>(`${DETAIL_URL}/${encoded}`)

    if (!data) {
      writeError("Job posting not found", "NOT_FOUND")
      return 1
    }

    const detail = normalizeDetail(data)

    if (opts.format === "plain") {
      const lines = [
        `Title: ${detail.title}`,
        `Employer: ${detail.company || "—"}`,
        `Location: ${detail.location || "—"}`,
        `Published: ${detail.date || "—"}`,
        `Entry date: ${detail.entryDate || "—"}`,
        `Contract: ${detail.employmentType || "—"}`,
      ]
      if (detail.applyUrl) lines.push(`Apply: ${detail.applyUrl}`)
      lines.push("", detail.description || "(no description)")
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
