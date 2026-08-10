import { describe, expect, test } from "bun:test";
import {
  parseJobCards,
  extractJobPostingJsonLd,
  normalizeDetail,
  richTextToPlain,
} from "../src/helpers";

function fakeCard(id: string, title: string, company: string, plz: string, city: string): string {
  return `<li class="relative @container">
  <a id="teaser_job_offer_${id}" class="flex" aria-current="false" href="/stellenangebote/${id}-p-slug">
    <div>
      <h2 class="text-secondary @lg:hidden break-words">${title}</h2>
      <div class="flex flex-wrap items-center gap-xs">
        <span class="text-secondary break-words hyphens-auto leading-[160%] tracking-tight text-[0.875rem]">${company}</span>
      </div>
    </div>
    <ul>
      <li class="flex items-center gap-xs">
        <svg><title id="x">Standort</title></svg>
        <span>${plz} <span>${city}</span></span>
      </li>
    </ul>
  </a>
</li>`;
}

describe("parseJobCards", () => {
  test("extracts id, title, company, location, and absolute url", () => {
    const html = fakeCard("12345", "Werkstudent Controlling (w/m/d)", "Test GmbH", "50667", "Köln");
    const cards = parseJobCards(html);

    expect(cards).toHaveLength(1);
    expect(cards[0]).toEqual({
      id: "12345",
      title: "Werkstudent Controlling (w/m/d)",
      company: "Test GmbH",
      location: "50667 Köln",
      date: null,
      url: "https://www.absolventa.de/stellenangebote/12345-p-slug",
    });
  });

  test("one malformed card does not break parsing of the rest", () => {
    const broken = `<li id="teaser_job_offer_999" class="flex" href="/stellenangebote/999-p-x">`; // no h2 -> skipped
    const good = fakeCard("111", "Werkstudent Finance", "Firma AG", "60311", "Frankfurt am Main");
    const cards = parseJobCards(broken + good);

    expect(cards).toHaveLength(1);
    expect(cards[0].id).toBe("111");
  });

  test("returns an empty array for a page with no job cards", () => {
    expect(parseJobCards("<html><body>no jobs</body></html>")).toEqual([]);
  });
});

describe("richTextToPlain", () => {
  test("decodes double-encoded entities and converts block tags to newlines", () => {
    const raw = "&lt;p&gt;Line one&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Bullet&lt;/li&gt;&lt;/ul&gt;&amp;nbsp;end";
    const plain = richTextToPlain(raw);
    expect(plain).toContain("Line one");
    expect(plain).toContain("Bullet");
    expect(plain).not.toContain("&lt;");
    expect(plain).not.toContain("<p>");
  });
});

describe("extractJobPostingJsonLd", () => {
  test("finds the JobPosting block among several JSON-LD scripts", () => {
    const html = `
      <script type="application/ld+json">{"@type": "BreadcrumbList", "numberOfItems": 2}</script>
      <script type="application/ld+json">{"@type": "JobPosting", "title": "Werkstudent Controlling"}</script>
    `;
    const result = extractJobPostingJsonLd(html);
    expect(result?.["@type"]).toBe("JobPosting");
    expect(result?.title).toBe("Werkstudent Controlling");
  });

  test("returns null when no JobPosting block is present", () => {
    const html = `<script type="application/ld+json">{"@type": "Organization"}</script>`;
    expect(extractJobPostingJsonLd(html)).toBeNull();
  });
});

describe("normalizeDetail", () => {
  test("maps schema.org JobPosting fields, including missing ones to null", () => {
    const raw = {
      title: "Werkstudent Controlling",
      datePosted: "2026-07-01",
      employmentType: "[OTHER]",
      industry: "finance",
      description: "&lt;p&gt;Do stuff.&lt;/p&gt;",
      jobLocation: [{ address: { postalCode: "50667", addressLocality: "Köln" } }],
      hiringOrganization: { name: "Test GmbH" },
    };
    const detail = normalizeDetail(raw, "https://www.absolventa.de/stellenangebote/12345-p-slug");

    expect(detail.id).toBe("12345");
    expect(detail.company).toBe("Test GmbH");
    expect(detail.location).toBe("50667 Köln");
    expect(detail.employmentType).toBe("OTHER");
    expect(detail.applyUrl).toBe("https://www.absolventa.de/stellenangebote/12345-p-slug/apply");
    expect(detail.description).toContain("Do stuff.");
  });

  test("missing optional fields become null, never omitted", () => {
    const detail = normalizeDetail({ title: "Job" }, "https://www.absolventa.de/stellenangebote/1-p-x");
    expect(detail.company).toBeNull();
    expect(detail.location).toBeNull();
    expect(detail.date).toBeNull();
    expect(detail.description).toBeNull();
  });
});
