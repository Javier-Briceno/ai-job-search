#!/usr/bin/env bun
// Self-contained CLI for searching jobs on Stepstone (Germany's largest general job
// board). No external CLI framework, so it runs anywhere `bun` is available with
// zero install beyond the repo clone.
//
// PERSONAL USE ONLY: Stepstone's robots.txt disallows /search-results and /listing
// (added within the last few months per the file's own edit-date comments) - these
// look like the site's actual current search-results and job-detail paths. This
// skill uses a different, still-allowed path (/jobs/<keyword>/in-<city>, without a
// disallowed query string) for search, built anyway at explicit user request. The
// `detail` command targets job-detail pages that were verified to actively reset the
// connection during development - see helpers.ts / url-reference.md.

import { runSearch, type SearchOpts } from "./commands/search.js"
import { runDetail, type DetailOpts } from "./commands/detail.js"

interface Flags {
  _: string[]
  [k: string]: string | boolean | string[]
}

function parseFlags(argv: string[]): Flags {
  const flags: Flags = { _: [] }
  const alias: Record<string, string> = { q: "query", l: "location", n: "limit" }
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]
    if (a.startsWith("--") || a.startsWith("-")) {
      const key = alias[a.replace(/^-+/, "")] ?? a.replace(/^-+/, "")
      const next = argv[i + 1]
      if (next === undefined || next.startsWith("-")) {
        flags[key] = true
      } else {
        flags[key] = next
        i++
      }
    } else {
      ;(flags._ as string[]).push(a)
    }
  }
  return flags
}

const HELP = `stepstone-cli — search jobs on Stepstone (Germany)

⚠️  PERSONAL USE ONLY. Stepstone's robots.txt disallows /search-results and /listing -
this CLI uses a different, still-allowed path (/jobs/<keyword>/in-<city>) for search,
built anyway at explicit user request. Keep volume low, no commercial or bulk use.

USAGE
  bun run src/cli.ts search --query "<text>" --location "<city>" [flags]
  bun run src/cli.ts detail <id|url> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>      REQUIRED. Job title or keyword, e.g. "Werkstudent Controlling"
  --location, -l <text>   REQUIRED. City, e.g. "Köln", "Frankfurt am Main"
  --page <n>              1-indexed page. Default 1.
  --limit, -n <n>         Cap results emitted (client-side).
  --format <fmt>          json (default) | table | plain.

DETAIL
  detail is EXPECTED TO FAIL: Stepstone's job-detail pages were verified to actively
  reset the connection during development (both curl and fetch() hung/reset, not a
  transient issue). It exits 1 with code BLOCKED and points you at the URL to open
  manually in a browser.

EXAMPLES
  bun run src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table
  bun run src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt am Main" --page 2 --format table
`

async function main(): Promise<number> {
  const argv = process.argv.slice(2)
  const flags = parseFlags(argv)
  const cmd = (flags._ as string[])[0]

  if (!cmd || flags.help || flags.h) {
    process.stdout.write(HELP)
    return cmd ? 0 : 1
  }

  if (cmd === "search") {
    const query = typeof flags.query === "string" ? flags.query : undefined
    if (!query) {
      process.stderr.write(JSON.stringify({ error: "--query/-q is required", code: "NO_QUERY" }) + "\n")
      return 1
    }
    const location = typeof flags.location === "string" ? flags.location : undefined
    if (!location) {
      process.stderr.write(JSON.stringify({ error: "--location/-l is required", code: "NO_LOCATION" }) + "\n")
      return 1
    }

    const fmt = (flags.format as string) || "json"

    const parseIntFlag = (name: string, raw: string | boolean | string[]): number | null => {
      const val = parseInt(raw as string, 10)
      if (isNaN(val)) {
        process.stderr.write(JSON.stringify({ error: `--${name} must be a number, got "${raw}"`, code: "BAD_ARG" }) + "\n")
        return null
      }
      return val
    }

    let page = 1
    if (flags.page !== undefined) {
      const v = parseIntFlag("page", flags.page)
      if (v === null) return 1
      page = Math.max(1, v)
    }
    let limit: number | undefined
    if (flags.limit !== undefined) {
      const v = parseIntFlag("limit", flags.limit)
      if (v === null) return 1
      limit = v
    }

    const opts: SearchOpts = {
      query,
      location,
      page,
      limit,
      format: (["json", "table", "plain"].includes(fmt) ? fmt : "json") as SearchOpts["format"],
    }
    return runSearch(opts)
  }

  if (cmd === "detail") {
    const id = (flags._ as string[])[1]
    if (!id) {
      process.stderr.write(JSON.stringify({ error: "detail requires an <id|url>", code: "NO_ID" }) + "\n")
      return 1
    }
    const fmt = (flags.format as string) || "json"
    const opts: DetailOpts = {
      id,
      format: (fmt === "plain" ? "plain" : "json") as DetailOpts["format"],
    }
    return runDetail(opts)
  }

  process.stderr.write(JSON.stringify({ error: `Unknown command "${cmd}"`, code: "BAD_CMD" }) + "\n")
  return 1
}

main()
  .then((code) => process.exit(code))
  .catch((e) => {
    process.stderr.write(
      JSON.stringify({
        error: e instanceof Error ? e.message : String(e),
        code: "INTERNAL_ERROR",
      }) + "\n",
    )
    process.exit(1)
  })
