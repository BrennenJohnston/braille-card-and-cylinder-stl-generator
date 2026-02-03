# Business Card Braille Translation Guide

> **Note:** Flat business card generation is currently **temporarily disabled** while we improve this feature. This guide is preserved for when the feature returns. In the meantime, see [CYLINDER_GUIDE.md](CYLINDER_GUIDE.md) for creating braille cylinders (labels, containers).

This guide helps you create effective braille business cards using the Braille STL Generator. It follows guidance from the Braille Authority of North America (BANA).

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

If an email must span two lines:

**Preferred split points (in order):**
1. After `@` symbol
2. After a period
3. After a hyphen
4. Between syllables
5. Between alphabetic and numeric parts

**Least preferred:** Splitting within a syllable

**Continuation indicator:** Use dot 5 at the end of the first line to show the address continues. Start the continuation at cell 1.

**Example:**

```
harry@"
hogwarts.edu
```

(The `"` at line end represents the continuation indicator, dot 5)

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

### Example 1: Standard Business Card (Fits Well)

**Print card:**
```
Jane Doe
Acme Corporation
555.123.4567
jane.doe@acme.com
```

**Strategy:** Standard 4-line layout, lowercase to save capitals.

**Result:** Fits in 4 lines.

---

### Example 2: Organization in Email

**Print card:**
```
Harry Potter
Hogwarts School
harry@hogwarts.edu
```

**Strategy:** 
- Omit capitals from organization (saves cells)
- Organization can be omitted entirely since "hogwarts" appears in email
- Wrap email after `@` if needed

**Braille result (4 lines):**
```
,harry ,potter
hogwarts school
harry@"
hogwarts.edu
```

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
- Name spans 2 lines (unavoidable)
- Omit organization (appears in email domain "usace.army")
- Omit phone if needed (email provides contact)

**Braille result (4 lines):**
```
,liesel ,a.
,schimmelfennig
l.schimmelfennig
@usace.army
```

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
- Client chose nickname "Fran" to keep capitals on name
- Organization in lowercase
- Use `c` prefix for cell, `f` for fax
- Use periods in phone numbers

**Braille result (4 lines):**
```
,fran ,rikard
albuquerque ac
c#505.312.4224
f#505.312.4225
```

---

### Example 5: International Phone Number

**Print card:**
```
Timaru Brailleworks
Jody Day, Proprietor
cell: +64 3 027 864 536
```

**Strategy:**
- Omit "Proprietor" title
- Split international number thoughtfully
- Use abbreviation "brlwks" or similar

**Braille result (4 lines):**
```
,timaru ,brlwks
,jody ,day
cell "+#64.3"
#027.864.536
```

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
