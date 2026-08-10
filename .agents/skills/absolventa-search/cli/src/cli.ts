#!/usr/bin/env bun
// Self-contained CLI for searching jobs on Absolventa (German student/graduate job
// board). No external CLI framework, so it runs anywhere `bun` is available with
// zero install beyond the repo clone.

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

const HELP = `absolventa-cli — search jobs on Absolventa (German student/graduate job board)

USAGE
  bun run src/cli.ts search [flags]
  bun run src/cli.ts detail <id|url> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>      Best-effort client-side title filter (see notes below)
  --category <slug>       Field/industry, e.g. "controlling", "finance", "rechnungswesen",
                          "buchhaltung", "bankwesen", "versicherungswesen", "steuerwesen",
                          "sap-erp", "wirtschaftspruefung". Maps to the portal's fields[] filter.
  --position <type>       Job type: "werkstudent" | "praktikum" | "trainee" | "festanstellung" |
                          "abschlussarbeit". Maps to the portal's positions[] filter.
  --page <n>              1-indexed page. Default 1.
  --limit, -n <n>         Cap results emitted (client-side).
  --format <fmt>          json (default) | table | plain.

NOTES
  Absolventa's own free-text search box canonicalizes queries server-side in ways
  that are unpredictable via plain HTTP requests (single recognized keywords redirect
  to a channel page; multi-word or unrecognized queries can silently return zero
  results). --category and --position map directly to verified, reliable portal
  filters; --query instead does a simple case-insensitive substring match against
  each result's title, applied locally after fetching. Location filtering is not
  supported for the same reason (the portal's location box requires a JS-resolved
  place ID, and passing raw place text redirects unpredictably).

EXAMPLES
  bun run src/cli.ts search --category controlling --position werkstudent --format table
  bun run src/cli.ts search --category finance --position werkstudent -q "Controlling" --format table
  bun run src/cli.ts search --position werkstudent --format table
  bun run src/cli.ts detail 12720125 --format plain

robots.txt on absolventa.de only blocks one unrelated abuse-report path - no ToS
concerns like some of the other portal skills in this repo.
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
      query: typeof flags.query === "string" ? flags.query : undefined,
      category: typeof flags.category === "string" ? flags.category : undefined,
      position: typeof flags.position === "string" ? flags.position : undefined,
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
