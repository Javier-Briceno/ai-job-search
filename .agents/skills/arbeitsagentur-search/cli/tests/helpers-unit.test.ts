import { describe, expect, test } from "bun:test";
import { encodeRefnr, looksBase64, normalizeCard, detailPageUrl } from "../src/helpers";

describe("encodeRefnr", () => {
  test("matches the documented example from the Bundesagentur API docs", () => {
    expect(encodeRefnr("10001-1002716922-S")).toBe("MTAwMDEtMTAwMjcxNjkyMi1T");
  });
});

describe("looksBase64", () => {
  test("a raw refnr (contains a dash) is not treated as already-encoded", () => {
    expect(looksBase64("12811-2300109-S")).toBe(false);
  });

  test("a base64 string is treated as already-encoded", () => {
    expect(looksBase64("MTI4MTEtMjMwMDEwOS1T")).toBe(true);
  });
});

describe("normalizeCard", () => {
  test("maps raw fields and builds a detail-page URL from refnr", () => {
    const card = normalizeCard({
      stellenangebotsTitel: "Werkstudent Controlling",
      referenznummer: "12811-2300109-S",
      firma: "plusserver GmbH",
      stellenlokationen: [{ adresse: { plz: "51149", ort: "Köln" } }],
      veroeffentlichungszeitraum: { von: "2026-07-21" },
    });
    expect(card).toEqual({
      id: "12811-2300109-S",
      title: "Werkstudent Controlling",
      company: "plusserver GmbH",
      location: "51149 Köln",
      date: "2026-07-21",
      url: detailPageUrl("12811-2300109-S"),
    });
  });

  test("missing fields become null, never omitted", () => {
    const card = normalizeCard({ stellenangebotsTitel: "Job", referenznummer: "1-S" });
    expect(card.company).toBeNull();
    expect(card.location).toBeNull();
    expect(card.date).toBeNull();
  });

  test("decodes HTML entities in title and company (regression: API returns literal &amp;)", () => {
    const card = normalizeCard({
      stellenangebotsTitel: "Werkstudent:in Controlling &amp; Finanzmanagement (D/M/W)",
      referenznummer: "1-S",
      firma: "Müller &amp; Partner GmbH",
    });
    expect(card.title).toBe("Werkstudent:in Controlling & Finanzmanagement (D/M/W)");
    expect(card.company).toBe("Müller & Partner GmbH");
  });
});
