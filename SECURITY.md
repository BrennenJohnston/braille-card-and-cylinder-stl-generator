# Security Policy

## Reporting a vulnerability

If you find a security vulnerability, please report it privately:

1. **Do not** open a public issue
2. Email the maintainer through GitHub
3. Include a description, steps to reproduce, potential impact, and a suggested fix if you have one

## Response timeline

- **Acknowledgment:** within 48 hours
- **Initial assessment:** within 7 days
- **Fix and disclosure:** coordinated with reporter

## What's in place

- Input validation and sanitization
- Content Security Policy headers
- Minimal server attack surface (client-side STL generation)
- No external service dependencies (no secrets to compromise)
- Path traversal protection on static file serving

For details, see [docs/security/](docs/security/).

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.0.x | Yes |
| 1.3.x | Yes |
| 1.2.x | Yes |
| < 1.2 | No |
