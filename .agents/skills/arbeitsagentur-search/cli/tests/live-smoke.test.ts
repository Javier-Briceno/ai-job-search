import { describe, expect, test } from "bun:test";
import { runCLI, parseJSON } from "./helpers";

// Live smoke test against the real Bundesagentur für Arbeit API. Keep this to
// a single search + single detail call - this is a public government API with
// no rate-limit concerns, but we still don't need more than one round trip to
// prove the CLI end-to-end.

describe("arbeitsagentur live smoke test", () => {
  test("search returns real results with non-null id/title/url", async () => {
    const result = await runCLI(["search", "-q", "Werkstudent Controlling", "-l", "Köln", "--limit", "5"]);
    const data = parseJSON<{ meta: { count: number }; results: Array<Record<string, unknown>> }>(result);

    expect(data.results.length).toBeGreaterThan(0);
    for (const job of data.results) {
      expect(job.id).toBeTruthy();
      expect(job.title).toBeTruthy();
      expect(job.url).toContain("arbeitsagentur.de/jobsuche/jobdetail/");
    }
  });

  test("detail returns a readable description for a real posting", async () => {
    const search = await runCLI(["search", "-q", "Werkstudent Controlling", "-l", "Köln", "--limit", "1"]);
    const searchData = parseJSON<{ results: Array<{ id: string }> }>(search);
    expect(searchData.results.length).toBeGreaterThan(0);

    const id = searchData.results[0].id;
    const detailResult = await runCLI(["detail", id, "--format", "plain"]);

    expect(detailResult.exitCode).toBe(0);
    expect(detailResult.stdout).toContain("Title:");
    expect(detailResult.stdout.length).toBeGreaterThan(100);
  });
});
