# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately:

1. **Do not** open a public issue
2. Email security details to the repository maintainer through GitHub
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix & Disclosure**: Coordinated with reporter

## Security Measures

This application implements:

- Input validation and sanitization
- Rate limiting (Flask-Limiter)
- Content Security Policy (CSP) headers
- Environment variable protection
- Secure cookie settings

For detailed security documentation, see [docs/security/](docs/security/).

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| < 1.1   | :x:                |

## Security Audit Reports

See [docs/security/SECURITY_AUDIT_REPORT.md](docs/security/SECURITY_AUDIT_REPORT.md) for comprehensive audit findings.
