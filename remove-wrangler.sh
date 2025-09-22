#!/bin/bash
# Quick script to remove wrangler.toml if it continues to cause issues

git rm wrangler.toml
git commit -m "fix: Remove wrangler.toml - configure via Pages dashboard instead

Cloudflare Pages doesn't require wrangler.toml and it was causing
deployment failures. All settings can be configured in the dashboard:
- Build command: npm run build
- Build output directory: /dist
- Root directory: /
- Environment variables: NODE_VERSION=20, etc."
git push origin feature/cloudflare-client

echo "wrangler.toml removed and changes pushed!"
echo "Now configure everything in Cloudflare Pages dashboard."
