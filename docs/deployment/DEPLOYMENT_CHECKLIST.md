# Deployment Checklist

## What you need

v2.0.0 has no external service dependencies. The server is Flask serving static files and one JSON endpoint. All STL generation happens in the browser.

| Component | What's required |
|-----------|----------------|
| External services | None |
| Server dependencies | Flask, Flask-CORS |
| Required secrets | None (all env vars are optional) |

## Deploying to Vercel

### 1. Connect and deploy

1. Push code to GitHub
2. Connect the repo to Vercel (framework preset: **Other**)
3. Deploy

No environment variables are required. Vercel auto-detects Python from `requirements.txt`.

### 2. Optional configuration

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session key (backend is stateless, so this is optional) |
| `FLASK_ENV` | Set to `production` for strict security mode |
| `PRODUCTION_DOMAIN` | Your domain for CORS (Vercel domains are allowed by default) |
| `LOG_LEVEL` | Logging verbosity (default: INFO) |

Generate a secret key if you want one:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Post-deployment testing

### Functionality
- [ ] Main UI loads
- [ ] Cylinder STL generation works (embossing + counter)
- [ ] Braille translation preview works
- [ ] Multiple languages work
- [ ] Expert mode parameters work
- [ ] Keyboard navigation and screen reader work
- [ ] Mobile layout is usable

### Security
- [ ] XSS payloads in text inputs are escaped
- [ ] Malformed JSON returns an error, not a crash
- [ ] Oversized requests (>100KB) are rejected
- [ ] Security headers present (check with `curl -I`)

### Endpoints

| Endpoint | Method | Expected |
|----------|--------|----------|
| `/` | GET | Main UI |
| `/health` | GET | `{"status": "ok"}` |
| `/liblouis/tables` | GET | JSON list of tables |
| `/geometry_spec` | POST | JSON geometry spec |

Old endpoints (`/generate_braille_stl`, `/generate_counter_plate_stl`, `/lookup_stl`) return 410 Gone.

## Troubleshooting

**"Manifold worker not available" on mobile:**
Expected on first load — WASM loads lazily. Refresh if it times out.

**STL generation fails:**
Check the browser console. Usually a WASM loading issue. Try a different browser.

**Translation preview is empty:**
Check that `/liblouis/tables` returns JSON. The liblouis tables may not be serving.

## Rollback

In the Vercel dashboard: go to Deployments, find the last working deployment, click "Promote to Production."
