---
framework_version: 2.0.0
---

# Cover Letter Template and Tailoring Guide (DIN 5008 Form B)

## Template: KOMA-Script `scrlttr2`

German application letters follow **DIN 5008 Form B**, which fixes the zones of the page head in millimetres from the top paper edge. `scrlttr2` knows those zones as pseudo-lengths and positions them itself: you set variables instead of placing boxes.

**Do not build this in moderncv or a hand-rolled class.** moderncv's letter support does not follow DIN 5008, and a hand-positioned layout drifts the moment the content length changes — which is exactly the failure you cannot see in the source and will not notice in the PDF until a recruiter does.

**Output file:** `cover_letters/cover_<company>_<role>.tex`
**Compile with:** XeLaTeX (the template uses `fontspec`)
**Reference:** `cover_letters/cover_example.tex`

### Compile command

```bash
cd cover_letters && xelatex -interaction=nonstopmode cover_<company>_<role>.tex
cd cover_letters && xelatex -interaction=nonstopmode cover_<company>_<role>.tex
```

Run it **twice** — a single run ends with `rerunfilecheck` and `hyperref` warnings asking for a second pass.

Then check the log for silent font substitutions before trusting the PDF:

```bash
cd cover_letters && grep 'Font shape' cover_<company>_<role>.log
```

Expected output: `Output written on cover_<company>_<role>.pdf (1 page, ...)`. **Any page count other than 1 is a failure.**

## Page geometry

Margins: top 4.5 cm, left 2.5 cm, right 2.0 cm, bottom 2.0 cm. Single line spacing.

The 2.5 cm left margin is not a style choice — it is the punch margin, so the letter can be filed without holes eating the text.

| Zone | Starts at | Height | Contains |
|---|---|---|---|
| Briefkopf | 0 mm | — | Your name and contact details |
| Zusatz-/Vermerkzone | 45 mm | 17.7 mm | Small return-address line, usually one line. Filled **from the bottom up**, so it sits flush against the address field below |
| Anschriftzone | 62.7 mm | 27.3 mm | Recipient address, **max 6 lines** |
| Betreff und Text | ca. 97 mm | — | Subject, salutation, body |

These are set in the template's pseudo-length block (`toaddrvpos`, `toaddrheight`, `toaddrhpos`, `backaddrheight`, `refvpos`). They match `DIN.lco`'s defaults; they are written out explicitly so the measurements are visible in the file and a change to the `.lco` cannot silently shift the form.

### Font

DIN 5008 names **Arial 11 pt** or **Times 12 pt**. The template defaults to **TeX Gyre Heros** — a Helvetica clone, metrically compatible with Arial, shipped with every TeX distribution. Arial does not exist on Linux build machines, so defaulting to it would break CI.

For real Arial locally, replace the `\setmainfont{texgyreheros}[...]` block with `\setmainfont{Arial}`.

## Block order, top to bottom

1. **Your details.** Name, address, phone, email. Right- or left-aligned — either is DIN-conformant. Keep it consistent with the CV header.
2. **Recipient.** Company, then contact person, then street, then postcode and city. **No `An`, no `Firma`.** Academic degrees go *after* the name: `Vorname Nachname B. Sc.`, never before it.
3. **Ort und Datum.** Right-aligned, one blank line below the address field. `Siegen, 12. August 2026`. The numeric form `12.08.2026` is permitted but reads as less formal.
4. **Betreff.** Bold. No `Betreff:` prefix, no underline, **no full stop at the end.** Two blank lines between date and subject, two more between subject and salutation. Content: the exact job title from the posting, plus the reference number if there is one.
5. **Anrede.** `Sehr geehrte Frau [Name],` — find a named person wherever you can. `Sehr geehrte Damen und Herren,` only when you genuinely cannot.
6. **Body.** Three to four paragraphs, see below.
7. **Grußformel.** `Mit freundlichen Grüßen`.
8. **Signature.** A scanned signature image, then your typed name below it.
9. **Anlagen.** The word in **bold**, with **no colon** after it.

Body text is **left-aligned, ragged right — never justified.** Same rule as the CV, same reason: justification forces hyphenation that splits German compounds across the line break.

## What goes in the body

**Paragraph 1 — the opener.** Why *this* company. Never `hiermit bewerbe ich mich`, and never a restatement of the job title, which is already in the Betreff. Name something concrete about what they build or who they build it for. This paragraph is skimmed hardest, so it must contain a fact that could only apply to this employer.

**Paragraph 2 — the evidence.** Two or three claims, each attached to something actually done. Not a list of skills. The shape is *"In X habe ich Y gebaut, was Z bewirkt hat."*

**Paragraph 3 — the fit.** How the evidence maps to what they need. If a listed requirement is genuinely missing, address it here in **one sentence** and move on. Do not apologise, do not spend a paragraph on it.

**Paragraph 4 — the close.** Availability, start date, hours per week. Salary expectation **only if the posting asked for one.** Then a direct request for a conversation. Avoid the subjunctive — `würde mich freuen` is weak; `Über ein Gespräch freue ich mich` is direct without being pushy.

### Length

**One page, always. No exceptions.** If it does not fit, cut paragraph 2 — never the margins. Shrinking the geometry breaks DIN conformance to hide a content problem.

## Language: follow the posting, not the employer

**An English-language posting gets an English letter, even at a German employer.** The posting's language is the instruction; the company's location is not.

The DIN 5008 layout stays correct in both cases — it is a letter *format*, not a language. A German employer advertising in English still receives post in DIN envelopes. Only for an employer outside the German-speaking world should you also drop the `backaddress` return line, which is a German postal convention.

Switching the template is one block at the top:

```latex
% \usepackage[english]{babel}
% \renewcaptionname{english}{\enclname}{\textbf{Enclosures}}
```

Both lines live together at the top so a language switch touches one place. Do **not** try to factor the language name into a macro and pass it to `\renewcaptionname` — that argument is used to build a control sequence name and will not expand.

Four things live in the body text and must be changed by hand:

| German | English |
|---|---|
| `Sehr geehrte Frau [Name],` | `Dear Ms [Name],` |
| `Mit freundlichen Grüßen` | `Kind regards,` |
| `Bewerbung als [Stelle]` | `Application for [Role]` |
| `12. August 2026` | `12 August 2026` |

The CV switches the same way — its section names are macros in one block, with the English values shipped commented out. Note that `\glqq`/`\grqq` come from babel-ngerman and are **undefined** under `[english]`; the CV's profile-statement example uses them, so swap those for plain quotes or the run aborts.

## Informatik vs BWL

The layout is identical. The weight is not.

**Informatik.** The Anschreiben is secondary. Recruiters read the CV first and use the letter to check that you write coherently and understand what the company sells. Three paragraphs is fine; let the projects carry the argument. In this segment the letter mostly exists to prove you did not mass-apply.

**BWL**, especially anything consulting-adjacent. The letter carries real weight and is read properly — it is closer to a short argument for your candidacy. Four paragraphs, more attention to phrasing. Grades and structured reasoning matter more than on the tech side.

## Key commands

| Command | Purpose |
|---|---|
| `\setkomavar{fromname}{...}` | Briefkopf name |
| `\setkomavar{fromaddress}{...}` | Briefkopf address (`\\` between lines) |
| `\setkomavar{backaddress}{...}` | One-line return address in the Vermerkzone |
| `\setkomavar{place}{...}` / `{date}{...}` | Ort und Datum |
| `\setkomavar{subject}{...}` | Betreff |
| `\setkomavar{signature}{...}` | Typed name below the signature |
| `\begin{letter}{...}` | Recipient address block |
| `\opening{...}` / `\closing{...}` | Anrede / Grußformel |
| `\encl{...}` | Anlagen |

## Pitfalls

**`\\[` swallows the next placeholder.** Address blocks are written one line per `\\`, and `\\` takes an optional vertical-space argument. So `\\[PLZ Ort]` is read as "line break, then a space of *PLZ Ort*" — the brackets vanish, or the line does. Write `\\{}[PLZ Ort]`. Whitespace and newlines between `\\` and `[` do **not** help; LaTeX skips them while scanning for the optional argument. This is the same trap as `\item [Text]` in the CV.

**Compile without `-halt-on-error` and this hides.** `nonstopmode` alone lets LaTeX recover from the resulting "Illegal unit of measure" and produce a PDF that looks nearly right. Always check the log:

```bash
cd cover_letters && grep -n '^!' cover_<company>_<role>.log
```

**The `Anlagen` label comes from `\enclname`, not from the KOMA variable.** `\setkomavar*{encl}{\textbf{Anlagen}}` has no effect — the letter keeps printing `Anlage(n)` — even though `\setkomavar{enclseparator}{}` on the very next line *does* remove the colon. That split is the giveaway: the separator is a variable, the label is a language name. Use `\renewcaptionname{ngerman}{\enclname}{\textbf{Anlagen}}`, which is KOMA's mechanism for language-dependent names and survives babel.

If that still prints `Anlage(n)`, drop `\encl{...}` and set the block by hand — deterministic, no variable machinery:

```latex
\vspace{\baselineskip}
\noindent\textbf{Anlagen}\\{}[Lebenslauf, Zeugnisse]
```

**Subject spacing stacks with `parskip`.** `parskip=full` already inserts a full blank line between blocks, so `subjectbeforevskip`/`subjectaftervskip` of `2\baselineskip` produce roughly four blank lines, not the two DIN 5008 wants. `1\baselineskip` each is correct with this `parskip` setting. Measure it on the compiled page rather than trusting the source.

**The signature image is never committed.** `*.png` and `*.jpg` are in `.gitignore`, and a scanned signature does not belong in a public repo. Keep the file locally and uncomment the `\includegraphics` line in `\setkomavar{signature}{...}`.

**Six lines is a hard cap on the address block.** The Anschriftzone is 27.3 mm. A seventh line overflows into the Betreff zone and breaks the form.

**Do not add `\usepackage{setspace}` to force a fit.** DIN 5008 specifies single spacing. If the letter overruns, the content is too long.

## Checklist before finalizing

- [ ] Compiles with **xelatex**, run twice, exactly **1 page**
- [ ] `grep 'Font shape'` on the log returns nothing
- [ ] Recipient block is at most 6 lines, no `An`/`Firma`, degrees after the name
- [ ] Betreff is bold, carries the exact job title and reference number, has no full stop
- [ ] Salutation names a real person wherever one could be found
- [ ] Opening paragraph contains a verified, company-specific fact — not a generic claim
- [ ] Every claim in paragraph 2 is attached to something actually done
- [ ] Any genuine gap is handled in one sentence, without apology
- [ ] Salary expectation present **only** if the posting asked
- [ ] No subjunctive in the closing
- [ ] `Anlagen` is bold with no colon
- [ ] Body is ragged right, not justified
- [ ] No em-dashes, no clichés, no filler
- [ ] Company name and role correct throughout; date current
- [ ] Language matches the posting
