# Business Card Braille Translation Guide

> **Note:** Flat business card generation is currently **temporarily disabled** while we improve this feature. This guide is preserved for when the feature returns. In the meantime, see [CYLINDER_GUIDE.md](CYLINDER_GUIDE.md) for creating braille cylinders (labels, containers).

This guide helps you create effective braille business cards using the Braille STL Generator. It follows guidance from the Braille Authority of North America (BANA).

## The Most Important Decision

> **Before using any tool:** Decide what information to include. Braille takes far more space than print — you cannot include everything from your print card.
>
> **The test:** *"Can someone identify me and contact me with just this information?"* If yes, you have enough. If no, add the minimum needed — nothing more.

## Quick Reference

| Constraint | Value |
|------------|-------|
| Lines available | ~4 |
| Cells per line | ~13-14 |
| Typical content | Name, org, phone, email |

## What Fits on a Business Card

Standard business card stock in the United States and Canada accommodates approximately **4 lines of braille with 13 or 14 cells each**, depending on the equipment used. This is significantly less space than what's typically on a print business card.

**Key insight:** Not everything from your print card will fit. You must prioritize.

### Typical Print Business Card Contains:

- Name
- Job title
- Organization/company
- Mailing address
- Phone (office, cell, fax)
- Email address
- Website

### What Usually Fits in Braille:

| Line | Content | Priority |
|------|---------|----------|
| 1 | Name | Essential |
| 2 | Organization/company | High (can omit if in email) |
| 3 | Phone number | High |
| 4 | Email address | High |

## Step-by-Step Selection Process

### Step 1: Identify Essential Information

Ask yourself: *"What does someone need to identify me and contact me?"*

**Almost always include:**
- Your name (essential)
- One contact method (phone OR email)

**Include if space allows:**
- Organization (unless clear from email/web address)
- Second contact method

**Usually omit:**
- Job title
- Mailing address
- Fax number
- Website (unless critical to your work)

### Step 2: Check if It Fits

1. Enter your text in the Braille STL Generator
2. Use **Auto Placement** mode
3. Click **Preview Braille Translation**
4. Review warnings about line/cell limits

### Step 3: Apply Space-Saving Strategies

If your content doesn't fit, apply these strategies in order:

| Strategy | How | Savings |
|----------|-----|---------|
| Remove capitals | Type in lowercase | ~1 cell per capital |
| Remove middle initial | "Jane Smith" not "Jane M. Smith" | 3+ cells |
| Use first initial only | "J. Smith" | Several cells |
| Abbreviate common words | "Lib" for Library, "Amer" for American | Variable |
| Omit organization | If in email/web address | Many cells |
| Use fold-over card | Doubles available space | 4+ more lines |

## Formatting Guidelines

### Phone Numbers

**Best practice:** Use periods as separators.

| Format | Braille Efficiency |
|--------|-------------------|
| `(123) 456-7890` | Poor — parentheses waste space |
| `123-456-7890` | OK |
| `123.456.7890` | **Best** — periods preserve groupings without extra indicators |

**Why periods?** In braille, periods between number groups maintain readability while avoiding repeated numeric indicators.

**Example transformation:**
- Print: `(123) 456-7890`
- Enter as: `123.456.7890`
- Braille: `#123.456.7890` (with one numeric indicator at start)

### Email Addresses

If an email must span two lines, split at a sensible point:

**Best split points (in order of preference):**
1. After `@` symbol
2. After a period
3. After a hyphen
4. Between syllables
5. Between alphabetic and numeric parts

**Avoid:** Splitting in the middle of a syllable

**How to handle wrapping:**
- **Auto Placement mode:** The app handles wrapping automatically. It will split at appropriate points.
- **Manual Placement mode:** If you need to control the split, put each portion on a separate line.

**Example — manually splitting after @:**
```
harry@
hogwarts.edu
```

*Note: In proper braille transcription, a continuation indicator (dot 5) appears at the end of a split line. This is a transcription detail — focus on choosing good split points.*

### Web Addresses

Same rules as email addresses. Split after:
1. Colon (`:`)
2. Period (`.`)
3. Slash (`/`)

**Space-saving tip:** Omit `https://` or `www.` if the domain is clear without it.

### Names

If a name is too long:

| Option | Example | Use When |
|--------|---------|----------|
| Remove capitals | `jane smith` | First attempt |
| Remove middle initial | `Jane Smith` not `Jane M. Smith` | Still too long |
| First initial only | `J. Smith` | Still too long |
| Span two lines | Line 1: first name, Line 2: surname | Last resort |

**Client choice matters:** Some people prefer keeping capital indicators on their name and shortening elsewhere. Discuss options with the card owner.

### Organization Names

Strategies for long organization names:

| Strategy | Example |
|----------|---------|
| Remove capitals | `national library association` |
| Abbreviate common words | `nat lib assoc` |
| Omit entirely | If appears in email/web address |

**Common abbreviations:**
- `Lib` for Library
- `Amer` for American
- `Nat` for National
- `Assoc` for Association
- `Univ` for University

## Worked Examples

These examples are adapted from the official BANA *Business Cards Fact Sheet*. They show **what to type** into the application, not braille output notation.

### Example 1: Standard Business Card (Fits Well)

**Print card:**
```
Jane Doe
Acme Corporation
555.123.4567
jane.doe@acme.com
```

**Strategy:** Standard 4-line layout.

**What to type:**
```
jane doe
acme corporation
555.123.4567
jane.doe@acme.com
```

**Result:** Fits in 4 lines with Capitalized Letters disabled (default).

---

### Example 2: Organization in Email Domain

**Print card:**
```
Harry Potter
Hogwarts School
harry@hogwarts.edu
```

**Strategy:** 
- Omit organization entirely — "hogwarts" appears in email domain
- This saves a full line for other content or shorter wrapping

**What to type:**
```
harry potter
harry@hogwarts.edu
```

**Result:** Fits in 2-3 lines (email may wrap). Organization omitted because it's redundant with email domain.

---

### Example 3: Long Name

**Print card:**
```
Liesel A. Schimmelfennig
US Army Corps of Engineers
l.schimmelfennig@usace.army
1-520-670-6277
```

**Strategy:**
- Name is unavoidably long — will span 2 lines
- Omit organization (appears in email domain "usace.army")
- Omit phone (email provides sufficient contact)

**What to type:**
```
liesel a. schimmelfennig
l.schimmelfennig@usace.army
```

**Result:** Fits in 3-4 lines. Organization and phone omitted.

---

### Example 4: Nickname Option

**Print card:**
```
Francine (Fran) Rikard
Albuquerque AC
505-312-4224 (cell)
505-312-4225 (fax)
```

**Strategy:**
- Client chose nickname "Fran" to keep the name short
- Convert phone hyphens to periods
- Use `c` and `f` prefixes to distinguish cell/fax

**What to type:**
```
fran rikard
albuquerque ac
c 505.312.4224
f 505.312.4225
```

**Result:** Fits in 4 lines. Full first name replaced with nickname per client preference.

---

### Example 5: Abbreviation Strategy

**Print card:**
```
J. Christopher
Braille Instructor
Texas School for the Blind
(512) 454-8631
```

**Strategy:**
- Abbreviate organization: "tx schl for the blind" or "tx sch bl"
- Abbreviate job title if needed
- Convert phone format

**What to type:**
```
j. christopher
braille instructor
tx sch for the blind
512.454.8631
```

**Result:** Fits in 4 lines using standard abbreviations.

---

### Notes on These Examples

- **Capitalized Letters disabled (default):** The app automatically converts to lowercase for braille translation, so you can type naturally.
- **Grade 1 uncontracted:** These examples assume Grade 1 (uncontracted) braille, which is recommended for names and contact info.
- **BANA source examples use Grade 2:** The original BANA examples use contracted braille, which produces shorter output but is harder to read for names. We adapted them for Grade 1.

## When to Seek Help

Consider consulting a **UEB-certified transcriber** for:

- International phone numbers with complex formatting
- Multiple languages on one card
- Technical credentials or post-nominal letters (PhD, CPA, etc.)
- Large organizations with formal naming requirements
- Legal or medical contexts requiring exact formatting

## Using the Application

### Important: Preview Before Generating

The **Preview Braille Translation** button is located inside **Expert Mode**. To access it:

1. Click **Show Expert Mode** on the main page
2. Click **Preview Braille Translation** at the top of the Expert Mode panel
3. Review any warnings about text length or character issues

### Capitalized Letters Toggle

The **Capitalized Letters** toggle controls how capitals are handled:

- **Disabled (default):** Text is automatically converted to lowercase before translation. You can type normally — capitals are converted for you.
- **Enabled:** Capital letters are preserved, adding indicator cells to the braille output.

**Why disable capitals?** Saves approximately 1 braille cell per capital letter. Braille readers understand this is standard practice for space-limited applications.

### Recommended Settings

| Setting | Recommended Value | Reason |
|---------|-------------------|--------|
| Placement Mode | Auto Placement | Handles wrapping automatically |
| Language | English (UEB) — uncontracted (grade 1) | Clearer for names and contact info |
| Capitalized Letters | Disabled | Saves space (default; recommended) |
| Braille Cells | 13 | Standard with indicators |
| Braille Lines | 4 | Standard card |
| Indicator Shapes | On | Helps readers find row start/end |

### When to Use Grade 2 (Contracted)

Use contracted braille only when:
- You've exhausted all other space-saving strategies
- The card owner understands contracted braille will be used
- The content is mostly common English words (names may contract unexpectedly)

**Caution:** Contracted braille can make names and email addresses harder to read.

## Resources & Credits

### Official Standards

- [BANA Position Statements and Fact Sheets](https://www.brailleauthority.org/bana-position-statements-and-fact-sheets) — includes the official Business Cards Fact Sheet
- [Business Cards Fact Sheet (PDF)](https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf) — official BANA guidance (approved March 2024)
- [BANA Braille Signage Guidelines](https://www.brailleauthority.org/braille-signage-guidelines)
- [BANA Size and Spacing of Braille Characters](https://www.brailleauthority.org/size-and-spacing-braille-characters)
- [The Rules of Unified English Braille (ICEB)](https://iceb.org/ueb.html)

### Acknowledgments

Business card guidance is adapted from the [*Business Cards Fact Sheet*](https://www.brailleauthority.org/sites/default/files/2024-10/Business%20Cards%20Fact%20Sheet.pdf) (approved March 2024) published by the Braille Authority of North America (BANA).

Braille translation powered by [liblouis](https://liblouis.io/).

---

*Document Version: 1.0*
*Last Updated: January 2026*
