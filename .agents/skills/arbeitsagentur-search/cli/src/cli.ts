#!/usr/bin/env bun
// Self-contained CLI for searching jobs on the Bundesagentur für Arbeit (German
// Federal Employment Agency) public Jobsuche API. No external CLI framework, so
// it runs anywhere `bun` is available with zero install beyond the repo clone.
//
// This is an official government API (robots.txt on arbeitsagentur.de is fully
// open) - no ToS concerns, unlike some of the other portal skills in this repo.

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

const HELP = `arbeitsagentur-cli — search jobs on the Bundesagentur für Arbeit Jobbörse (Germany)

USAGE
  bun run src/cli.ts search [flags]
  bun run src/cli.ts detail <refnr> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>      Job title / keyword search (maps to "was"), e.g. "Werkstudent Controlling"
  --location, -l <text>   City, region, or postal code (maps to "wo"), e.g. "Köln", "50667"
  --jobage <days>         Only postings published within N days (0-100). Omit for all.
  --radius <km>           Search radius in km around --location. Default: portal default (~25km).
  --parttime              Filter to part-time / Werkstudent-style postings (arbeitszeit=tz)
  --page <n>              1-indexed page. Default 1.
  --limit, -n <n>         Cap results emitted (client-side).
  --format <fmt>          json (default) | table | plain.

EXAMPLES
  bun run src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table
  bun run src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt am Main" --jobage 14 --format table
  bun run src/cli.ts search -q "Controlling" -l "Köln" --parttime --format table
  bun run src/cli.ts detail 12811-2300109-S --format plain

No authentication beyond a public static client key. Official government data (robots.txt
on arbeitsagentur.de is fully open) - no ToS concerns.
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

    let jobage: number | undefined
    if (flags.jobage !== undefined) {
      const v = parseIntFlag("jobage", flags.jobage)
      if (v === null) return 1
      jobage = v
    }
    let radius: number | undefined
    if (flags.radius !== undefined) {
      const v = parseIntFlag("radius", flags.radius)
      if (v === null) return 1
      radius = v
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
      location: typeof flags.location === "string" ? flags.location : undefined,
      jobage,
      radius,
      parttime: Boolean(flags.parttime),
      page,
      limit,
      format: (["json", "table", "plain"].includes(fmt) ? fmt : "json") as SearchOpts["format"],
    }
    return runSearch(opts)
  }

  if (cmd === "detail") {
    const id = (flags._ as string[])[1]
    if (!id) {
      process.stderr.write(JSON.stringify({ error: "detail requires a <refnr>", code: "NO_ID" }) + "\n")
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
