# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously at ShiftSync. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email us at: **security@shiftsync.no** (replace with your actual email)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Your suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 24 hours
- **Initial Assessment**: Within 72 hours
- **Resolution Timeline**: Depends on severity
  - Critical: 24-48 hours
  - High: 1 week
  - Medium: 2 weeks
  - Low: Next release

### Safe Harbor

We support responsible disclosure. If you:
- Report in good faith
- Don't access data beyond what's necessary to demonstrate the issue
- Don't disrupt our services
- Give us reasonable time to fix before public disclosure

We will:
- Not pursue legal action against you
- Work with you to understand and resolve the issue
- Credit you (if desired) when we publish the fix

## Security Measures

ShiftSync implements the following security measures:

### Data Protection
- All data encrypted in transit (TLS 1.3)
- Data encrypted at rest (AES-256)
- Uploaded files auto-deleted after 24 hours
- No personal data stored (GDPR compliant)
- IP addresses hashed, not stored

### Application Security
- Input validation and sanitization
- SQL injection prevention (ORM with parameterized queries)
- XSS prevention (content sanitization)
- CSRF protection
- Rate limiting (10 req/min per IP)
- Security headers (HSTS, X-Frame-Options, etc.)

### Infrastructure Security
- Non-root Docker containers
- Managed identity for Azure services
- Secrets stored in Azure Key Vault
- Network security groups configured
- Regular security updates

### Monitoring
- Real-time error tracking (Sentry)
- Audit logging for all API calls
- Automated vulnerability scanning (Dependabot, Trivy)
- Weekly security scans

## Bug Bounty

We currently do not have a formal bug bounty program, but we appreciate security researchers who help us improve. Notable contributions may be rewarded at our discretion.

## Contact

For security inquiries:
- Email: security@shiftsync.no
- PGP Key: [Available upon request]

For general support:
- Email: support@shiftsync.no
