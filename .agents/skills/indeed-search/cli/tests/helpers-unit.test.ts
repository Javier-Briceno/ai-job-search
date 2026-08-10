import { describe, expect, test } from "bun:test";
import { extractJsonAfter, normalizeCard, isBlockedPage, detailPageUrl } from "../src/helpers";

describe("extractJsonAfter", () => {
  test("extracts a balanced JSON object after a marker, ignoring braces inside strings", () => {
    const html = `<script>window.mosaic.providerData["x"]={"a":1,"b":{"nested":true},"s":"contains } a brace"};</script>`;
    const result = extractJsonAfter(html, 'window.mosaic.providerData["x"]=') as Record<string, unknown>;
    expect(result).toEqual({ a: 1, b: { nested: true }, s: "contains } a brace" });
  });

  test("returns null when the marker is not present", () => {
    expect(extractJsonAfter("<html></html>", "missing-marker=")).toBeNull();
  });

  test("returns null when the JSON is malformed", () => {
    const html = `marker={"a":}`;
    expect(extractJsonAfter(html, "marker=")).toBeNull();
  });
});

describe("normalizeCard", () => {
  test("maps raw fields and builds a viewjob URL", () => {
    const card = normalizeCard(
      {
        jobkey: "abc123",
        displayTitle: "Werkstudent Controlling",
        company: "Test GmbH",
        formattedLocation: "50667 Köln",
        formattedRelativeTime: "vor 2 Tagen",
        snippet: "<ul><li>Do stuff</li></ul>",
      },
      "de.indeed.com",
    );
    expect(card).toEqual({
      id: "abc123",
      title: "Werkstudent Controlling",
      company: "Test GmbH",
      location: "50667 Köln",
      date: "vor 2 Tagen",
      url: "https://de.indeed.com/viewjob?jk=abc123",
      snippet: "Do stuff",
    });
  });

  test("returns null when required fields (jobkey/title) are missing", () => {
    expect(normalizeCard({ company: "X" }, "de.indeed.com")).toBeNull();
  });

  test("missing optional fields become null, never omitted", () => {
    const card = normalizeCard({ jobkey: "1", displayTitle: "Job" }, "de.indeed.com");
    expect(card?.company).toBeNull();
    expect(card?.location).toBeNull();
    expect(card?.date).toBeNull();
    expect(card?.snippet).toBeNull();
  });
});

describe("isBlockedPage", () => {
  test("detects the Security Check interstitial title", () => {
    expect(isBlockedPage("<title>Security Check - Indeed.com</title>")).toBe(true);
  });

  test("does not flag a normal page", () => {
    expect(isBlockedPage("<title>Werkstudent Controlling Jobs</title>")).toBe(false);
  });
});

describe("detailPageUrl", () => {
  test("builds a viewjob URL for the given domain", () => {
    expect(detailPageUrl("abc123", "de.indeed.com")).toBe("https://de.indeed.com/viewjob?jk=abc123");
  });
});
