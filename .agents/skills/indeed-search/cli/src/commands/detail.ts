import { curlRequest, detailPageUrl, isBlockedPage, writeError } from "../helpers.js"

export interface DetailOpts {
  id: string
  domain: string
  format: "json" | "plain"
}

/**
 * Verified live: Indeed's /viewjob page is actively blocked for automated requests -
 * either a bare 403, or (via some clients) a 200 "Security Check" bot-check
 * interstitial. Either way this is an active technical block, not a robots.txt
 * courtesy, so this command reliably fails and reports that clearly rather than
 * returning garbage or a false success. Use the `snippet` field from `search`
 * results for a short preview instead.
 */
export async function runDetail(opts: DetailOpts): Promise<number> {
  const url = detailPageUrl(opts.id, opts.domain)
  try {
    const { status, body } = await curlRequest(url)

    if (status === 403 || isBlockedPage(body)) {
      writeError(
        `Indeed blocked this request (HTTP ${status}) - viewjob pages are actively protected, not just robots.txt-disallowed. ` +
          `Use the "snippet" field from the search command for a short preview, or open ${url} manually in a browser.`,
        "BLOCKED",
      )
      return 1
    }
    if (status === 404) {
      writeError("Job posting not found", "NOT_FOUND")
      return 1
    }
    if (status < 200 || status >= 300) {
      writeError(`Request failed: HTTP ${status}`, "DETAIL_FAILED")
      return 1
    }

    // If Indeed ever serves real content here, still don't claim a parse we haven't
    // verified - report that parsing is not implemented rather than fabricate a shape.
    writeError(
      "Received a non-blocked response, but detail parsing for this page was not implemented (Indeed consistently blocked it during development - see url-reference.md).",
      "NOT_IMPLEMENTED",
    )
    return 1
  } catch (e) {
    writeError(e instanceof Error ? e.message : String(e), "DETAIL_FAILED")
    return 1
  }
}
