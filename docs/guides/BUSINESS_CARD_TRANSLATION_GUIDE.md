# Business Card Braille Translation Guide

> **Source:** BANA *Guidelines for Brailling Business Cards* — [Business Cards Fact Sheet](https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf), approved March 2024.
>
> **Do not edit the quoted BANA blocks in this file.** They are reproduced verbatim from the verified transcription in [`docs/guides/_bana_business_cards_verified_source.md`](./_bana_business_cards_verified_source.md). If BANA publishes a revised Fact Sheet, update the verified-source file first, then propagate downstream.

> **Status:** Flat business card generation is currently temporarily disabled while we improve this feature. This guide is preserved for when the feature returns. In the meantime, see [CYLINDER_GUIDE.md](CYLINDER_GUIDE.md) for creating braille cylinders (labels, containers).

This guide helps you create effective braille business cards using the Braille STL Generator. It quotes the Braille Authority of North America (BANA) Fact Sheet for every normative rule, and gives Grade 1 *"what to type into this app"* hints for each BANA example. **BANA's own published examples are Grade 2 (contracted) braille and are not reproduced here — see the Fact Sheet PDF for the originals.**

## The most important decision

> *"With only a few very short lines, it is often the transcriber's task to determine what will fit in the available space in order to help the client select which elements from the card will be brailled."* — BANA Fact Sheet, p. 2

Braille takes far more space than print — you cannot include everything from your print card. Use this self-test: *"Can someone identify me and contact me with just this information?"* If yes, you have enough. If no, add the minimum needed, nothing more.

## What fits on a card

> *"The typical business card stock used in the United States and Canada can accommodate 4 lines of braille with 13 or 14 cells each, depending on the equipment used to produce the cards. One strategy that can help is to use the fold-over style of business card stock that effectively doubles the writing surface of the card. In any event, there is usually far more print on the card than will fit in braille no matter how it is produced."* — BANA Fact Sheet, p. 1

| Constraint | BANA value |
|------------|------------|
| Lines available | 4 |
| Cells per line | 13 or 14 |
| Doubling option | Fold-over card stock |

## Selecting what to braille

BANA lists the elements typically found on a business card:

> - name
> - job title
> - organization/company
> - mailing address
> - phone
> - fax
> - cell
> - e-mail address
> - website
>
> *"There may be other elements as well, but those will almost certainly have to be omitted."* — BANA Fact Sheet, p. 1

The Fact Sheet's suggested four-line layout is:

> - first line: name
> - second line: organization/company
> - third line: phone number
> - fourth line: e-mail address
>
> *"The format of these lines should be planned considering the entire card, not just one line at a time."* — BANA Fact Sheet, p. 2

## Principles to follow

BANA's general principles, verbatim:

> - Follow *The Rules of Unified English Braille*.
> - Work with a UEB-certified transcriber.
> - Have a conversation with the owner of the business card so that they may decide which information is most important to convey.
> - When information needs to be pared down to fit within the available space, offer the client suggestions so that they can make an informed decision. — BANA Fact Sheet, p. 2

## Formatting rules (BANA, verbatim)

### Names

> *"In most cases, the person's name is essential. If the name will not fit on a 13- or 14-cell line, one option is to remove the capital indicators. If it still does not fit, remove the middle initial, if there is one. If it still will not fit, use an initial for the person's first name. Another option, if space is available, is to continue the person's name onto a second braille line beginning in cell 1."* — BANA Fact Sheet, p. 2

**In this app**, the order maps to typing decisions:

1. Remove capital indicators — type the name in lowercase, or leave the **Capitalized Letters** toggle disabled (default).
2. Remove the middle initial — type `Jane Smith` rather than `Jane M. Smith`.
3. Use an initial for the first name — type `J. Smith`.
4. Continue onto a second line in cell 1 — split the name across two of the four available lines.

### Organization or company

> *"Some indication of the name of the organization or company is usually desirable on a business card. However, this may be omitted, especially if the e-mail or web address contains the name of the company or organization. Other strategies, such as removing capital indicators, may also be used as needed. In the case of an organization or company name, abbreviating words such as 'lib' for 'library,' 'amer' for 'American,' or 'nat' for 'National' can work well."* — BANA Fact Sheet, p. 2

The only abbreviations BANA explicitly names are **lib**, **amer**, and **nat**. Treat these as the pattern (drop trailing letters; keep the start of the word recognizable) rather than an exhaustive list. The Fact Sheet does not name "Assoc" or "Univ"; they are commonly used in practice but are not endorsed by name in BANA's text.

### Phone numbers

> *"If the telephone number has no extension, then it can be brailled as follows: #123.456.7890. Omit extra characters such as parentheses. Convert the hyphens to periods to retain the natural sub-units of the phone number. This will maintain the ease of readability, while eliminating the need to repeat numeric indicators. Do not remove the numeric indicator unless absolutely necessary."* — BANA Fact Sheet, p. 3

**In this app**, type the phone number with period separators and no parentheses:

- Print `(123) 456-7890` → enter `123.456.7890`.
- Print `1-800-423-9826` → enter `1.800.423.9826`.

The numeric indicator (`#`) is added by the braille translator; do not type it yourself.

**Why only one number sign?** In UEB, a period (or comma) inside a number keeps numeric mode active, so the digits after it do not need another number sign (`⠼`). For example, `206.616.7678` translates to `⠼⠃⠚⠋⠲⠋⠁⠋⠲⠛⠋⠛⠓` — exactly 13 braille cells, which fits a default 13-cell row. This is what BANA means by "eliminating the need to repeat numeric indicators." Some online translators repeat the number sign after each period; that output is non-standard and uses extra cells. The app has an off-by-default **"Repeat number sign after each period in numbers (non-standard)"** toggle under the text input area if you need to match such output.

**Splitting a long number across two rows:** if a phone number will not fit on one row, divide it after a period and begin the next row with the remaining digits — the translator automatically adds a new number sign (`⠼`) at the start of the new row. For example, typing `206.616.` on one line and `7678` on the next produces `⠼⠃⠚⠋⠲⠋⠁⠋⠲` then `⠼⠛⠋⠛⠓`, the same pattern used in BANA's worked examples.

### E-mail addresses

> *"An e-mail address should be brailled according to The Rules of Unified English Braille. When an e-mail address must be divided over two lines, divide it after punctuation (e.g., the 'at' sign, a period, or a hyphen). An e-mail address may also be divided between syllables, or between alphabetic and numeric sub-units. The least desirable option is to divide an e-mail address between the letters of a syllable. Use the line continuation indicator (dot 5) at the end of the line to show that the e-mail address has been divided. As a last resort, omit the line continuation indicator. Begin the second line of the e-mail address in cell 1."* — BANA Fact Sheet, p. 3

BANA's three-tier division preference:

1. **After punctuation** — at sign, period, or hyphen.
2. **Between syllables, or between alphabetic and numeric sub-units.**
3. **Between the letters of a syllable** — least desirable; only when nothing else works.

The dot-5 line continuation indicator is preferred; omitting it is BANA's "last resort" fallback. The second line always begins in cell 1.

**In this app:**

- **Auto Placement** wraps your text. Where it splits is influenced by BANA's punctuation-first preference.
- **Manual Placement** puts you in control of the split. To split after `@`, type:

  ```
  harry@
  hogwarts.edu
  ```

  The dot-5 continuation indicator is a braille typographic detail the translator emits; you do not type it.

### Web addresses

> *"A web address should be brailled according to The Rules of Unified English Braille. When a web address must be divided over two lines, divide it after punctuation (e.g., a colon, a period, or a slash). A web address may also be divided between syllables, or between alphabetic and numeric sub-units. The least desirable option is to divide a web address between the letters of a syllable. Use the line continuation indicator (dot 5) at the end of the line to show that the web address has been divided. As a last resort, omit the line continuation indicator. Begin the second line of the web address in cell 1."* — BANA Fact Sheet, p. 3

Same shape as the e-mail rule, with the preferred division points being colon, period, and slash. If the domain is clear without it, omit `https://` or `www.` to save cells.

## Worked examples — BANA Grade 2 braille + Grade 1 "what to type"

Each example below shows three things, in order:

1. **Print card** — what was on the original print business card.
2. **BANA Grade 2 braille** — the cells BANA published in the Fact Sheet, reproduced verbatim in Unicode (U+2800–U+28FF) from the verified visual transcription. **Best viewed in a system font that has good support for Unicode braille** (Segoe UI Symbol, Apple Symbols, DejaVu Sans, etc. — most modern OSes render these glyphs out of the box).
3. **What to type in this app** — Grade 1 "what to type" hint that captures BANA's content decisions (which fields to omit, how to split a name); the app then translates this with liblouis.

BANA's published braille is Grade 2 (contracted). This app defaults to Grade 1 (uncontracted) for clarity on names and contact info, so the cells the app emits will look different from BANA's even when the *content decisions* match.

### Example 1 — Omit organization (appears in e-mail domain), wrap e-mail

**Print card:** Harry Potter / Hogwarts School / harry@hogwarts.edu

BANA strategy: omit capitals from the organization; divide the e-mail address.

**BANA Grade 2 braille:**

```
⠠⠓⠜⠗⠽ ⠠⠏⠕⠞⠞⠻
⠓⠕⠛⠺⠜⠞⠎ ⠎⠡⠕⠕⠇
⠓⠜⠗⠽⠈⠁⠐
⠓⠕⠛⠺⠜⠞⠎⠲⠫⠥
```

**Type into this app:**

```
harry potter
harry@hogwarts.edu
```

### Example 2 — Abbreviate job title, modify phone

**Print card:** Indra Jackson / AlcotteAmerica / Services Representative / 800-929-1733

BANA strategy: omit capitals from organization; abbreviate job title; convert phone hyphens to periods.

**BANA Grade 2 braille:**

```
⠠⠔⠙⠗⠁ ⠠⠚⠁⠉⠅⠎⠕⠝
⠁⠇⠉⠕⠞⠞⠑⠁⠍⠻⠊⠉⠁
⠠⠎⠻⠧⠊⠉⠑⠎ ⠠⠗⠑⠏⠲
⠼⠓⠚⠚⠲⠊⠃⠊⠲⠁⠛⠉⠉
```

**Type into this app:**

```
indra jackson
alcotteamerica
services rep.
800.929.1733
```

### Example 3 — Abbreviate organization, modify phone

**Print card:** J. Christopher / Braille Instructor / Texas School for the Blind / (512) 454-8631

BANA strategy: abbreviate organization (`tx sch for the bl`); convert phone format.

**BANA Grade 2 braille:**

```
⠰⠠⠚ ⠠⠡⠗⠊⠌⠕⠏⠓⠻
⠃⠗⠇ ⠔⠌⠗⠥⠉⠞⠕⠗
⠞⠭ ⠎⠡⠇ ⠿ ⠮ ⠃⠇
⠼⠑⠁⠃⠲⠙⠑⠙⠲⠓⠋⠉⠁
```

**Type into this app:**

```
j. christopher
braille instructor
tx sch for the bl
512.454.8631
```

### Example 4 — Long name spans two lines, omit organization and phone

**Print card:** Liesel A. Schimmelfennig / US Army Corps of Engineers / Southwest Division / l.schimmelfennig@usace.army / 1-520-670-6277

BANA strategy: continue the name onto a second line in cell 1; omit organization (in e-mail); divide the e-mail address; omit the continuation indicator (last-resort fallback); omit phone.

**BANA Grade 2 braille:**

```
⠠⠇⠊⠑⠎⠑⠇ ⠠⠁⠲
⠠⠎⠡⠊⠍⠍⠑⠇⠋⠢⠝⠊⠛
⠇⠲⠎⠡⠊⠍⠍⠑⠇⠋⠢⠝⠊⠛
⠈⠁⠥⠎⠁⠉⠑⠲⠜⠍⠽
```

**Type into this app:**

```
liesel a.
schimmelfennig
l.schimmelfennig@usace.army
```

### Example 5 — Very long surname wraps, omit company

**Print card:** Rupert Wolfeschlegelsteinhausen / Galaxy Printing Co. / rupert@galaxyprinting.com

BANA strategy: first name reduced to an initial; surname wraps with the dot-5 continuation indicator; omit the company name (in e-mail).

**BANA Grade 2 braille:**

```
⠰⠗ ⠺⠕⠇⠋⠑⠎⠡⠇⠑⠛⠑⠇⠐
⠌⠑⠔⠓⠁⠥⠎⠢
⠗⠥⠏⠻⠞⠈⠁⠛⠁⠇⠁⠭⠽⠐
⠏⠗⠔⠞⠬⠲⠉⠕⠍
```

**Type into this app:**

```
r. wolfeschlegel
steinhausen
rupert@galaxyprinting.com
```

### Example 6 — Hyphenated surname split, omit company

**Print card:** Jennifer Lynnzes-Sleightower, OD / Midwest Eye Center / sleightower@midwesteye.com

BANA strategy: divide the hyphenated surname between lines 1 and 2; omit capitals from post-nominal credentials; omit the organization (in e-mail).

**BANA Grade 2 braille:**

```
⠠⠚⠢ ⠠⠇⠽⠝⠝⠵⠑⠎⠤
⠠⠎⠇⠑⠊⠣⠞⠪⠻⠂ ⠕⠙
⠎⠇⠑⠊⠣⠞⠪⠻⠈⠁⠐
⠍⠊⠙⠺⠑⠌⠑⠽⠑⠲⠉⠕⠍
```

**Type into this app:**

```
jen lynnzes-
sleightower, od
sleightower@midwesteye.com
```

### Example 7 — Nickname instead of capital-stripping; cell vs. fax

**Print card:** Francine (Fran) Rikard / Albuquerque AC / 505-312-4224 (cell) / 505-312-4225 (fax)

BANA strategy: client chose the nickname "Fran" rather than removing the capital indicators from "Francine"; convert phone format; tag cell/fax with a one-letter prefix.

**BANA Grade 2 braille:**

```
⠠⠋⠗⠁⠝ ⠠⠗⠊⠅⠜⠙
⠁⠇⠃⠥⠟⠥⠻⠟⠥⠑ ⠰⠁⠉
⠉⠼⠑⠚⠑⠲⠉⠁⠃⠲⠙⠃⠃⠙
⠋⠼⠑⠚⠑⠲⠉⠁⠃⠲⠙⠃⠃⠑
```

**Type into this app:**

```
fran rikard
albuquerque ac
c 505.312.4224
f 505.312.4225
```

### Example 8 — International phone, abbreviated work title

**Print card:** Timaru Brailleworks / Jody Day, Proprietor / cell: +64 3 027 864 536

BANA strategy: omit job title; divide and modify the international phone number.

**BANA Grade 2 braille:**

```
⠠⠞⠊⠍⠜⠥ ⠠⠃⠗⠇⠐⠺⠎
⠠⠚⠕⠙⠽ ⠠⠐⠙
⠉⠑⠇⠇⠒ ⠐⠖⠼⠋⠙ ⠼⠉
⠼⠚⠃⠛⠲⠓⠋⠙⠲⠑⠉⠋
```

**Type into this app:**

```
timaru brailleworks
jody day
cell: +64 3 027
864.536
```

### Example 9 — Web address split between numeric and alphabetic units

**Print card:** Pablo Ruíz Pocket Calendars / DIY2023calendars.com / 1-800-423-9826

BANA strategy: omit some capitals; divide the web address between the numeric and alphabetic units; omit the phone number.

**BANA Grade 2 braille:**

```
⠠⠏⠁⠃⠇⠕ ⠠⠗⠥⠘⠌⠊⠵
⠏⠕⠉⠅⠑⠞ ⠉⠁⠇⠢⠙⠜⠎
⠠⠠⠙⠊⠽⠼⠃⠚⠃⠉⠰⠄⠐
⠉⠁⠇⠢⠙⠜⠎⠲⠉⠕⠍
```

**Type into this app:**

```
pablo ruiz
pocket calendars
diy2023
calendars.com
```

(Note: the accented `í` in "Ruíz" is rendered by the translator according to UEB's accented-letter rules; type plain `ruiz` if your input method does not produce `í` and the translator falls back gracefully.)

## When to seek help

Consider consulting a UEB-certified transcriber for:

- International phone numbers with complex formatting
- Multiple languages on one card
- Technical credentials or post-nominal letters (PhD, CPA, etc.)
- Large organizations with formal naming requirements
- Legal or medical contexts requiring exact formatting

This restates BANA's "Work with a UEB-certified transcriber" principle (p. 2) in concrete terms.

## Using the application

### Preview before generating

The **Preview Braille Translation** button is inside Expert Mode:

1. Click **Show Expert Mode** on the main page.
2. Click **Preview Braille Translation** at the top of the Expert Mode panel.
3. Review any warnings about text length or character issues.

### Capitalized Letters toggle

| State | Behaviour | When to use |
|-------|-----------|-------------|
| Disabled (default) | Text is converted to lowercase before translation; no braille capital indicators are inserted | Standard for space-constrained business cards (matches BANA's "remove the capital indicators" strategy) |
| Enabled | Capitals are preserved; each adds one indicator cell | When the card owner has explicitly asked for capitalization |

### Recommended settings

| Setting | Value | Reason |
|---------|-------|--------|
| Placement Mode | Auto Placement | Handles wrapping automatically and applies BANA's punctuation-first division preference where it can |
| Language | English (UEB) — uncontracted (grade 1) | Clearer for names, e-mail, and contact info |
| Capitalized Letters | Disabled | Saves cells per BANA's "remove the capital indicators" strategy |
| Braille Cells | 13 | Matches BANA's lower bound for typical card stock |
| Braille Lines | 4 | BANA's typical layout |
| Indicator Shapes | On | Reserves two cells so braille readers can locate row start/end |

### When to use Grade 2 (contracted)

BANA's worked examples are Grade 2. Use it only when:

- You have exhausted the space-saving strategies in the "Names" and "Organization" sections above
- The card owner understands contracted braille will be used
- The content is mostly common English words

Contracted braille can make names, e-mail addresses, and web addresses harder to read because their letter sequences may collide with English contractions.

## Resources

### Official standards

- [BANA Position Statements and Fact Sheets](https://www.brailleauthority.org/bana-position-statements-and-fact-sheets) — includes the official Business Cards Fact Sheet
- [Business Cards Fact Sheet (PDF, approved March 2024)](https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf) — authoritative source for everything quoted in this guide
- [BANA Braille Signage Guidelines](https://www.brailleauthority.org/braille-signage-guidelines)
- [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters)
- [The Rules of Unified English Braille (ICEB)](https://iceb.org/ueb.html)

### Acknowledgements

Quoted material reproduced from the *Business Cards Fact Sheet* (approved March 2024) published by the Braille Authority of North America (BANA). Braille translation powered by [liblouis](https://liblouis.io/).

---

*Last verified against the BANA Fact Sheet: May 2026. The verified visual transcription is at [`_bana_business_cards_verified_source.md`](./_bana_business_cards_verified_source.md).*
