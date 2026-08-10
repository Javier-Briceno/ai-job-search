#!/usr/bin/env bun
// Self-contained CLI for searching jobs on Workwise (German student/SME-focused job
// board). No external CLI framework, so it runs anywhere `bun` is available with
// zero install beyond the repo clone.
//
// Workwise's site is a client-rendered Next.js SPA with no job data in its
// server-rendered HTML - the endpoints this CLI calls were found via a real browser
// network capture, not documented anywhere. See url-reference.md.

import { runSearch, type SearchOpts } from "./commands/search.js"
import { runDetail, type DetailOpts } from "./commands/detail.js"

interface Flags {
  _: string[]
  [k: string]: string | boolean | string[]
}

function parseFlags(argv: string[]): Flags {
  const flags: Flags = { _: [] }
  const alias: Record<string, string> = { q: "query", n: "limit" }
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

const HELP = `workwise-cli — search jobs on Workwise (Germany, student/SME-focused)

USAGE
  bun run src/cli.ts search --query "<text>" [flags]
  bun run src/cli.ts detail <id> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>      REQUIRED. Job title or keyword, e.g. "Controlling"
  --enquiry-type <id>     Filter by employment-type ID. Only 1 = Werkstudent
                          (Werkstudententätigkeit) is confirmed; other IDs are
                          unverified. Omit for all types.
  --size <n>              Results requested from the API. Default 14.
  --limit, -n <n>         Cap results emitted (client-side).
  --format <fmt>          json (default) | table | plain.

NOTES
  --location is NOT supported: Workwise's search API takes a structured location
  object (city/zip/lat/lon/googlePlaceId), which needs a geocoding lookup this CLI
  doesn't have access to (same class of limitation as absolventa-search's location
  field - see url-reference.md). Each result's own "location" field still shows
  city/postal code, so check it per-result instead.

  Pagination beyond the first --size results is unverified - no offset/page
  parameter was observed in the captured request, so only a single batch is
  supported for now.

EXAMPLES
  bun run src/cli.ts search -q "Werkstudent Controlling" --enquiry-type 1 --format table
  bun run src/cli.ts search -q "Controlling" --format table
  bun run src/cli.ts detail 125882 --format plain
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

    const fmt = (flags.format as string) || "json"

    const parseIntFlag = (name: string, raw: string | boolean | string[]): number | null => {
      const val = parseInt(raw as string, 10)
      if (isNaN(val)) {
        process.stderr.write(JSON.stringify({ error: `--${name} must be a number, got "${raw}"`, code: "BAD_ARG" }) + "\n")
        return null
      }
      return val
    }

    let enquiryTypeId: number | undefined
    if (flags["enquiry-type"] !== undefined) {
      const v = parseIntFlag("enquiry-type", flags["enquiry-type"])
      if (v === null) return 1
      enquiryTypeId = v
    }
    let size = 14
    if (flags.size !== undefined) {
      const v = parseIntFlag("size", flags.size)
      if (v === null) return 1
      size = Math.max(1, v)
    }
    let limit: number | undefined
    if (flags.limit !== undefined) {
      const v = parseIntFlag("limit", flags.limit)
      if (v === null) return 1
      limit = v
    }

    const opts: SearchOpts = {
      query,
      enquiryTypeId,
      size,
      limit,
      format: (["json", "table", "plain"].includes(fmt) ? fmt : "json") as SearchOpts["format"],
    }
    return runSearch(opts)
  }

  if (cmd === "detail") {
    const id = (flags._ as string[])[1]
    if (!id) {
      process.stderr.write(JSON.stringify({ error: "detail requires an <id>", code: "NO_ID" }) + "\n")
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
