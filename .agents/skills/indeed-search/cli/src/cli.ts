#!/usr/bin/env bun
// Self-contained CLI for searching jobs on Indeed's public search-results pages.
// No external CLI framework, so it runs anywhere `bun` is available with zero
// install beyond the repo clone.
//
// PERSONAL USE ONLY, more so than the other portal skills in this repo: Indeed's
// robots.txt has a dedicated block naming ClaudeBot, GPTBot, anthropic-ai, and other
// AI crawlers specifically, disallowing /jobs and /viewjob. This was built anyway at
// explicit user request. /viewjob (the `detail` command) was verified to return an
// active bot-check interstitial regardless of User-Agent, so `detail` reliably fails
// with a clear BLOCKED error rather than pretending to work - see helpers.ts and
// url-reference.md.

import { runSearch, type SearchOpts } from "./commands/search.js"
import { runDetail, type DetailOpts } from "./commands/detail.js"
import { DEFAULT_DOMAIN } from "./helpers.js"

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

const HELP = `indeed-cli — search jobs on Indeed (default market: Germany)

⚠️  PERSONAL USE ONLY. Indeed's robots.txt specifically names AI crawlers (ClaudeBot,
GPTBot, anthropic-ai, etc.) and disallows /jobs and /viewjob for them. This CLI was
built anyway at explicit user request - keep volume low, do not use commercially or
for bulk collection, and run it on your own responsibility.

USAGE
  bun run src/cli.ts search [flags]
  bun run src/cli.ts detail <jobkey> [--format json|plain]

SEARCH FLAGS
  --query, -q <text>      Keywords (title, skill, or role), e.g. "Werkstudent Controlling"
  --location, -l <text>   City or region, e.g. "Köln"
  --domain <host>         Indeed country domain. Default: de.indeed.com
  --page <n>              1-indexed page (15 results/page). Default 1.
  --limit, -n <n>         Cap results emitted (client-side).
  --format <fmt>          json (default) | table | plain.

DETAIL
  detail is EXPECTED TO FAIL: Indeed's /viewjob page returns an active bot-check
  interstitial regardless of User-Agent (verified during development, not just a
  robots.txt disallow). It exits 1 with code BLOCKED and points you at the job's
  URL to open manually, or at the "snippet" field search already returns.

EXAMPLES
  bun run src/cli.ts search -q "Werkstudent Controlling" -l "Köln" --format table
  bun run src/cli.ts search -q "Werkstudent Controlling" -l "Frankfurt" --format plain
  bun run src/cli.ts detail 67580be47dbcecf2 --format plain
`

async function main(): Promise<number> {
  const argv = process.argv.slice(2)
  const flags = parseFlags(argv)
  const cmd = (flags._ as string[])[0]

  if (!cmd || flags.help || flags.h) {
    process.stdout.write(HELP)
    return cmd ? 0 : 1
  }

  const domain = typeof flags.domain === "string" ? flags.domain : DEFAULT_DOMAIN

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
      location: typeof flags.location === "string" ? flags.location : undefined,
      domain,
      page,
      limit,
      format: (["json", "table", "plain"].includes(fmt) ? fmt : "json") as SearchOpts["format"],
    }
    return runSearch(opts)
  }

  if (cmd === "detail") {
    const id = (flags._ as string[])[1]
    if (!id) {
      process.stderr.write(JSON.stringify({ error: "detail requires a <jobkey>", code: "NO_ID" }) + "\n")
      return 1
    }
    const fmt = (flags.format as string) || "json"
    const opts: DetailOpts = {
      id,
      domain,
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
