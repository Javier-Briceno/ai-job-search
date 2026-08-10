import { BASE_URL, htmlFetch, writeError } from "../helpers.js"

export interface DetailOpts {
  id: string
  format: "json" | "plain"
}

function resolveUrl(id: string): string {
  if (id.startsWith("http")) return id
  if (id.startsWith("/")) return `${BASE_URL}${id}`
  // A bare numeric ID has no way to reconstruct the full slugged URL (the ID sits at
  // the *end* of the slug, not a lookup key Stepstone accepts on its own) - detail
  // requires the full path or URL from a search result.
  return `${BASE_URL}/stellenangebote--x--${id}-inline.html`
}

/**
 * Verified live: Stepstone's job-detail pages (/stellenangebote--...-inline.html) hang
 * and then reset the TLS connection entirely - both curl and Bun's fetch() were tested
 * directly against real detail URLs and neither completed (CURLE_RECV_ERROR / an abort
 * timeout), unlike the /jobs/<keyword>/in-<city> search pages, which load normally.
 * This matches robots.txt's disallow of /listing and /search-results (Stepstone's
 * detail/listing surface being actively defended), so this command uses a hard
 * timeout and reports the failure clearly rather than hanging indefinitely.
 */
export async function runDetail(opts: DetailOpts): Promise<number> {
  const url = resolveUrl(opts.id)
  try {
    const html = await htmlFetch(url, 12000)
    if (!html) {
      writeError("Job posting not found", "NOT_FOUND")
      return 1
    }
    // If Stepstone ever serves real content here, still don't claim a parse we
    // haven't verified - report that parsing is not implemented rather than guess
    // at markup that was never actually observed.
    writeError(
      "Received a response, but detail parsing for this page was not implemented (Stepstone's detail pages reset the connection during every attempt in development - see url-reference.md).",
      "NOT_IMPLEMENTED",
    )
    return 1
  } catch (e) {
    writeError(
      `Stepstone's detail pages are actively defended - the connection hung or was reset (${e instanceof Error ? e.message : String(e)}). ` +
        `This was consistent across both curl and fetch() during development, not a transient failure. Open ${url} manually in a browser instead.`,
      "BLOCKED",
    )
    return 1
  }
}
