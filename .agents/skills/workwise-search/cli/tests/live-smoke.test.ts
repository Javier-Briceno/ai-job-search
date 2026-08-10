import { describe, expect, test } from "bun:test";
import { runCLI, parseJSON } from "./helpers";

// Live smoke test against the real Workwise API. Kept to a couple of requests.

describe("workwise live smoke test", () => {
  test("search returns real results with non-null id/title/url", async () => {
    const result = await runCLI(["search", "-q", "Werkstudent Controlling", "--enquiry-type", "1", "--limit", "5"]);
    const data = parseJSON<{ meta: { count: number }; results: Array<Record<string, unknown>> }>(result);

    expect(data.results.length).toBeGreaterThan(0);
    for (const job of data.results) {
      expect(job.id).toBeTruthy();
      expect(job.title).toBeTruthy();
      expect(job.url).toContain("workwise.io/jobsuche?id=");
    }
  });

  test("detail returns a readable description for a real posting", async () => {
    const search = await runCLI(["search", "-q", "Werkstudent Controlling", "--enquiry-type", "1", "--limit", "1"]);
    const searchData = parseJSON<{ results: Array<{ id: string }> }>(search);
    expect(searchData.results.length).toBeGreaterThan(0);

    const id = searchData.results[0].id;
    const detailResult = await runCLI(["detail", id, "--format", "plain"]);

    expect(detailResult.exitCode).toBe(0);
    expect(detailResult.stdout).toContain("Title:");
    expect(detailResult.stdout.length).toBeGreaterThan(100);
  });
});
