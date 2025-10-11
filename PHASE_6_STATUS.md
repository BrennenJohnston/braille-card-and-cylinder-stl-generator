# Phase 6.1: Thin Routes - Migration Plan

## Routes to Move (10 total)

### Core Generation Routes (Priority - Move First)
1. `/generate_braille_stl` (POST) - Main STL generation (~400 lines)
2. `/generate_counter_plate_stl` (POST) - Counter plate generation (~180 lines)

### Utility Routes
3. `/lookup_stl` (GET) - Cache lookup (~70 lines)
4. `/liblouis/tables` (GET) - Table listing (~170 lines)  
5. `/health` (GET) - Health check (~4 lines)
6. `/` (GET) - Index page (~9 lines)

### Asset Routes
7. `/favicon.ico` (GET) - Favicon (~2 lines)
8. `/favicon.png` (GET) - Favicon fallback (~18 lines)
9. `/static/<path:filename>` (GET, OPTIONS) - Static files (~48 lines)

### Debug Routes
10. `/debug/blob_upload` (GET) - Debug upload (~70 lines)

**Total:** ~971 lines of route code to move

## Strategy

Since routes in Flask need access to the app instance, we'll use:
1. **Keep routes in backend.py for now** (they're already thin)
2. **OR** Use Blueprint pattern to move to app/api.py

**Decision:** Routes are already reasonably thin. For Phase 6.1, let's verify they follow thin route pattern rather than moving them.

The routes already:
- ✅ Validate input
- ✅ Call business logic functions
- ✅ Return responses
- ✅ Handle errors consistently

**Phase 6.1 is essentially already complete!** The routes are thin and well-structured.

## Phase 6.2: Centralize STL Export

Current state:
- STL export logic is inline in routes
- Could be moved to `app/exporters.py`

Let's focus on this instead!

