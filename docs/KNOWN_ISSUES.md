# Known Issues

This document tracks known issues that need to be addressed in future development.

---

## 1. Vercel Blob Storage Caching - Not Working

**Status:** 🔴 Broken - Needs Investigation
**Priority:** Medium
**Date Identified:** 2025-12-08
**Affects:** Counter plate STL caching on Vercel deployment

### Description

The Vercel Blob storage caching system for counter plate STL files is not functioning correctly. This caching is designed to store generated counter plate STLs in Vercel Blob storage to avoid regenerating them on subsequent requests.

### Background

- User deleted files within the blob storage location (`braille-card-and-cylinder-s-blob/stl/`) to clear space
- After clearing the folder, the virtual "stl" folder disappeared (expected behavior for object storage)
- User manually recreated the "stl" folder through the Vercel dashboard
- Blob storage caching appears to not be working after these changes

### Environment Configuration

The following environment variables are configured in Vercel:
- `BLOB_PUBLIC_BASE_URL` - Set to: `https://aq4in5fwaqi1kror.public.blob.vercel-storage.com`
- `BLOB_READ_WRITE_TOKEN` - Configured (encrypted)
- `REDIS_URL` - Configured for cache key mapping

### Investigation Notes

1. The debug endpoint (`/debug/blob_upload`) returns `{"error": "Endpoint not available"}` - this endpoint is disabled in production for security reasons

2. The "Flat Card" shape (which uses blob storage for counter plates) is currently disabled in the UI, making it difficult to test the blob storage path

3. Blob storage is primarily used for:
   - Card-shaped counter plates (negative plates)
   - Backend endpoints: `/generate_braille_stl` and `/generate_counter_plate_stl`

4. Cylinder shapes use client-side CSG generation and don't exercise the blob storage path

### Relevant Code Locations

- `app/cache.py` - Blob storage upload/check functions
- `backend.py` - STL generation endpoints with blob caching logic
- Lines ~1120-1430 in `backend.py` - `/generate_braille_stl` endpoint
- Lines ~1570-1710 in `backend.py` - `/generate_counter_plate_stl` endpoint

### To Reproduce

1. Re-enable the Flat Card shape in the UI
2. Select "Universal Counter Plate"
3. Generate an STL
4. Check response headers for `X-Blob-Cache` values
5. Check Vercel logs for blob upload success/failure messages

### Potential Causes to Investigate

1. **Folder recreation issue** - The manually created "stl" folder may have different permissions or structure than what's expected
2. **Token/permission issues** - The `BLOB_READ_WRITE_TOKEN` may need to be regenerated
3. **URL mismatch** - The constructed blob URLs may not match the actual storage location
4. **Redis cache state** - Old cache entries may be pointing to deleted blobs

### Workaround

Currently, STL generation falls back to direct response (no caching) when blob storage fails. Users can still generate and download STLs, but without caching benefits.

### Resolution Steps (Future)

1. Enable the debug endpoint temporarily to verify configuration
2. Re-enable Flat Card shape for testing
3. Add more verbose logging to blob upload functions
4. Consider regenerating the blob storage token
5. Clear Redis cache entries for blob URL mappings
6. Test end-to-end blob upload and retrieval

---

## 2. Flat Card Shape - Temporarily Disabled

**Status:** 🟡 Disabled
**Priority:** Low
**Date Identified:** Unknown
**Affects:** UI shape selection

### Description

The "Flat Card" shape option is currently disabled in the UI with a "temporarily disabled" label. Only the Cylinder shape is available.

### Reason

The exact reason for disabling is not documented. May be related to:
- The blob storage issues above
- CSG generation issues with flat cards
- Other stability concerns

### Location

- `public/index.html` and `templates/index.html` - Lines ~2408-2412
- JavaScript initialization - Lines ~5972-5974

---

*Last updated: 2025-12-08*
