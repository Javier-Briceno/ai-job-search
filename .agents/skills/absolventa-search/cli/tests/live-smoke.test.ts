import { describe, expect, test } from "bun:test";
import { runCLI, parseJSON } from "./helpers";

// Live smoke test against the real Absolventa site. Kept to a couple of requests -
// this exercises the verified fields[]+positions[] filter combo (see url-reference.md)
// rather than the portal's own unreliable text search.

describe("absolventa live smoke test", () => {
  test("category + position filter returns real results with non-null id/title/url", async () => {
    const result = await runCLI(["search", "--category", "finance", "--position", "werkstudent", "--format", "json"]);
    const data = parseJSON<{ meta: { count: number }; results: Array<Record<string, unknown>> }>(result);

    expect(data.results.length).toBeGreaterThan(0);
    for (const job of data.results) {
      expect(job.id).toBeTruthy();
      expect(job.title).toBeTruthy();
      expect(job.url).toContain("absolventa.de/stellenangebote/");
    }
  });

  test("detail returns a readable description for a real posting", async () => {
    const search = await runCLI(["search", "--position", "werkstudent", "--limit", "1"]);
    const searchData = parseJSON<{ results: Array<{ id: string }> }>(search);
    expect(searchData.results.length).toBeGreaterThan(0);

    const id = searchData.results[0].id;
    const detailResult = await runCLI(["detail", id, "--format", "plain"]);

    expect(detailResult.exitCode).toBe(0);
    expect(detailResult.stdout).toContain("Title:");
    expect(detailResult.stdout.length).toBeGreaterThan(100);
  });
});
