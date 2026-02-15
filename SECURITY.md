# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | Yes       |
| < 0.2.0 | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in JAIA, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Email the maintainer directly with details of the vulnerability
3. Include steps to reproduce, if possible
4. Allow reasonable time for a fix before public disclosure

## Security Features

JAIA includes the following security measures:

### Authentication & Access Control
- API documentation (Swagger/ReDoc) is disabled in production (`DEBUG=false`)
- CORS origins are configurable via environment variables

### Network Security
- Rate limiting: 100 requests/minute per IP (configurable)
- IP blocking after 10 suspicious request violations
- Suspicious pattern detection (SQL injection, XSS, directory traversal)
- Security headers (HSTS, CSP, X-Frame-Options, etc.)

### Data Protection
- All credentials stored in environment variables only (never in code)
- `.env` files excluded from version control via `.gitignore`
- Database files excluded from version control
- Request ID tracing for audit logging

### Audit Logging
- All API access to critical endpoints is logged
- Security events (rate limit violations, blocked IPs) are recorded
- Performance metrics are tracked per request

## Configuration for Production

### Required Environment Variables

```bash
ENVIRONMENT=production
DEBUG=false
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

### Security Checklist

- [ ] Set `DEBUG=false` in production
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `CORS_ALLOWED_ORIGINS` with actual domain
- [ ] Use HTTPS (TLS) in production
- [ ] Rotate API keys regularly
- [ ] Review audit logs periodically
- [ ] Keep dependencies updated (`pip-audit`, `npm audit`)
- [ ] Ensure `.env` files are not tracked in git

## Dependencies

Security scanning is integrated into the CI pipeline:
- **bandit**: Python static security analysis
- **safety**: Python dependency vulnerability scanning
- **npm audit**: Node.js dependency vulnerability scanning
