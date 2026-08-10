import { describe, expect, test } from "bun:test";
import { slugify, parseJobCards } from "../src/helpers";

describe("slugify", () => {
  test("lowercases and hyphenates", () => {
    expect(slugify("Werkstudent Controlling")).toBe("werkstudent-controlling");
  });

  test("transliterates German umlauts and ß to match Stepstone's own scheme", () => {
    expect(slugify("Köln")).toBe("koeln");
    expect(slugify("Düsseldorf")).toBe("duesseldorf");
    expect(slugify("Straße")).toBe("strasse");
  });

  test("collapses non-alphanumeric runs and trims edge hyphens", () => {
    expect(slugify("  Finance & Controlling!! ")).toBe("finance-controlling");
  });
});

function fakeCard(id: string, title: string, company: string, location: string, timeago: string): string {
  return `<div data-testid="job-item" data-jobcard-green-phase="true">
    <a href="/stellenangebote--${title.replace(/\s+/g, "-")}--${id}-inline.html">
      <div data-at="job-item-title">${title}</div>
    </a>
    <span data-at="job-item-company-name"><svg><path d="M1 2"/></svg><span>${company}</span></span>
    <span data-at="job-item-location"><svg><path d="M1 2"/></svg><span>${location}</span></span>
    <span data-at="job-item-timeago"><time>${timeago}</time></span>
  </div>`;
}

describe("parseJobCards", () => {
  test("extracts id, title, company, location, date, and absolute url", () => {
    const html = fakeCard("14162707", "Werkstudent Controlling", "abcbank GmbH", "Köln", "vor 16 Stunden");
    const cards = parseJobCards(html);

    expect(cards).toHaveLength(1);
    expect(cards[0].id).toBe("14162707");
    expect(cards[0].title).toBe("Werkstudent Controlling");
    expect(cards[0].company).toBe("abcbank GmbH");
    expect(cards[0].location).toBe("Köln");
    expect(cards[0].date).toBe("vor 16 Stunden");
    expect(cards[0].url).toBe("https://www.stepstone.de/stellenangebote--Werkstudent-Controlling--14162707-inline.html");
  });

  test("splitting on job-item does not false-match job-item-title etc.", () => {
    // Two cards back to back - if the split marker were too loose, sub-element
    // markers like data-at="job-item-title" would create phantom extra chunks.
    const html =
      fakeCard("1", "Job One", "Firma A", "Köln", "vor 1 Tag") +
      fakeCard("2", "Job Two", "Firma B", "Frankfurt", "vor 2 Tagen");
    const cards = parseJobCards(html);
    expect(cards).toHaveLength(2);
    expect(cards.map((c) => c.id)).toEqual(["1", "2"]);
  });

  test("a card with no matching detail href is skipped without breaking others", () => {
    const broken = `<div data-testid="job-item"><div data-at="job-item-title">No href here</div></div>`;
    const good = fakeCard("99", "Good Job", "Firma", "Köln", "vor 3 Tagen");
    const cards = parseJobCards(broken + good);
    expect(cards).toHaveLength(1);
    expect(cards[0].id).toBe("99");
  });

  test("returns an empty array for a page with no job cards", () => {
    expect(parseJobCards("<html><body>no jobs</body></html>")).toEqual([]);
  });
});
