---
framework_version: 2.1.0
---

# CV Templates and Tailoring Guide

<!-- SETUP: Profile statements and section ordering are personalized by running /setup -->

## Template: LaTeX moderncv (Banking Style)

All CVs use the moderncv LaTeX package with the "banking" style and "blue" color scheme.

**Output file:** `cv/main_<company>_<role>.tex`
**Compile with:** **lualatex** on MiKTeX/TeX Live. pdflatex often fails on modern MiKTeX installs with `fontawesome5` font-expansion errors; lualatex handles the same sources cleanly.
**Master reference:** `cv/main_example.tex` (comprehensive CV with all competencies, experience, and achievements - use as source when building targeted CVs)

### Compile command

```bash
cd cv && lualatex -interaction=nonstopmode main_<company>_<role>.tex
```

Run it **twice**: the `n/m` page footer resolves from the `.aux` file, so a single run after a length change reports the previous run's total.

Expected output: 1 or 2 pages. Prefer 1 page when it carries the relevant evidence cleanly; use a second page when reaching 1 would remove material, non-duplicative proof of fit. More than 2 pages is always a failure.

## Document Structure

`cv/main_example.tex` is the authoritative skeleton - read it before drafting rather than reconstructing a preamble from memory. Section order:

```
Kurzprofil -> Kernkompetenzen -> Berufserfahrung -> Projekte -> Ausbildung -> Sprachen
```

The preamble carries five groups of overrides. **None of them are cosmetic; do not drop any when tailoring.**

| Override | Why it is there |
|---|---|
| `\firstnamestyle` / `\lastnamestyle` / `\sectionstyle` | Banking on lualatex+MiKTeX renders names and headings black despite `\moderncvcolor{blue}` |
| `\mobilephonesymbol` etc. blanked | FontAwesome icons have no Unicode mapping and extract as `MOBILE-ANDROID-ALT` or `U+FFFD` |
| `\labelitemi` -> `-` | moderncv's circle marker extracts as a stray symbol on every bullet line |
| `\makeheaddetailssymbol` -> `\textbar` | The default `\rmfamily\textbullet` reaches the text layer as a bare `0xB7` byte - invalid UTF-8 |
| `\cventry` -> single-column | See below |
| `\raggedright` + `\hyphenpenalty=10000` | Justified text hyphenates German compounds across line breaks, so a screening parser never matches the keyword |

### The single-column `\cventry` override (do not revert)

moderncv's banking `\cventry` sets location and date in a right-aligned second column. It looks good and it extracts wrong: in **raw** `pdftotext` mode those fields emerge as one floating block *after* every entry in the section, so a parser attributes dates to the wrong employer or to none.

Measured on the stock template, three roles:

```
[Company] [Job Title] - [Achievement 1] - [Achievement 2] ...
[Company] [Job Title] - [Achievement 1] ...
[Company] [Job Title] - [Achievement 1] ...

[City, Country] [YYYY-Present]      <- detached from its employer
[City, Country] [YYYY-YYYY]
[City, Country] [YYYY-YYYY]
```

With the override, each entry extracts sequentially and complete:

```
[Unternehmen], [Position]
[MM/JJJJ-heute] | [Ort]
- [Aufgabe oder Erfolg 1]
```

Argument order is unchanged from moderncv - `{date}{title}{organization}{location}{grade}{description}` - so **argument 3 is the bold line**. A project entry therefore passes the project name as argument 3 and the stack as argument 2, not the reverse.

Arguments 4 and 5 are optional and the override tests for emptiness, so `{}` is safe for a project with no location.

### Placeholder bracing (silent text loss)

Always write `\item {[Text]}`, never `\item [Text]`. Unbraced, LaTeX parses the square brackets as `\item`'s **optional label argument**: the text becomes the bullet's label, renders into the left margin, and is clipped off the page edge. It is not subtle once compiled - it is simply easy to introduce and easy to leave uncompiled.

```latex
\item {[Achievement or responsibility 1]}   % correct
\item [Achievement or responsibility 1]     % text lost off the page edge
```

### Localisation via the heading macro block

Section names live in one block of `\newcommand`s (`\headingCompetencies`, `\headingExperience`, `\headingProjects`, `\headingEducation`, `\headingLanguages`, `\headingAwards`). Localise the CV by editing that block only. Never rewrite individual `\section{...}` lines - that is how headings drift out of sync between profile variants.

### Date format

German convention, `MM/JJJJ`, with an **ASCII hyphen** joining the range: `[MM/JJJJ-MM/JJJJ]`. Never `--` - it ligatures into an en-dash (U+2013) that many parsers fail to read as a range, and under lualatex it also lands in the text layer as an invalid byte. See "Date fields must be ASCII ranges" below.

### Color overrides

The three `\renewcommand*` lines in the preamble are required on lualatex+MiKTeX. Without them the firstname, lastname, and section headings render in black even though `\moderncvcolor{blue}` is set, which looks inconsistent with the rest of the blue accent scheme (links, bullet markers, contact icons). The override forces all three to use `color1` (moderncv's accent colour, which becomes blue under `\moderncvcolor{blue}`). Both names render bold; if you prefer the firstname in regular weight, change the firstnamestyle override from `\bfseries` to `\mdseries`. Don't drop the override - on most modern installs the defaults render visibly wrong.

### Spacing inside itemize lists (important)

**Do not place `\vspace{...}` between `\item` entries in an `itemize` list.** Even though the source looks symmetric, this pattern occasionally produces a noticeably oversized gap before a single item: the inter-item `\vspace` creates a paragraph break that interacts unpredictably with the list's internal `\itemsep`, so LaTeX renders one of the gaps wider than the rest. Remove the inter-item `\vspace` and let `itemize` use its native uniform spacing.

```latex
% WRONG - intermittently produces an oversized gap before one bullet
\begin{itemize}
\item \textbf{Foo}: ...
\vspace{1pt}
\item \textbf{Bar}: ...
\vspace{1pt}
\item \textbf{Baz}: ...
\end{itemize}

% RIGHT - uniform spacing using the list's native itemsep
\begin{itemize}
\item \textbf{Foo}: ...
\item \textbf{Bar}: ...
\item \textbf{Baz}: ...
\end{itemize}
```

Two related patterns are fine and should be kept:
- `\vspace{1pt}` immediately after `\section{...}` (between section heading and first item) - this is between the heading and the list, not between list items.
- `\vspace{3pt}` between top-level `\cventry` blocks in Professional Experience or Education - this gives breathing room between roles and renders consistently.

### Section headings must match the CV's language (important)

Section headings such as `\section{Core Competencies}`, `Professional Experience`, `Education`, `Languages`, `Publications`, `Honors and Awards`, `References` (and any others your template defines), plus the `Available upon request.` line under References, are all **literal English text baked into the template** - they do not translate themselves. Whenever the CV language (see `CV language` in the candidate profile) is not English, translate every one of these too, whatever they are, not just the body prose - a CV with a fully localized profile statement and bullets sitting under untouched English section headers reads as sloppy and inconsistent, and it's an easy thing to forget precisely because the prose translation is the obvious, visible part of the job. Worked example for Spanish: `Competencias Clave`, `Experiencia Profesional`, `Educaci\'on`, `Idiomas`, `Publicaciones`, `Distinciones y Premios`, `Referencias`, `Disponibles a solicitud.` The same rule applies for any other target language - check this explicitly during the verification pass.

## Section-by-Section Tailoring

### Profile Statement / Elevator Pitch (Best Practice)
This is the most important section to customize. It appears right after `\makecvtitle`.

Write 5-7 lines that function as an "elevator pitch": a concise, compelling introduction explaining why you're qualified for *this specific role*. Focus on what the employer gains from hiring you.

When the role sits outside your home domain, **lead with the domain-transfer argument** - the one or two sentences connecting your background to their problem (e.g. wave physics to radar signal processing) belong in the profile statement's opening, not buried in the cover letter. It is the strongest card a domain-changer holds; play it first.

**Create 2-3 profile statement templates for your main role types:**

<!-- SETUP: These are populated based on your background -->
**For [YOUR_PRIMARY_ROLE_TYPE] roles:**
> [YOUR_PROFILE_STATEMENT_TEMPLATE_1]

**For [YOUR_SECONDARY_ROLE_TYPE] roles:**
> [YOUR_PROFILE_STATEMENT_TEMPLATE_2]

Statements labeled *[Used for: <company>_<role>]* were extracted from archived application drafts by `/setup` Path A. They are **phrasing references, never fact sources**: when drafting from one, every factual claim still comes from `01-candidate-profile.md` - a past tailored draft does not vouch for its own accuracy.

### Core Competencies / Skills Section (Best Practice)
Reorder and emphasize based on the role. Use bold category labels.

List **5-7 key competencies** in bullet format, tailored to the specific job. For each competency, briefly explain how it adds value to the position.

Use the posting's own core term in the matching bullet's bold label when it truthfully applies - ATS and skim-reading hiring managers match literally, and "MLOps" in a heading outperforms a paraphrase like "ML Deployment".

### Education
- Always include your highest degrees
- For senior roles, keep education brief (dates and titles only)
- Include thesis topics when relevant to the target role

#### In-progress qualifications must say so explicitly

**A bare year range is not enough.** An entry reading `2025–2026`, seen partway through 2026, looks like a *finished* degree, because a reader skimming a CV treats a closed range as closed. A profile statement that says "currently completing…" does not fix it: the education entry is where a reader checks the credential, so it has to stand on its own.

State completion inside the entry itself:

```latex
\item{\cventry{2025--2026}{[Degree], [Field]}{[Institution]}{[Location]}{}{\vspace{1pt}
In progress, expected [Month Year]. [Relevant topics]
}}
```

Any consistent form works: `In progress, expected <Month Year>.` / `Expected completion <Month Year>.` / a date field of `2025–present`.

Claiming a credential not yet held is a factual misstatement, and it is the kind discovered at transcript or reference check rather than at interview. It costs nothing to prevent. The same applies to in-progress certifications and courses.

**Check for agreement:** for a current student, the profile statement, the education entry, and any availability or work-permit note must all give the same completion date. Contradiction between them is worse than any single version.

### Professional Experience
- Rewrite bullet points to emphasize aspects most relevant to the target role
- Use 4-6 bullets for most recent role, 3-4 for previous, 2-3 for older
- **Emphasize measurable results** where possible: "Reduced processing time by X%", "Model adopted by the team"

#### Check tenure against visible output

Before finalizing, look at each role the way a stranger will: **date span versus how much work is shown.** A two-year role represented by a single project reads as low output, whether or not that is fair. The reader cannot know what filled the time, so they guess, and the guess is unflattering.

This bites hardest on **career changers** (part of the tenure went into learning the new field), on **long-cycle work** (industrial deployment, clinical or regulatory projects, research — one delivery genuinely takes quarters), and on anyone whose employer kept them on a single account or product.

Three honest fixes, in order of preference:

1. **Surface more real work.** Ask what else the period contained. There are often real secondary projects, internal tooling, or support work that never reached the CV because it felt minor. Best fix when the material exists.
2. **Make the phases within the role explicit.** If the span genuinely had stages, say so — an initial period learning the domain or supporting the team, then ownership of the named work through to delivery. A phased arc reads as a growth curve; an undifferentiated multi-year block reads as stagnation.
3. **Name what made the cycle long.** Data collection from a live environment, validation with domain experts, deployment and iteration against real output. Reviewers who know the domain accept this immediately.

**Never** pad with invented projects, and **never** quietly shorten the employment dates so the ratio looks better. Both are discoverable, and both are worse than the perception problem being solved.

**Prepare the interview answer too.** If a long span against little visible output survives these fixes, the question is coming. The candidate needs a ready two-part answer — what actually filled the time, and what the outcome was — recorded in their interview prep rather than improvised in the room.

### Handling Employment Gaps (Best Practice)
If there is a gap in your employment history:
- The gap should be explained matter-of-factly if needed
- Describe how professional development continued during the gap
- Frame as deliberate skill-building and career repositioning

### Publications
- Include Google Scholar link if applicable
- Select 3-4 most relevant publications (not always all of them)
- For non-academic roles, keep brief

### Evidence Links
Wherever the CV names a verifiable artifact - a public project, a hackathon entry, a publication - carry its link (`\href`) so a reader can verify the claim in one click. A CV whose strongest claims are checkable reads as more credible everywhere else too.

### Honors and Awards
- Keep format brief, one line each

### References - deliberately absent

The template has **no References section and no "Available upon request." line**. That is an Anglo-American convention with no functional equivalent in the German market, where Arbeitszeugnisse are attached as Anlagen instead. The line spends a heading and a row of the page budget carrying zero information.

Do not reintroduce it. If a posting explicitly asks for referees, supply them in the application form or as a separate Anlage, not as a CV section.

## Compile-and-Inspect Loop (MANDATORY)

After writing the CV and before presenting to the user, always compile and visually inspect the PDF. Iterate until the layout is clean. Workflow:

1. Run `lualatex -interaction=nonstopmode main_<company>_<role>.tex` **twice** - the `n/m` footer resolves from the `.aux`, so one run after a length change prints the previous total (a 1-page CV footed `1/2` is a stale `.aux`, not an overflow)
2. Check the output page count: prefer 1 page, allow 2 when the second page contains relevant evidence, and never exceed 2
3. Read the PDF via the Read tool and inspect it visually
4. Check for **orphaned entries**: a `\cventry` title line must never sit alone at the foot of the page with its bullets pushed over

### Fixing common page-break problems

**Problem: entry title stranded at the foot of the page**
The overridden `\cventry` already issues `\needspace{4\baselineskip}` on every entry, so this should not occur. If it does, raise that value inside the override rather than sprinkling `\needspace` at call sites - one definition, every entry.

**Caveat - `\needspace` belongs before entries, never before `\section` headings.** A section-level `\needspace` pushes the entire section to the next page whenever the request does not fit, stranding empty space above and *adding* a page instead of saving one.

**Problem: only a few lines spill to page 2**
Remove redundancy first. If the spill is still only a few lines, `\enlargethispage{2-3\baselineskip}` before a late section can rescue the near miss without shrinking margins or type. Do not use it to force substantial relevant content onto page 1.

**Problem: page 2 has substantial relevant content**
Keep the second page and balance the break. A two-page CV is valid when page 2 carries material evidence rather than repetition or filler. Check that no heading or entry is orphaned and that page 2 is not mostly empty.

**Problem: page 3 appears**
Cut content using relevance-weighted cutting; never reduce margins, font size, or line spacing to hide a three-page content problem.

## ATS Parseability

Most employers run CVs through an ATS before a human sees them, and the ATS reads the PDF's embedded **text layer**, not the rendered page. A CV can pass visual inspection and still extract as garbage. After the layout passes the compile-and-inspect loop, verify the text layer:

Extract in **both** modes - they fail differently, and `-layout` hides the fault the override exists to fix:

```bash
cd cv && pdftotext -layout main_<company>_<role>.pdf main_<company>_<role>.txt
cd cv && pdftotext main_<company>_<role>.pdf -            # raw order
```

`pdftotext` comes from [poppler](https://poppler.freedesktop.org/), not the TeX distribution - it is an **optional** dependency, and it does **not** ship with MiKTeX or TeX Live. If it is not installed, skip the mechanical check with a warning and rely on the visual PDF read for keyword coverage.

What to check in the extraction:

- **No disallowed characters.** The rule is an allowlist, **not** ASCII - a correct German CV contains `Universität`, `für`, `Straße`, the `„…“` quotes the template emits via `\glqq`/`\grqq`, and `€` in any budget figure. Flag any character above U+024F, permitting U+00C0-U+00FF (umlauts, accents, ß), U+2010-U+2027 (hyphens, dashes, German quotes) and U+20AC (€). That still catches every defect this was written for: the U+FFFD fallback from moderncv's `0xB7` separator, the circle list marker, and FontAwesome glyph fallbacks. Do not tighten it back to ASCII - `tests/test_verify_pdf.py::CharacterPolicyTests` exists to stop exactly that.

  **Do not eyeball this in a Windows console.** PowerShell renders UTF-8 through a legacy OEM codepage, so correct output looks broken: `„` shows as `ÔÇ×` and `“` as `ÔÇ£`. Both are fine. Trust `tools/verify_pdf.py`, which decodes explicitly as UTF-8.
- **Contact details as literal text.** The contact icons are blanked in the preamble precisely so they cannot leak glyph names. Email, phone and both profile URLs must appear as printed text; `\href{...}{LinkedIn}` stores the address in a PDF annotation that most parsers never read.
- **No garbled output.** `(cid:NNN)` markers or `�` characters mean a font is embedded without a Unicode mapping - an ATS sees the same garbage.
- **Reading order, checked in raw mode.** Dates and locations must sit with their own entry. If they appear as a block after all entries, moderncv's two-column `\cventry` has been restored - re-apply the single-column override.
- **Keyword coverage.** Match the posting's required/preferred terms against the extracted text, in the posting's language. Prefer the posting's exact term over a synonym when it is truthfully applicable - ATS matching is often literal. Never add a keyword the profile does not support.

### Date fields must be ASCII ranges (confirmed ATS import failure)

This one is worth knowing about because it fails **silently**. A CV that passes every other check in this section - clean extraction, no `(cid:)` markers, contact details intact, correct reading order - can still have its dates dropped on import. In a real Workday resume import, a CV built from this template lost the end date of a short contract role and failed to import **any** education entry at all, forcing manual re-entry. Nothing about the PDF or its text layer looked wrong.

Two independent causes, both easy to avoid:

1. **`--` in a `\cventry` date renders as an en-dash (U+2013), not a hyphen.** LaTeX ligatures `--` (two ASCII hyphens, U+002D) into a single en-dash glyph, so `2016--2024` reaches the PDF text layer as `2016<U+2013>2024`. Many parsers split date ranges only on an ASCII hyphen and see no range at all. Write the date argument with a **single hyphen**:

   ```latex
   \item{\cventry{2016-2024}{Role Title}{Organization}{Location}{}{...}}   % parses
   \item{\cventry{2016--2024}{Role Title}{Organization}{Location}{}{...}}  % en-dash, may not
   ```

   This applies to the **date argument only**. Keep `--` everywhere it is typographically correct in prose, for example a numeric range like `EUR 600k--1M`.

2. **A bare single year gives the parser no end date.** A short contract, mandate or internship written as `\cventry{2016}` imports as a start date with nothing to close it. Use an explicit range, with months where the role ran under a year:

   ```latex
   \item{\cventry{Mar 2016 - Jul 2016}{Contract Role}{Client}{Location}{}{...}}
   ```

   Where a genuine range exists, use it even when a single year would be factually accurate - a degree written `1995` is true but imports worse than `1992-1995`. Do not invent a start date you do not have; a lone graduation year is fine, just expect it to be typed in by hand.

**Add this to the step 5d checks**: after extracting the text layer, confirm every experience entry shows a start *and* an end separated by an ASCII hyphen. Because the failure is silent and invisible in the PDF, the candidate otherwise discovers it only while filling in the application form.

## Page Budget - Prefer 1 Page, Hard 2-Page Limit

One page is the preferred target, not a reason to delete useful evidence. A second page is appropriate when the candidate has relevant experience, projects, education, or achievements that materially strengthen this specific application. The CV must never exceed 2 pages.

Use these as the one-page baseline. Expand selectively for a justified second page:

| Section | Max budget |
|---------|-----------|
| Kurzprofil | 3 lines |
| Kernkompetenzen | 4 items, 1 line each |
| Most recent role | 3 bullets |
| Previous role | 2 bullets |
| Projekte | 1 entry, 2 bullets |
| Ausbildung | 2 entries |
| Sprachen | 1 line |
| Auszeichnungen | commented out by default - restore only by cutting elsewhere |
| Publikationen | commented out - academic track only |
| References | **no section** - see below |

Before using page 2, remove duplication and low-signal filler. Do not remove unique, posting-relevant evidence merely to claim a one-page CV. Never squeeze margins, font size, or line spacing to force either target.

The second page is justified when at least one of these is true:

- a relevant earlier role adds evidence not present in the recent roles;
- a project, qualification, award, or publication directly supports a posting requirement;
- compressing to one page would turn concrete achievements into unsupported keyword lists.

It is not justified by repeated skills, generic responsibilities, references-on-request, or unrelated history.

## Relevance-weighted cutting (the right way to shrink a CV)

**Cut by signal, not by section.** Static priority lists ("remove oldest education first, then shorten the earliest role...") are wrong when a relevant "lower-priority" item is competing with an irrelevant "higher-priority" item. An older-role bullet that speaks directly to the posting is worth more than a recent-role bullet that does not.

For every candidate line, score three things:

1. **Relevance to THIS posting** — does the line hit a named tool, keyword, or stated responsibility in the job ad?
2. **Uniqueness** — is it the only place this claim appears, or is it duplicated elsewhere in the CV?
3. **Narrative load** — does the cover letter depend on it? If cutting the line would force you to rewrite a cover-letter paragraph, it is load-bearing.

Cut the lowest-total-score line first, regardless of which section it sits in.

### Practical order of cuts (easiest → last resort)

1. **Redundancy.** If an achievement appears in both Core Competencies AND a role bullet, the Core Competencies version is usually the cleaner cut (the experience bullet is more concrete evidence).
2. **Profile-statement fluff.** A sentence that just restates what Publications or Skills will show. ("Peer-reviewed publications on X..." is already a Publications entry — profile can claim it once and stop.)
3. **Low-relevance experience bullets.** A bullet about work that does not touch posting keywords, wherever it sits. This cuts across sections before touching the structural list.
4. **Low-relevance supporting content.** An older-role bullet that does not speak to the target role. A certification that does not touch the posting's stack. A language entry that can be condensed to one line.
5. **Low-relevance publications.** Keep 1-2 publications that best match the posting. Cut the rest before touching experience bullets.
6. **Last-resort structural cuts.** Oldest education entry, tightening an older role to 2 bullets, collapsing Certifications into a single line. These only happen if the relevance-weighted cuts above have already been exhausted.

### Pitfalls to avoid

- Do not mechanically cut from the bottom of a static section list without checking relevance. "Cut the oldest role first" is wrong if that role is literally about the skill the posting asks for.
- Do not cut the one concrete example the cover letter leans on. Relevance is measured against the cover letter you wrote, not just the job posting — interviewers will have read both.
- Do not cut to fit if the fit is borderline (2.02 pages). Prefer `\enlargethispage{2-3\baselineskip}` on a late section for near-misses; reserve content cuts for genuine overflow (content on page 3 that is more than a single trailing section).

## Recommended Section Order

**Default (technical / Werkstudent roles):**
1. Kurzprofil
2. Kernkompetenzen
3. Berufserfahrung (reverse chronological)
4. Projekte
5. Ausbildung (reverse chronological)
6. Sprachen

**For roles where the credential is the main qualifier:** move Ausbildung above Berufserfahrung. For a student with little work history, move Projekte above Berufserfahrung - it is the load-bearing section.

There is no References section, and Publikationen ships commented out for the academic track only.
