# Environment Variables Configuration Guide

**ARCHITECTURE UPDATE (2026-01-05):** Redis and Blob storage dependencies have been removed. The application now uses a minimal backend that provides lightweight JSON geometry specifications for client-side CSG generation.

---

## Quick Start

### Minimal Production Configuration (Vercel)

```bash
# Optional but recommended
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
PRODUCTION_DOMAIN=https://your-domain.vercel.app
```

**That's it!** The application now works with just these optional variables. No Redis, no Blob storage, no external service dependencies.

### Setting in Vercel

```bash
# Interactive method
vercel env add SECRET_KEY production
vercel env add PRODUCTION_DOMAIN production

# Or via Vercel dashboard:
# 1. Go to your project settings
# 2. Navigate to Environment Variables
# 3. Add each variable
```

---

## Complete Reference

### 🔐 Security

#### `SECRET_KEY` (Optional for Stateless Backend)
- **Purpose:** Flask session signing (unused in stateless backend)
- **Type:** String (hex)
- **Required:** No (backend is stateless)
- **Default:** `'stateless-backend-no-sessions'` (production)
- **Security:** Recommended for defense-in-depth

**Generate:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example:**
```bash
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

**Notes:**
- Backend does not use sessions, so this is optional
- Set it anyway for defense-in-depth security
- Never commit to version control if set

---

#### `FLASK_ENV`
- **Purpose:** Application environment mode
- **Type:** String
- **Required:** No
- **Default:** `'production'` (if not set)
- **Valid Values:** `'development'`, `'production'`

**Example:**
```bash
# Production
FLASK_ENV=production

# Development
FLASK_ENV=development
```

**Effects:**
- `development`: Enables debug mode, relaxed security, localhost CORS
- `production`: Strict security, no debug output

---

#### `PRODUCTION_DOMAIN`
- **Purpose:** Allowed CORS origin for production
- **Type:** String (URL)
- **Required:** Recommended for production
- **Default:** None (allows all origins with warning)

**Example:**
```bash
PRODUCTION_DOMAIN=https://braille-generator.vercel.app
```

**Notes:**
- Include protocol (`https://`)
- Do not include trailing slash
- Can be comma-separated for multiple domains
- If not set, application logs security warning and allows all origins

---

### 🐛 Development / Debugging

#### `ENABLE_DIAGNOSTICS`
- **Purpose:** Enable platform diagnostics in production
- **Type:** Boolean string
- **Required:** No
- **Default:** `False`
- **Valid Values:** `'1'`, `'true'`, `'yes'`, `'on'` (case-insensitive)

**Example:**
```bash
ENABLE_DIAGNOSTICS=1
```

**Effects:**
- Enables `_log_platform_info()` in `wsgi.py`
- Logs Python version, platform, glibc version
- **Security warning:** Reveals system information

**Recommendation:** Only enable when troubleshooting deployment issues.

---

#### `LOG_LEVEL`
- **Purpose:** Python logging level
- **Type:** String
- **Required:** No
- **Default:** `'INFO'`
- **Valid Values:** `'DEBUG'`, `'INFO'`, `'WARNING'`, `'ERROR'`, `'CRITICAL'`

**Example:**
```bash
LOG_LEVEL=DEBUG
```

**Notes:**
- `DEBUG` is very verbose (development only)
- `INFO` is recommended for production
- `WARNING` or `ERROR` for quiet production

---

## ❌ REMOVED VARIABLES (2026-01-05)

The following environment variables are **no longer used** and should be removed from your Vercel configuration:

### Redis / Caching (DEPRECATED)

#### `REDIS_URL` ⚠️ **REMOVE THIS**
- **Status:** **DEPRECATED** - Causes deployment failures
- **Reason:** Upstash Redis archives after 14 days of inactivity, causing all requests to fail
- **Solution:** **Remove from Vercel environment variables**
- **Replacement:** None needed (rate limiting removed, Vercel provides DDoS protection)

**Migration:**
```bash
# Remove from Vercel
vercel env rm REDIS_URL production
```

---

#### `BLOB_STORE_WRITE_TOKEN` / `BLOB_READ_WRITE_TOKEN` ⚠️ **REMOVE THIS**
- **Status:** **DEPRECATED**
- **Reason:** Blob storage not needed for client-side generation
- **Solution:** Remove from Vercel environment variables

**Migration:**
```bash
vercel env rm BLOB_STORE_WRITE_TOKEN production
vercel env rm BLOB_READ_WRITE_TOKEN production
```

---

#### `BLOB_PUBLIC_BASE_URL` ⚠️ **REMOVE THIS**
- **Status:** **DEPRECATED**
- **Reason:** Blob storage integration removed
- **Solution:** Remove from Vercel environment variables

**Migration:**
```bash
vercel env rm BLOB_PUBLIC_BASE_URL production
```

---

#### Other Removed Variables

Remove these if present:
- `BLOB_DIRECT_UPLOAD_URL`
- `BLOB_API_BASE_URL`
- `BLOB_CACHE_MAX_AGE`
- `BLOB_URL_TTL_SEC`
- `BLOB_STORE_ID`
- `ENABLE_DEBUG_ENDPOINTS` (debug endpoints return 410 Gone)
- `FORCE_CLIENT_CSG` (client-side CSG is now the only method)

---

## Configuration Examples

### Production (Vercel) - RECOMMENDED

```bash
# Minimal (works out of the box)
# No environment variables needed!

# Recommended (better security)
SECRET_KEY=a1b2c3d4e5f6...
FLASK_ENV=production
PRODUCTION_DOMAIN=https://braille-stl.vercel.app
LOG_LEVEL=INFO
```

### Development (Local)

```bash
# Minimal
FLASK_ENV=development

# With diagnostics
ENABLE_DIAGNOSTICS=1
LOG_LEVEL=DEBUG
```

### Testing (Local)

```bash
FLASK_ENV=development
LOG_LEVEL=DEBUG
```

---

## Security Best Practices

### ✅ Do

- **Set PRODUCTION_DOMAIN** explicitly for proper CORS
- **Use strong random SECRET_KEY** if setting it (64+ characters hex)
- **Use environment-specific values** (different keys per environment)
- **Store in Vercel environment variables** (encrypted at rest)
- **Remove old Redis/Blob variables** to prevent confusion

### ❌ Don't

- **Never commit secrets** to version control
- **Never use default SECRET_KEY** if you set one
- **Never keep REDIS_URL** set (will cause failures if Upstash archives)
- **Never add Blob storage variables** back (no longer needed)

---

## Migration from Old Architecture

If you're migrating from the Redis/Blob architecture (pre-2026-01-05):

### Step 1: Remove Old Variables

```bash
# Remove ALL Redis and Blob variables from Vercel
vercel env rm REDIS_URL production
vercel env rm BLOB_STORE_WRITE_TOKEN production
vercel env rm BLOB_READ_WRITE_TOKEN production
vercel env rm BLOB_PUBLIC_BASE_URL production
vercel env rm BLOB_DIRECT_UPLOAD_URL production
vercel env rm BLOB_API_BASE_URL production
vercel env rm BLOB_CACHE_MAX_AGE production
vercel env rm BLOB_URL_TTL_SEC production
vercel env rm BLOB_STORE_ID production
```

### Step 2: Set Minimal Configuration

```bash
# Optional but recommended
vercel env add SECRET_KEY production
vercel env add PRODUCTION_DOMAIN production
vercel env add FLASK_ENV production
```

### Step 3: Redeploy

```bash
vercel --prod
```

### Step 4: Verify

```bash
# Check logs for NO Redis errors
vercel logs --follow

# Test functionality
curl https://your-domain.vercel.app/health
curl https://your-domain.vercel.app/geometry_spec -X POST \
  -H "Content-Type: application/json" \
  -d '{"lines":["⠓⠑⠇⠇⠕","","",""],"settings":{}}'
```

**Success indicators:**
- ✅ No Redis connection errors in logs
- ✅ `/health` returns `{"status": "ok"}`
- ✅ `/geometry_spec` returns JSON geometry
- ✅ UI generates and downloads STL files

---

## Troubleshooting

### Application fails to start (old error)

**Error:** `RuntimeError: SECRET_KEY environment variable must be set in production`

**Note:** This error no longer occurs in the new architecture. If you see it, you're using an old version.

---

### CORS errors

**Error:** `Access to fetch at ... from origin ... has been blocked by CORS policy`

**Solution:**
```bash
# Set your actual domain
vercel env add PRODUCTION_DOMAIN production
# Value: https://your-actual-domain.vercel.app
```

**Verify:**
```bash
curl -I https://your-domain.vercel.app | grep -i "access-control"
```

---

### Redis connection errors (after migration)

**Error:** `redis.exceptions.ConnectionError: Error 16 connecting to ...`

**Cause:** You still have `REDIS_URL` set in environment variables.

**Solution:**
```bash
# Remove the variable
vercel env rm REDIS_URL production

# Redeploy
vercel --prod
```

---

## Environment Variable Checklist

Use this checklist when deploying:

### Pre-Deployment
- [ ] **Remove** any `REDIS_URL` environment variable
- [ ] **Remove** any `BLOB_*` environment variables
- [ ] Generate SECRET_KEY (optional but recommended)
- [ ] Get production domain URL

### Vercel Configuration
- [ ] Set `SECRET_KEY` (optional)
- [ ] Set `FLASK_ENV=production` (optional)
- [ ] Set `PRODUCTION_DOMAIN` (recommended)
- [ ] Set `LOG_LEVEL=INFO` (optional)
- [ ] **Verify NO `REDIS_URL`** is set
- [ ] **Verify NO `BLOB_*`** variables are set

### Post-Deployment Verification
- [ ] Application starts successfully
- [ ] No Redis connection errors in logs
- [ ] CORS works from production domain
- [ ] `/health` endpoint responds
- [ ] `/geometry_spec` returns JSON
- [ ] UI generates STL files successfully

### Security Verification
- [ ] SECRET_KEY is random (if set)
- [ ] CORS only allows intended domains
- [ ] Debug endpoints return 410 Gone
- [ ] No Redis or Blob credentials present

---

## Additional Resources

### Vercel CLI Commands

```bash
# List all environment variables
vercel env ls

# Add new variable
vercel env add VARIABLE_NAME production

# Remove variable
vercel env rm VARIABLE_NAME production

# Pull environment variables to local .env file
vercel env pull
```

### Generate Secrets

```bash
# SECRET_KEY (64 character hex)
python -c "import secrets; print(secrets.token_hex(32))"

# Alternative with openssl
openssl rand -hex 32

# Alternative with node
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### Verify Configuration

```bash
# Check environment in deployed app
curl https://your-domain.vercel.app/health

# Check security headers
curl -I https://your-domain.vercel.app

# Check CORS
curl -H "Origin: https://unauthorized.com" \
     https://your-domain.vercel.app/geometry_spec

# Test geometry spec endpoint
curl -X POST https://your-domain.vercel.app/geometry_spec \
  -H "Content-Type: application/json" \
  -d '{"lines":["⠓⠑⠇⠇⠕","","",""],"settings":{}}'
```

---

## Architecture Documentation

For details on the architecture changes:

- [Codebase Audit and Renovation Plan](../development/CODEBASE_AUDIT_AND_RENOVATION_PLAN.md)

---

## Support

If you encounter issues:

1. **Check logs:** `vercel logs --follow`
2. **Verify environment:** `vercel env ls`
3. **Ensure NO `REDIS_URL`:** Should not be in environment variables
4. **Test locally:** Run with minimal environment variables
5. **Rollback if needed:** `vercel rollback`

---

**Last Updated:** January 5, 2026
**Version:** 2.0 (Minimal Backend Architecture)
**Migration:** Removed Redis/Blob dependencies (see CODEBASE_AUDIT_AND_RENOVATION_PLAN.md)
