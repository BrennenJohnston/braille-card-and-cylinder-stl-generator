# Environment Variables

**Architecture note:** As of v2.0.0 (January 2026), Redis and Blob storage have been removed. All environment variables are optional.

## Quick start

For most deployments, you don't need to set anything. The app works out of the box on Vercel.

If you want tighter security, set these:

```bash
SECRET_KEY=<random-hex-string>
FLASK_ENV=production
PRODUCTION_DOMAIN=https://your-domain.vercel.app
```

## Variable reference

### SECRET_KEY

Flask session signing key. The backend is stateless and doesn't use sessions, so this is optional. Set it for defense-in-depth if you want.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### FLASK_ENV

`development` or `production`. Defaults to `production` if not set.

- **development:** debug mode, relaxed security, localhost CORS
- **production:** strict security, no debug output

### PRODUCTION_DOMAIN

Your production URL for CORS. Include the protocol (`https://`), no trailing slash. If not set, the app logs a warning and allows all origins.

```bash
PRODUCTION_DOMAIN=https://braille-generator.vercel.app
```

### LOG_LEVEL

Python logging level. Defaults to `INFO`. Use `DEBUG` only in development.

### ENABLE_DIAGNOSTICS

Set to `1` to log Python version and platform info on startup. Only useful when debugging deployment issues. Reveals system information, so don't leave it on.

## Removed variables

If you're migrating from v1.x, remove these from your Vercel config:

- `REDIS_URL` — will cause failures if Upstash has archived the database
- `BLOB_STORE_WRITE_TOKEN` / `BLOB_READ_WRITE_TOKEN`
- `BLOB_PUBLIC_BASE_URL`
- `BLOB_DIRECT_UPLOAD_URL`, `BLOB_API_BASE_URL`, `BLOB_CACHE_MAX_AGE`, `BLOB_URL_TTL_SEC`, `BLOB_STORE_ID`
- `ENABLE_DEBUG_ENDPOINTS` — debug endpoints now return 410 Gone
- `FORCE_CLIENT_CSG` — client-side CSG is the only method

```bash
vercel env rm REDIS_URL production
vercel env rm BLOB_STORE_WRITE_TOKEN production
vercel env rm BLOB_READ_WRITE_TOKEN production
vercel env rm BLOB_PUBLIC_BASE_URL production
```

## Troubleshooting

**CORS errors:** Set `PRODUCTION_DOMAIN` to your actual domain.

**Redis connection errors after migration:** You still have `REDIS_URL` set. Remove it and redeploy.

## Setting variables in Vercel

```bash
vercel env add SECRET_KEY production
vercel env add PRODUCTION_DOMAIN production
```

Or use the Vercel dashboard under Project Settings > Environment Variables.
