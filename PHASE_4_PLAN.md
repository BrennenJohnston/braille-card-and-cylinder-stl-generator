# Phase 4: Logging & Error Handling Plan

## Objective
Replace print statements with proper logging and standardize error responses.

## Current State

### Print Statements Found
- `backend.py`: 91 print statements
- `app/geometry/cylinder.py`: ~60+ print statements  
- `app/models.py`: ~10+ print statements
- **Total:** ~161+ print statements to replace

### Types of Print Statements
1. **Debug info:** Grid configs, mesh stats, timing
2. **Warnings:** Failed operations, fallbacks, validation issues
3. **Errors:** Boolean failures, mesh problems
4. **Info:** Progress indicators, success messages

## Phase 4.1: Configure Logging & Replace Prints

### Strategy
1. Configure logging in `app/utils.py`
2. Add logger to each module
3. Replace prints systematically:
   - `print('DEBUG: ...')` → `logger.debug(...)`
   - `print('WARNING: ...')` → `logger.warning(...)`
   - `print('ERROR: ...')` → `logger.error(...)`
   - `print('INFO: ...')` or `print('✓ ...')` → `logger.info(...)`
   - Regular status prints → `logger.info(...)`

### Benefits
- Proper log levels (DEBUG, INFO, WARNING, ERROR)
- Can control verbosity via environment variable
- Better for production monitoring
- Structured logging possible
- No print noise in tests

## Phase 4.2: Consistent API Errors

### Current State
- Mix of error response formats
- Some return tuples, some raise exceptions
- Inconsistent error objects

### Goal
- All errors return `{'error': 'message'}` with appropriate status code
- Consistent structure across all endpoints
- No raw stack traces in responses

## Implementation Plan

### Step 1: Configure Logging (5 minutes)
- Enhance `app/utils.py` with logging configuration
- Add `get_logger()` function
- Configure INFO by default, DEBUG via env variable

### Step 2: Add Logging to Modules (10 minutes)
- Import logger in each module
- backend.py
- app/geometry/cylinder.py
- app/models.py

### Step 3: Replace Prints Systematically (30 minutes)
- backend.py: Replace 91 print statements
- cylinder.py: Replace ~60 print statements
- models.py: Replace ~10 print statements
- Test after each file

### Step 4: Error Response Consistency (15 minutes)
- Review error returns
- Standardize format
- Update error handlers

**Total Estimated Time:** 60 minutes

## Acceptance Criteria

✅ No print statements remain  
✅ All logging uses proper levels  
✅ Can control log level via env variable  
✅ Errors return consistent JSON format  
✅ All tests still pass  

Ready to implement!

