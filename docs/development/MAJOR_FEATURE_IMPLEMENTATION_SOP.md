# Major Feature Implementation - Standard Operating Procedure (SOP)

## Document Purpose

This document provides a standardized roadmap for implementing major features in the Braille Card and Cylinder STL Generator. It captures the proven workflow established during the Card Thickness Preset System implementation (2025-12-07) and ensures consistency, completeness, and quality for all future feature additions.

**Target Audience:**
- Contributors
- Junior developers
- Senior developers implementing large features
- Code reviewers

**Scope:**
- Major UI features affecting multiple parameters
- New user-facing functionality
- Features requiring specification documentation
- Features affecting existing architecture

---

## Quick Reference: Implementation Checklist

```
Phase 1: Investigation & Planning
├── [ ] Understand user requirements
├── [ ] Read SPECIFICATIONS_INDEX.md
├── [ ] Identify affected specifications
├── [ ] Review settings.schema.json
└── [ ] Plan implementation scope

Phase 2: Specification Consultation
├── [ ] Read all related specification documents
├── [ ] Verify no conflicts with existing features
├── [ ] Identify all affected parameters
└── [ ] Document integration points

Phase 3: Implementation
├── [ ] Update frontend files (public/index.html, templates/index.html)
├── [ ] Update backend if needed (app/*.py)
├── [ ] Verify settings.schema.json coverage
├── [ ] Add appropriate error handling
└── [ ] Ensure accessibility (ARIA, keyboard nav)

Phase 4: Documentation
├── [ ] Create feature specification document
├── [ ] Update SPECIFICATIONS_INDEX.md
├── [ ] Add to relevant existing specs if needed
├── [ ] Include verification checklist
└── [ ] Document version history

Phase 5: Verification
├── [ ] Verify consistency across all files
├── [ ] Check for related specifications updates needed
├── [ ] Test critical paths
├── [ ] Document testing recommendations
└── [ ] Verify no breaking changes

Phase 6: Finalization
├── [ ] Complete all TODOs
├── [ ] Review changes holistically
├── [ ] Provide testing guidance
└── [ ] Document known limitations
```

---

## Table of Contents

1. Overview: Feature Implementation Lifecycle
2. Phase 1: Investigation & Planning
3. Phase 2: Specification Consultation (MANDATORY)
4. Phase 3: Implementation
5. Phase 4: Documentation
6. Phase 5: Verification & Testing
7. Phase 6: Finalization & Handoff
8. Case Study: Card Thickness Preset System
9. Common Pitfalls & How to Avoid Them
10. File Change Impact Matrix
11. Related Documents
12. Document History

---

## 1. Overview: Feature Implementation Lifecycle

### The Golden Rule

**ALWAYS consult specifications BEFORE implementing changes.**

The specifications are the single source of truth. Implementation without consulting specs leads to:
- Inconsistent parameter naming
- Missing integration points
- Broken features
- Incomplete documentation
- Technical debt

### Standard Workflow

```
User Request
    │
    ├─► Phase 1: Investigation & Planning (30 min - 2 hours)
    │   └─► Understand requirements, read specs, plan scope
    │
    ├─► Phase 2: Specification Consultation (1-3 hours)
    │   └─► MANDATORY: Read all related specifications
    │
    ├─► Phase 3: Implementation (2-8 hours)
    │   └─► Code changes, schema updates, error handling
    │
    ├─► Phase 4: Documentation (2-4 hours)
    │   └─► Create/update specifications, update index
    │
    ├─► Phase 5: Verification (1-2 hours)
    │   └─► Consistency checks, testing, validation
    │
    └─► Phase 6: Finalization (30 min - 1 hour)
        └─► Review, testing guidance, handoff
```

**Total Time Estimate for Major Feature**: 8-20 hours

---

## 2. Phase 1: Investigation & Planning

### Step 1.1: Understand User Requirements

**Questions to Answer:**
1. What is the user trying to accomplish?
2. Is this a new feature or a bug fix?
3. What are the expected outcomes?
4. Are there any performance constraints?
5. Does this affect existing functionality?

**Actions:**
- Read user request carefully
- Ask clarifying questions if needed
- Identify if this is frontend, backend, or full-stack

### Step 1.2: Read SPECIFICATIONS_INDEX.md

**File Location**: `docs/specifications/SPECIFICATIONS_INDEX.md`

**Purpose**: Understand existing architecture and find related specifications

**What to Look For:**
- Similar features already implemented
- Related subsystems that might be affected
- Specification naming conventions
- Current architecture patterns

**Time Investment**: 15-30 minutes

### Step 1.3: Identify Affected Specifications

**Create a List of Specifications to Read:**

Example from Card Thickness Preset System:
- SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md (parameter definitions)
- BRAILLE_SPACING_SPECIFICATIONS.md (spacing parameters)
- BRAILLE_DOT_ADJUSTMENTS_SPECIFICATIONS.md (dot parameters)
- SURFACE_DIMENSIONS_SPECIFICATIONS.md (cylinder/card dimensions)
- UI_INTERFACE_CORE_SPECIFICATIONS.md (UI patterns)

### Step 1.4: Review settings.schema.json

**File Location**: `settings.schema.json`

**Purpose**: Understand backend parameter schema

**Check:**
- Do the parameters you need already exist?
- Are there validation rules to follow?
- What are the default values?
- Are there enum constraints?

### Step 1.5: Plan Implementation Scope

**Document Your Plan:**
1. Files that need to be modified
2. New files that need to be created
3. Specifications that need updates
4. Dependencies between changes
5. Potential breaking changes

**Create TODO List** using the TodoWrite tool

---

## 3. Phase 2: Specification Consultation (MANDATORY)

### Why This Phase is Critical

**Historical Lesson (Card Thickness Preset):**
- HTML had default values that didn't match intended preset values
- This caused confusion and bugs
- Could have been avoided by consulting specifications first

**The Specification-First Approach Prevents:**
- Parameter naming inconsistencies
- Default value mismatches
- Missing integration points
- Duplicate implementations
- Architecture violations

### Step 2.1: Read All Related Specifications

**Reading Strategy:**

For each specification:
1. **Skim the Table of Contents** (2 min)
2. **Read "Document Purpose" section** (5 min)
3. **Study relevant sections in detail** (15-30 min)
4. **Note all parameter names and defaults** (5 min)
5. **Review "Related Specifications" section** (5 min)

**Take Notes On:**
- Parameter names (exact spelling, case)
- Default values
- Validation rules
- Cross-field dependencies
- Integration points with other features
- Known issues or limitations

### Step 2.2: Cross-Reference Multiple Specifications

**Check for Consistency:**

Example questions:
- Does `BRAILLE_SPACING_SPECIFICATIONS.md` use the same parameter names as `SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md`?
- Are default values consistent across specifications?
- Are there any deprecated parameters to avoid?

**Create a Parameter Reference Table:**

| Parameter | Spec 1 Default | Spec 2 Default | Schema Default | Our Value |
|-----------|----------------|----------------|----------------|-----------|
| grid_columns | 13 | 14 | - | 13 |
| cell_spacing | 6.5 | 6.5 | 6.5 | 6.5 |

### Step 2.3: Verify No Conflicts

**Conflict Checklist:**
- [ ] Does this feature duplicate existing functionality?
- [ ] Will this break existing features?
- [ ] Are there parameter name collisions?
- [ ] Does this violate architecture principles?
- [ ] Are there performance implications?

**If Conflicts Found:**
- Document them
- Propose resolution strategy
- Consult with user if needed

### Step 2.4: Document Integration Points

**Identify Where New Feature Connects:**
- UI controls location
- Expert Mode visibility
- LocalStorage keys
- Backend API endpoints
- Form submission flow
- Event handlers

---

## 4. Phase 3: Implementation

### Step 3.1: Update Frontend Files

**Files to Modify (typically):**
- `public/index.html` (production frontend)
- `templates/index.html` (template source)

**⚠️ CRITICAL**: These files MUST remain identical

**Frontend Implementation Checklist:**

#### A. HTML Structure
- [ ] Add UI controls with proper semantic HTML
- [ ] Use appropriate ARIA attributes
- [ ] Add descriptive labels and legends
- [ ] Include screen-reader-only descriptions
- [ ] Follow existing CSS class patterns

#### B. JavaScript Implementation
- [ ] Define data structures (e.g., `THICKNESS_PRESETS` object)
- [ ] Implement core logic function (e.g., `applyThicknessPreset()`)
- [ ] Add event listeners (change, click, etc.)
- [ ] Implement localStorage persistence
- [ ] Add restoration on page load
- [ ] Include error handling (try-catch blocks)
- [ ] Add debug logging

#### C. Integration Points
- [ ] Update related UI elements (e.g., `updateGridColumnsForPlateType()`)
- [ ] Trigger validation functions (e.g., `checkCylinderOverflow()`)
- [ ] Reset generation state (e.g., `resetToGenerateState()`)
- [ ] Show user feedback (confirmation messages)

#### D. Error Handling
```javascript
// Pattern: Wrap in try-catch, fail gracefully
try {
    localStorage.setItem(key, value);
} catch (e) {
    // Don't break user experience if localStorage fails
}
```

### Step 3.2: Update Backend (If Needed)

**Backend Files (Python):**
- `app/models.py` - Data models and defaults
- `app/validation.py` - Validation rules
- `backend.py` - API endpoints
- `app/geometry/*.py` - Geometry generation

**Backend Implementation Checklist:**

- [ ] Add new fields to `CardSettings` class if needed
- [ ] Update default values in `app/models.py`
- [ ] Add validation rules in `app/validation.py`
- [ ] Update API endpoint handlers if needed
- [ ] Ensure backward compatibility

**⚠️ Note**: Many frontend features (like presets) don't require backend changes!

### Step 3.3: Verify settings.schema.json Coverage

**Check:**
- [ ] All parameters exist in schema
- [ ] Default values match implementation
- [ ] Types are correct (number, string, boolean)
- [ ] Validation constraints are appropriate
- [ ] Enum values are complete

**If Updates Needed:**
```json
{
  "properties": {
    "new_parameter": {
      "type": "number",
      "minimum": 0,
      "default": 2.5,
      "description": "Clear description"
    }
  }
}
```

### Step 3.4: Ensure Consistency Between Files

**Consistency Checklist:**

- [ ] `public/index.html` matches `templates/index.html` exactly
- [ ] Parameter names match across frontend/backend
- [ ] Default values match across all locations
- [ ] Event handlers are identical
- [ ] Error handling is consistent

**Use diff tools to verify:**
```bash
diff public/index.html templates/index.html
```

### Step 3.5: Add Accessibility Features

**Accessibility Checklist:**
- [ ] All form controls have labels
- [ ] Radio buttons have `role="radiogroup"`
- [ ] Screen reader descriptions with `aria-describedby`
- [ ] Keyboard navigation works correctly
- [ ] Focus indicators are visible
- [ ] Color contrast meets WCAG AA standards

---

## 5. Phase 4: Documentation

### Step 4.1: Create Feature Specification Document

**File Naming Convention:**
`{FEATURE_NAME}_SPECIFICATIONS.md`

Example: `CARD_THICKNESS_PRESET_SPECIFICATIONS.md`

**Location**: `docs/specifications/`

**Required Sections:**

```markdown
# Feature Name Specifications

## Document Purpose
[What this spec covers]

## Scope
[In scope / Out of scope]

## Source Priority (Order of Correctness)
[Priority order for resolving conflicts]

## Table of Contents
[Numbered sections]

---

## 1. Feature Overview
### Purpose
### Key Benefits
### Architecture

## 2. Detailed Specifications
[Core content with subsections]

## 3. Implementation Details
### Code Locations
### Key Functions
### Data Structures

## 4. Parameter Reference
[Table of all parameters]

## 5. Integration Points
[How this integrates with other systems]

## 6. Default Behavior
[What happens in various scenarios]

## 7. Error Handling
[Failure modes and recovery]

## 8. Verification Checklist
[How to verify correct implementation]

## 9. Related Specifications
[Links to related docs]

## 10. Document History
[Version history table]
```

**Writing Guidelines:**

1. **Be Comprehensive**: Include every detail
2. **Use Code Examples**: Show actual implementation code
3. **Include Tables**: For parameter lists, comparisons
4. **Add Diagrams**: ASCII art for flow charts
5. **Cross-Reference**: Link to related specifications
6. **Provide Context**: Explain WHY, not just WHAT

### Step 4.2: Update SPECIFICATIONS_INDEX.md

**File Location**: `docs/specifications/SPECIFICATIONS_INDEX.md`

**Changes Required:**

1. **Update Header Metadata:**
```markdown
**Last Updated:** [TODAY'S DATE]
**Total Specification Documents:** [INCREMENT COUNT]
```

2. **Add to Core Features Section:**
```markdown
#### [YOUR_SPECIFICATION.md](./YOUR_SPECIFICATION.md)
**Status:** ✅ Complete (Created [DATE])
**Covers:**
- [Feature aspect 1]
- [Feature aspect 2]

**Key Components:**
- [Component 1]
- [Component 2]
```

3. **Update Coverage Analysis Table:**
Add your specification to the appropriate row

4. **Add to Quick Reference Section:**
```markdown
**Your feature?** → YOUR_SPECIFICATION (Section X)
```

5. **Update Version History:**
```markdown
| Date | Changes |
|------|---------|
| [TODAY] | Added YOUR_SPECIFICATION documenting [feature name] |
```

### Step 4.3: Update Related Specifications (If Needed)

**When to Update Existing Specs:**
- Feature modifies behavior described in another spec
- Feature adds new integration points
- Feature changes default values
- Feature deprecates old functionality

**How to Update:**
1. Add section describing new behavior
2. Update parameter tables
3. Add cross-reference to new specification
4. Update Document History section

### Step 4.4: Include Verification Checklist

**Every Specification Should Include:**

```markdown
## Verification Checklist

### Implementation Consistency
- [ ] File X contains correct implementation
- [ ] File Y matches File X
- [ ] Parameters have matching IDs
- [ ] Event handlers are attached
- [ ] Persistence works correctly

### Parameter Coverage
- [ ] All parameters included
- [ ] Defaults match specification
- [ ] Validation rules correct

### Integration Points
- [ ] Feature A integrates correctly
- [ ] Feature B is not broken
- [ ] Edge cases handled
```

---

## 6. Phase 5: Verification & Testing

### Step 5.1: Code Consistency Verification

**Files to Check:**

#### Frontend Consistency
```bash
# Verify HTML files match
diff public/index.html templates/index.html
```

**What to Look For:**
- Identical JavaScript implementations
- Same HTML structure
- Matching parameter names
- Identical event handlers

#### Backend Consistency
- Parameter names match frontend
- Defaults match schema
- Validation rules are appropriate

### Step 5.2: Specification Consistency Check

**Cross-Check:**
- [ ] Parameter names in spec match code
- [ ] Default values in spec match code
- [ ] All code locations documented in spec
- [ ] All parameters in code are documented in spec

**Use grep to find all references:**
```bash
grep -r "parameter_name" public/
grep -r "parameter_name" app/
```

### Step 5.3: Schema Validation

**Verify:**
- [ ] `settings.schema.json` validates correctly
- [ ] All properties have descriptions
- [ ] All defaults are specified
- [ ] All enums are complete
- [ ] Types match implementation

### Step 5.4: Test Critical Paths

**Manual Testing Checklist:**

1. **Happy Path:**
   - [ ] Feature works as intended
   - [ ] UI responds correctly
   - [ ] Values persist correctly
   - [ ] Confirmation messages display

2. **Edge Cases:**
   - [ ] localStorage disabled (private browsing)
   - [ ] Invalid saved values
   - [ ] Missing input elements
   - [ ] Multiple rapid clicks

3. **Integration:**
   - [ ] Works with Expert Mode
   - [ ] Works with existing features
   - [ ] Doesn't break other features
   - [ ] Form submission includes values

4. **Accessibility:**
   - [ ] Keyboard navigation works
   - [ ] Screen reader announces correctly
   - [ ] Focus indicators visible
   - [ ] ARIA attributes correct

### Step 5.5: Browser Testing

**Test in Multiple Browsers:**
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if possible)

**Test localStorage:**
- [ ] Normal mode
- [ ] Private/Incognito mode
- [ ] After clearing cache

### Step 5.6: Document Testing Recommendations

**In Your Specification, Include:**

```markdown
## Testing Recommendations

### Manual Testing Steps
1. Clear browser cache (Ctrl+F5)
2. [Specific action 1]
3. [Specific action 2]
4. Expected result: [description]

### Edge Cases to Test
- [Edge case 1]
- [Edge case 2]

### Known Limitations
- [Limitation 1]
- [Limitation 2]
```

---

## 7. Phase 6: Finalization & Handoff

### Step 6.1: Complete All TODOs

**Review TODO List:**
- [ ] All tasks marked as "completed"
- [ ] No pending items
- [ ] No unresolved questions

### Step 6.2: Holistic Review

**Review Entire Implementation:**

1. **Code Quality:**
   - Clean, readable code
   - Appropriate comments
   - No console errors
   - No linter warnings

2. **Documentation Quality:**
   - Comprehensive specifications
   - Clear examples
   - Accurate code references
   - Up-to-date cross-references

3. **User Experience:**
   - Intuitive UI
   - Clear feedback
   - Graceful error handling
   - Accessible to all users

### Step 6.3: Create Summary for User

**Provide:**
1. **Changes Made** - Bullet list of all changes
2. **Files Modified** - Complete list with line numbers
3. **Testing Recommendations** - How to test the feature
4. **Known Limitations** - Any edge cases or limitations
5. **Next Steps** - Deployment considerations

### Step 6.4: Document Known Limitations

**Be Honest About:**
- Browser compatibility issues
- Performance considerations
- Features not yet implemented
- Workarounds needed

### Step 6.5: Provide Deployment Guidance

**Consider:**
- Cache invalidation needs
- Database migrations (if any)
- Environment variable changes
- CDN updates (if applicable)

---

## 8. Case Study: Card Thickness Preset System

### Timeline: December 7, 2025

**User Request:**
"The 0.3mm/0.4mm card thickness buttons don't work correctly. When I click them, the radio dials in Expert Mode don't change to the saved default states."

### Phase 1: Investigation (30 minutes)

**What We Did:**
1. Read both HTML files to find preset implementation
2. Identified the Card Thickness UI controls
3. Found the `THICKNESS_PRESETS` object with values
4. Located the `applyThicknessPreset()` function
5. Examined event listeners and page load logic

**What We Found:**
- Feature already existed but had bugs
- Presets were defined for 0.3mm and 0.4mm
- Three distinct bugs identified:
  1. HTML default values didn't match preset values
  2. Preset not applied on page load
  3. Click event on already-selected button did nothing

### Phase 2: Specification Consultation (1 hour)

**Specifications Read:**
1. `SPECIFICATIONS_INDEX.md` - Understood project structure
2. `SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md` - Verified parameter schema
3. `settings.schema.json` - Checked backend parameter definitions
4. Reviewed `app/models.py` - Confirmed backend parameter handling

**Key Findings:**
- All preset parameters already existed in backend schema
- No backend changes needed (frontend-only feature)
- Parameter naming was consistent
- Feature followed established patterns

### Phase 3: Implementation (1 hour)

**Code Changes:**

**File 1: `public/index.html`**
- Added click event listener (in addition to change event)
- Modified restoration function to apply preset on load
- Added fallback to 0.4mm default

**File 2: `templates/index.html`**
- Applied identical changes to maintain consistency

**Key Code Added:**
```javascript
// Click listener for re-applying current preset
radio.addEventListener('click', function() {
    if (this.checked) {
        applyThicknessPreset(this.value);
    }
});

// Apply preset on page load (critical fix)
applyThicknessPreset(presetToApply);
```

### Phase 4: Documentation (2.5 hours)

**Documents Created:**

**1. CARD_THICKNESS_PRESET_SPECIFICATIONS.md** (600+ lines)
   - Complete preset definitions
   - Parameter reference tables
   - Integration points
   - Error handling strategy
   - Verification checklist

**2. Updated SPECIFICATIONS_INDEX.md**
   - Added new specification entry
   - Updated total document count
   - Added to coverage tables
   - Updated version history

### Phase 5: Verification (30 minutes)

**Checks Performed:**
- ✅ Both HTML files identical
- ✅ All 26 parameters documented
- ✅ settings.schema.json coverage verified
- ✅ Cross-references added
- ✅ No breaking changes
- ✅ Backward compatible

### Phase 6: Finalization (20 minutes)

**Deliverables:**
- Bug fixes in both HTML files
- Complete specification document
- Updated index
- Testing recommendations
- Summary report

**Total Time:** ~5.5 hours

### Key Success Factors

1. **Specification-First Approach**: Reading specs prevented introducing new bugs
2. **Comprehensive Documentation**: Future developers have complete reference
3. **Consistency Verification**: Both HTML files remain in sync
4. **Proper Error Handling**: Feature degrades gracefully
5. **Testing Guidance**: User knows exactly how to verify fixes

### Lessons Learned

**What Worked Well:**
- Reading specifications before coding
- Creating TODO list to track progress
- Verifying schema coverage
- Documenting as we went
- Maintaining file consistency

**What Could Be Improved:**
- Could have caught HTML default mismatch earlier by comparing defaults to preset values systematically
- Could have added automated tests

---

## 9. Common Pitfalls & How to Avoid Them

### Pitfall 1: Skipping Specification Consultation

**Problem:**
- Duplicate functionality
- Inconsistent naming
- Architecture violations
- Missing integration points

**Solution:**
- **ALWAYS** read SPECIFICATIONS_INDEX.md first
- Read ALL related specifications
- Take notes on parameters and patterns
- Verify no conflicts

**Time Saved by Consulting Specs First:** 2-4 hours of debugging

### Pitfall 2: Inconsistent File Updates

**Problem:**
- `public/index.html` doesn't match `templates/index.html`
- Frontend doesn't match backend
- Parameters have different names

**Solution:**
- Use diff tools to verify consistency
- Copy-paste identical sections when possible
- Create checklist of files to update
- Verify with grep searches

### Pitfall 3: Incomplete Documentation

**Problem:**
- Future developers don't understand feature
- Integration points are unclear
- Parameters aren't documented
- Testing guidance is missing

**Solution:**
- Create specification document DURING implementation
- Include every parameter
- Document all integration points
- Add verification checklist
- Provide testing recommendations

### Pitfall 4: Breaking Existing Features

**Problem:**
- Changed shared functionality
- Modified global state incorrectly
- Didn't test integration points
- Broke backward compatibility

**Solution:**
- Read related specifications to understand dependencies
- Test existing features after changes
- Maintain backward compatibility
- Document breaking changes if unavoidable

### Pitfall 5: Poor Error Handling

**Problem:**
- Feature breaks when localStorage unavailable
- No graceful degradation
- User sees cryptic errors
- Application crashes

**Solution:**
- Wrap localStorage in try-catch
- Fail gracefully (use defaults)
- Never show technical errors to users
- Test in private browsing mode

### Pitfall 6: Forgetting to Update Index

**Problem:**
- New specification isn't discoverable
- SPECIFICATIONS_INDEX.md is out of date
- Future developers don't know spec exists
- Coverage analysis incomplete

**Solution:**
- Update SPECIFICATIONS_INDEX.md immediately after creating spec
- Add to all relevant tables
- Update version history
- Verify cross-references

### Pitfall 7: Ignoring Accessibility

**Problem:**
- Feature not usable with keyboard
- Screen readers can't understand it
- Poor color contrast
- No focus indicators

**Solution:**
- Add ARIA attributes
- Test keyboard navigation
- Include screen-reader descriptions
- Follow existing UI patterns

### Pitfall 8: Not Testing Edge Cases

**Problem:**
- Feature breaks in private browsing
- Doesn't handle missing inputs
- Fails with invalid localStorage data
- Doesn't work in all browsers

**Solution:**
- Test localStorage disabled
- Test with missing elements
- Test with corrupted saved data
- Test in multiple browsers

---

## 10. File Change Impact Matrix

### When You Modify Frontend Parameters

| Change Type | Files to Update | Documentation to Update |
|-------------|----------------|------------------------|
| Add UI control | public/index.html, templates/index.html | UI_INTERFACE_CORE_SPECIFICATIONS.md |
| Add parameter | public/index.html, templates/index.html, (maybe) app/models.py | SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md, feature spec |
| Change default | public/index.html, templates/index.html, app/models.py, settings.schema.json | Feature spec, SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md |
| Add validation | frontend JS, app/validation.py | Feature spec |
| Add event handler | public/index.html, templates/index.html | Feature spec |

### When You Modify Backend Logic

| Change Type | Files to Update | Documentation to Update |
|-------------|----------------|------------------------|
| Add model field | app/models.py, settings.schema.json | SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md |
| Change geometry | app/geometry/*.py | Relevant geometry spec (dots, spacing, etc.) |
| Add API endpoint | backend.py | STL_EXPORT_AND_DOWNLOAD_SPECIFICATIONS.md |
| Change validation | app/validation.py | SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md |
| Update cache key | _(N/A - caching removed)_ | CACHING_SYSTEM_CORE_SPECIFICATIONS.md (archived) |

### When You Modify Specifications

| Change Type | Files to Update | Other Actions |
|-------------|----------------|---------------|
| Create new spec | N/A | Update SPECIFICATIONS_INDEX.md |
| Update existing spec | N/A | Update Document History, verify code still matches |
| Add cross-reference | N/A | Verify referenced spec exists |
| Change parameter definition | Code files (find all references) | Update all specs referencing that parameter |

---

## 11. Related Documents

### Process Documents
- This document (MAJOR_FEATURE_IMPLEMENTATION_SOP.md)
- VERIFICATION_GUIDE.md (if exists)

### Architecture Documents
- SPECIFICATIONS_INDEX.md - Master index of all specifications
- SETTINGS_SCHEMA_CORE_SPECIFICATIONS.md - Parameter schema
- settings.schema.json - JSON schema definition

### Reference Specifications
All specifications in `docs/specifications/` are relevant depending on the feature being implemented.

### Development Guidelines
- PROJECT_STRUCTURE.md - Project organization
- docs/development/DEVELOPMENT_GUIDELINES.md - Development guidelines (if available)

---

## 12. Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-12-07 | 1.0 | Initial creation. Documented standardized process for implementing major features based on Card Thickness Preset System case study. Includes 6-phase workflow, comprehensive checklists, pitfall avoidance, and file change impact matrix. |

---

**Document Version**: 1.0
**Created**: 2025-12-07
**Purpose**: Standard Operating Procedure for implementing major features in the Braille STL Generator
**Status**: ✅ Complete
**Target Audience**: Contributors, junior developers, senior developers

---

## Appendix A: Quick Start Guide for Contributors

When a user requests a new major feature:

1. **Stop and read this document first** (5 min)
2. **Read SPECIFICATIONS_INDEX.md** (15 min)
3. **Read related specifications** (1-2 hours)
4. **Create TODO list** using TodoWrite tool
5. **Implement following Phase 3 checklist** (2-8 hours)
6. **Create specification document** (2-3 hours)
7. **Update SPECIFICATIONS_INDEX.md** (15 min)
8. **Verify consistency** (30 min)
9. **Provide summary and testing guidance** (15 min)

**Total Time**: Plan for 8-20 hours depending on feature complexity

---

## Appendix B: Specification Template

Save this template for quick specification creation:

```markdown
# [Feature Name] Specifications

## Document Purpose
[One paragraph explaining what this spec covers]

## Scope
[What's included and excluded]

## Source Priority (Order of Correctness)
1. [Most authoritative source]
2. [Second priority]
3. This specification document

---

## Table of Contents
[Generated from sections]

---

## 1. Feature Overview
### Purpose
### Key Benefits
### Architecture

## 2. [Core Content Sections]

## 10. Verification Checklist
[Comprehensive checklist]

## 11. Related Specifications
[Links to related docs]

## 12. Document History
| Date | Version | Changes |
|------|---------|---------|
| [DATE] | 1.0 | Initial creation |
```

---

**End of Standard Operating Procedure**
