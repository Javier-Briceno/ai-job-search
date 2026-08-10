import { describe, expect, test } from "bun:test";
import { runCLI, parseJSON } from "./helpers";

// Live smoke test against the real Stepstone site. Kept to a couple of requests,
// respecting the "keep volume low" personal-use requirement. `detail` is expected to
// fail with BLOCKED - that is the verified, correct behavior for this portal's
// job-detail pages (see helpers.ts / url-reference.md).

describe("stepstone live smoke test", () => {
  test("search returns real results with non-null id/title/url", async () => {
    const result = await runCLI(["search", "-q", "Werkstudent Controlling", "-l", "Köln", "--limit", "5"]);
    const data = parseJSON<{ meta: { count: number }; results: Array<Record<string, unknown>> }>(result);

    expect(data.results.length).toBeGreaterThan(0);
    for (const job of data.results) {
      expect(job.id).toBeTruthy();
      expect(job.title).toBeTruthy();
      expect(job.url).toContain("stepstone.de/stellenangebote--");
    }
  });

  test("detail reliably reports BLOCKED rather than hanging or fabricating success", async () => {
    const search = await runCLI(["search", "-q", "Werkstudent Controlling", "-l", "Köln", "--limit", "1"]);
    const searchData = parseJSON<{ results: Array<{ id: string; url: string }> }>(search);
    expect(searchData.results.length).toBeGreaterThan(0);

    const detailResult = await runCLI(["detail", searchData.results[0].url]);

    expect(detailResult.exitCode).toBe(1);
    const err = JSON.parse(detailResult.stderr);
    expect(err.code).toBe("BLOCKED");
  }, 20000);
});
