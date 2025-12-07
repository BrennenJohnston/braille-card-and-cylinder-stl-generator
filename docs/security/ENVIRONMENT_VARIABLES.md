# Environment Variables Configuration Guide

This document provides complete documentation for all environment variables used in the Braille STL Generator application.

---

## Quick Start

### Required for Production

```bash
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
PRODUCTION_DOMAIN=https://your-domain.vercel.app
REDIS_URL=rediss://user:password@host:port/db
BLOB_STORE_WRITE_TOKEN=your-blob-token
BLOB_PUBLIC_BASE_URL=https://your-store.public.blob.vercel-storage.com
```

### Setting in Vercel

```bash
# Interactive method
vercel env add SECRET_KEY production
vercel env add PRODUCTION_DOMAIN production
vercel env add REDIS_URL production

# Or via Vercel dashboard:
# 1. Go to your project settings
# 2. Navigate to Environment Variables
# 3. Add each variable
```

---

## Complete Reference

### 🔐 Security

#### `SECRET_KEY` (Required in Production)
- **Purpose:** Flask session signing and CSRF protection
- **Type:** String (hex)
- **Required:** Yes (production), No (development)
- **Default:** `'dev-key-change-in-production'` (development only)
- **Security:** CRITICAL - Must be random and secret

**Generate:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example:**
```bash
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
```

**Notes:**
- Application will **fail to start** in production without this
- Never commit to version control
- Rotate periodically (annually recommended)
- Use different keys for different environments

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
- `development`: Enables debug mode, relaxed security, diagnostics
- `production`: Strict security, no debug output, requires SECRET_KEY

---

#### `PRODUCTION_DOMAIN`
- **Purpose:** Allowed CORS origin for production
- **Type:** String (URL)
- **Required:** Strongly recommended for production
- **Default:** None (allows all origins with warning)

**Example:**
```bash
PRODUCTION_DOMAIN=https://braille-generator.vercel.app
```

**Notes:**
- Include protocol (`https://`)
- Do not include trailing slash
- Can be comma-separated for multiple domains (not currently implemented)
- If not set, application logs security warning

---

### 💾 Redis / Caching

#### `REDIS_URL`
- **Purpose:** Redis connection string for rate limiting and caching
- **Type:** String (URL)
- **Required:** No (falls back to memory storage)
- **Format:** `redis://` or `rediss://` (TLS)

**Production Example (TLS required):**
```bash
REDIS_URL=rediss://default:password@redis-host.com:6379/0
```

**Development Example (localhost):**
```bash
REDIS_URL=redis://localhost:6379/0
```

**Notes:**
- Production MUST use `rediss://` (TLS)
- Application enforces TLS for non-localhost connections
- Passwords are redacted in logs
- Connection timeout: 5 seconds
- If not set, uses in-memory rate limiting (not persistent)

---

#### `BLOB_PUBLIC_BASE_URL`
- **Purpose:** Base URL for Vercel Blob storage
- **Type:** String (URL)
- **Required:** No (disables blob caching)
- **Format:** `https://<store-id>.public.blob.vercel-storage.com`

**Example:**
```bash
BLOB_PUBLIC_BASE_URL=https://abc123xyz.public.blob.vercel-storage.com
```

**Notes:**
- Required for counter plate caching
- Get from Vercel Blob console
- Do not include trailing slash
- Automatically added to CSP `connect-src`

---

#### `BLOB_STORE_WRITE_TOKEN` or `BLOB_READ_WRITE_TOKEN`
- **Purpose:** Authentication token for blob storage writes
- **Type:** String (token)
- **Required:** No (disables blob uploads)
- **Aliases:** Both names work

**Example:**
```bash
BLOB_STORE_WRITE_TOKEN=vercel_blob_rw_XXXXXXXXXXXXXXXX
```

**Notes:**
- Get from Vercel Blob console
- Needs write permissions
- Used for uploading generated STL files
- Never log or expose publicly

---

#### `BLOB_DIRECT_UPLOAD_URL`
- **Purpose:** Override default blob upload endpoint
- **Type:** String (URL)
- **Required:** No
- **Default:** `https://blob.vercel-storage.com`

**Example:**
```bash
BLOB_DIRECT_UPLOAD_URL=https://custom-blob-endpoint.com
```

**Notes:**
- Rarely needed (use default)
- Advanced configuration only

---

#### `BLOB_API_BASE_URL`
- **Purpose:** Vercel API base URL for blob operations
- **Type:** String (URL)
- **Required:** No
- **Default:** `https://api.vercel.com`

**Example:**
```bash
BLOB_API_BASE_URL=https://api.vercel.com
```

**Notes:**
- Rarely needed (use default)
- Used as fallback upload method

---

#### `BLOB_CACHE_MAX_AGE`
- **Purpose:** Cache-Control max-age for blob uploads
- **Type:** String (seconds)
- **Required:** No
- **Default:** `'31536000'` (1 year)

**Example:**
```bash
BLOB_CACHE_MAX_AGE=86400
```

---

#### `BLOB_URL_TTL_SEC`
- **Purpose:** Redis TTL for cached blob URLs
- **Type:** String (seconds)
- **Required:** No
- **Default:** `'31536000'` (1 year)

**Example:**
```bash
BLOB_URL_TTL_SEC=2592000
```

---

#### `BLOB_STORE_ID`
- **Purpose:** Vercel Blob store identifier
- **Type:** String
- **Required:** No
- **Notes:** Automatically managed by Vercel

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

#### `ENABLE_DEBUG_ENDPOINTS`
- **Purpose:** Enable debug endpoints in production
- **Type:** Boolean string
- **Required:** No
- **Default:** `False`
- **Valid Values:** `'1'`, `'true'`, `'yes'`, `'on'`

**Example:**
```bash
ENABLE_DEBUG_ENDPOINTS=1
```

**Effects:**
- Enables `/debug/blob_upload` endpoint
- **Security warning:** Exposes configuration information

**Recommendation:** Never enable in production. Use development mode instead.

---

#### `FORCE_CLIENT_CSG`
- **Purpose:** Force client-side CSG even if server backends available
- **Type:** Boolean string
- **Required:** No
- **Default:** `False`
- **Valid Values:** `'1'`, `'true'`, `'yes'`

**Example:**
```bash
FORCE_CLIENT_CSG=1
```

**Effects:**
- Disables server-side STL generation
- Forces use of client-side CSG
- Useful for testing client-side behavior

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

## Configuration Examples

### Production (Vercel)

```bash
# Required
SECRET_KEY=a1b2c3d4e5f6...
FLASK_ENV=production
PRODUCTION_DOMAIN=https://braille-stl.vercel.app

# Recommended
REDIS_URL=rediss://default:pass@redis.cloud:6379/0
BLOB_STORE_WRITE_TOKEN=vercel_blob_rw_...
BLOB_PUBLIC_BASE_URL=https://abc123.public.blob.vercel-storage.com

# Optional
LOG_LEVEL=INFO
```

### Development (Local)

```bash
# Minimal
FLASK_ENV=development

# With Redis (optional)
REDIS_URL=redis://localhost:6379/0

# With diagnostics
ENABLE_DIAGNOSTICS=1
LOG_LEVEL=DEBUG
```

### Testing (Local)

```bash
FLASK_ENV=development
FORCE_CLIENT_CSG=1
LOG_LEVEL=DEBUG
```

---

## Security Best Practices

### ✅ Do

- **Use strong random SECRET_KEY** (64+ characters hex)
- **Use TLS for Redis** in production (`rediss://`)
- **Set PRODUCTION_DOMAIN** explicitly
- **Rotate SECRET_KEY** annually
- **Use environment-specific values** (different keys per environment)
- **Store in Vercel environment variables** (encrypted at rest)

### ❌ Don't

- **Never commit secrets** to version control
- **Never use default SECRET_KEY** in production
- **Never expose tokens** in logs or error messages
- **Never use `redis://`** (non-TLS) in production
- **Never enable debug endpoints** in production
- **Never share secrets** between environments

---

## Troubleshooting

### Application fails to start

**Error:** `RuntimeError: SECRET_KEY environment variable must be set in production`

**Solution:**
```bash
# Generate and set SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
vercel env add SECRET_KEY production
```

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

### Redis connection fails

**Error:** `Redis connection failed - check REDIS_URL environment variable`

**Solutions:**

1. **Verify URL format:**
   ```bash
   # Production must use TLS
   REDIS_URL=rediss://user:pass@host:port/db

   # Development can use non-TLS localhost
   REDIS_URL=redis://localhost:6379/0
   ```

2. **Test connection:**
   ```bash
   redis-cli -u $REDIS_URL ping
   ```

3. **Check TLS:**
   ```bash
   # Should start with rediss:// for production
   echo $REDIS_URL
   ```

---

### Rate limiting not working

**Issue:** Rate limits not persisting between requests

**Cause:** No Redis configured (using in-memory storage)

**Solution:**
```bash
# Set up Redis
vercel env add REDIS_URL production
```

**Verify:**
```bash
# Check logs for "Redis connected: rediss://..."
vercel logs
```

---

### Blob caching not working

**Issue:** Counter plates not caching, always regenerating

**Solutions:**

1. **Check blob storage configured:**
   ```bash
   vercel env ls
   # Should see:
   # - BLOB_STORE_WRITE_TOKEN
   # - BLOB_PUBLIC_BASE_URL
   ```

2. **Verify blob store access:**
   ```bash
   curl -I $BLOB_PUBLIC_BASE_URL/stl/test.stl
   ```

3. **Check logs:**
   ```bash
   vercel logs | grep -i blob
   ```

---

## Environment Variable Checklist

Use this checklist when deploying:

### Pre-Deployment
- [ ] Generate SECRET_KEY (new random value)
- [ ] Get production domain URL
- [ ] Set up Redis with TLS
- [ ] Configure Vercel Blob storage
- [ ] Get blob storage tokens

### Vercel Configuration
- [ ] Set `SECRET_KEY`
- [ ] Set `FLASK_ENV=production`
- [ ] Set `PRODUCTION_DOMAIN`
- [ ] Set `REDIS_URL` (with `rediss://`)
- [ ] Set `BLOB_STORE_WRITE_TOKEN`
- [ ] Set `BLOB_PUBLIC_BASE_URL`
- [ ] Set `LOG_LEVEL=INFO`

### Post-Deployment Verification
- [ ] Application starts successfully
- [ ] No SECRET_KEY warnings in logs
- [ ] CORS works from production domain
- [ ] Redis connection successful
- [ ] Blob storage uploads working
- [ ] Rate limiting functional

### Security Verification
- [ ] SECRET_KEY is random and not default
- [ ] Redis uses TLS (`rediss://`)
- [ ] CORS only allows intended domains
- [ ] Debug endpoints return 404
- [ ] Diagnostics disabled (or controlled)

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
     https://your-domain.vercel.app/generate_braille_stl

# Check rate limiting
for i in {1..5}; do
  curl https://your-domain.vercel.app/health
done
```

---

## Support

If you encounter issues:

1. **Check logs:** `vercel logs --follow`
2. **Verify environment:** `vercel env ls`
3. **Test locally:** Run with same environment variables
4. **Check documentation:** Review `SECURITY_AUDIT_REPORT.md`
5. **Rollback if needed:** `vercel rollback`

---

**Last Updated:** December 7, 2025
**Version:** 1.0
