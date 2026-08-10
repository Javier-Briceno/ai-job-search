import { describe, expect, test } from "bun:test";
import { normalizeCard, normalizeDetail, detailPageUrl } from "../src/helpers";

const rawEnquiry = {
  id: 125882,
  name: "Werkstudent für Accounting / Controlling (m/w/d)",
  shortDescription: "Kurzbeschreibung",
  hoursStart: 20,
  hoursEnd: 20,
  minSalary: "16.00",
  maxSalary: "18.00",
  company: { name: "WeWash GmbH" },
  locationLevels: [{ city: "München", zip: "80336" }],
};

describe("normalizeCard", () => {
  test("maps raw fields and builds a jobsuche detail URL", () => {
    const card = normalizeCard(rawEnquiry);
    expect(card).toEqual({
      id: "125882",
      title: "Werkstudent für Accounting / Controlling (m/w/d)",
      company: "WeWash GmbH",
      location: "80336 München",
      date: null,
      url: "https://www.workwise.io/jobsuche?id=125882",
      hoursPerWeek: "20h/Woche",
      salaryPerHour: "16.00-18.00 EUR/h",
    });
  });

  test("missing optional fields become null, never omitted", () => {
    const card = normalizeCard({ id: 1, name: "Job" });
    expect(card.company).toBeNull();
    expect(card.location).toBeNull();
    expect(card.hoursPerWeek).toBeNull();
    expect(card.salaryPerHour).toBeNull();
  });
});

describe("normalizeDetail", () => {
  test("prefers descriptionParts over the raw description field, stripping HTML", () => {
    const detail = normalizeDetail({
      ...rawEnquiry,
      firstPublished: "2026-07-17T11:34:21+02:00",
      descriptionParts: [
        { title: "Was erwartet dich?", text: "<ul><li>Do stuff</li></ul>" },
        { title: "Was bringst du mit?", text: "<p>Studium der BWL</p>" },
      ],
      description: "<p>Should not be used</p>",
    });
    expect(detail.description).toContain("Was erwartet dich?");
    expect(detail.description).toContain("Do stuff");
    expect(detail.description).toContain("Was bringst du mit?");
    expect(detail.description).not.toContain("Should not be used");
    expect(detail.description).not.toContain("<ul>");
    expect(detail.firstPublished).toBe("2026-07-17T11:34:21+02:00");
  });

  test("falls back to the raw description field when descriptionParts is absent", () => {
    const detail = normalizeDetail({ ...rawEnquiry, description: "<h3>Title</h3><p>Body text</p>" });
    expect(detail.description).toContain("Title");
    expect(detail.description).toContain("Body text");
    expect(detail.description).not.toContain("<h3>");
  });
});

describe("detailPageUrl", () => {
  test("builds a jobsuche URL for a given ID", () => {
    expect(detailPageUrl(125882)).toBe("https://www.workwise.io/jobsuche?id=125882");
  });
});
