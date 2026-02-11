# Security Best Practices for ShiftSync

This document outlines security best practices for operating ShiftSync in production.

## Table of Contents
- [API Key Management](#api-key-management)
- [OpenAI API Security](#openai-api-security)
- [Secret Rotation](#secret-rotation)
- [Database Security](#database-security)
- [Incident Response](#incident-response)

---

## API Key Management

### General Rules
1. **Never commit secrets** to version control
2. **Use environment variables** for all sensitive configuration
3. **Rotate keys regularly** (every 90 days recommended)
4. **Use least-privilege access** - give each key only the permissions it needs

### Environment Variables
Required secrets in `.env`:
```bash
DATABASE_URL=postgresql://...
SECRET_SALT=<random-32-chars>
INTERNAL_API_KEY=<random-32-chars>
OPENAI_API_KEY=sk-proj-...
```

Generate secure random values:
```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
[System.Guid]::NewGuid().ToString() + [System.Guid]::NewGuid().ToString()
```

---

## OpenAI API Security

### Creating a Secure API Key

1. **Go to OpenAI Platform**: https://platform.openai.com/api-keys

2. **Create a Project-Scoped Key** (NOT account-wide):
   - Click "Create new secret key"
   - Select "Project" scope
   - Name it: `shiftsync-production` or similar
   - Save the key securely - it won't be shown again!

3. **Set Spending Limits**:
   - Go to: https://platform.openai.com/account/limits
   - Set monthly budget: Recommended $10-50/month for startup
   - Set usage alerts at 50% and 80% of limit

4. **Enable Usage Alerts**:
   - Go to: https://platform.openai.com/account/billing/overview
   - Enable email notifications
   - Set up webhooks for real-time alerts (optional)

### Rate Limiting
OpenAI has built-in rate limits, but also implement your own:
- Max 10 Vision API calls per minute per user
- Queue requests during high load
- Cache results when appropriate

### If Key is Compromised
1. **Immediately revoke** the compromised key in OpenAI dashboard
2. Generate new key with new name
3. Update all production environments
4. Review usage logs for unauthorized access
5. Consider enabling IP restrictions

---

## Secret Rotation

### Schedule
| Secret | Rotation Frequency | Notes |
|--------|-------------------|-------|
| DATABASE_URL password | Every 90 days | Coordinate with DB team |
| SECRET_SALT | Never (unless compromised) | Would invalidate all user sessions |
| INTERNAL_API_KEY | Every 90 days | Update all internal tools |
| OPENAI_API_KEY | Every 90 days or on suspected breach | |
| STRIPE_SECRET_KEY | Every 90 days | Update webhook endpoints |

### Rotation Process
1. Generate new key/password
2. Update in Azure Key Vault (or .env for dev)
3. Deploy updated configuration
4. Verify functionality
5. Revoke old key after 24h grace period

---

## Database Security

### Connection Security
- Always use SSL/TLS connections
- Use connection pooling (already configured in SQLAlchemy)
- Limit max connections to prevent DOS

### Query Security
- All queries use SQLAlchemy ORM (parameterized by default)
- Never use f-strings for SQL
- Log slow queries for review

### Backup Security
- Encrypt backups at rest
- Store backups in separate region
- Test restore process monthly

---

## Incident Response

### Security Incident Checklist

#### 1. Detection
- [ ] Unusual API usage patterns
- [ ] Failed authentication attempts
- [ ] Unexpected errors in Sentry
- [ ] Customer reports

#### 2. Containment
- [ ] Revoke compromised credentials
- [ ] Block suspicious IPs
- [ ] Enable maintenance mode if needed
- [ ] Preserve logs for analysis

#### 3. Investigation
- [ ] Review access logs
- [ ] Check for data exfiltration
- [ ] Identify attack vector
- [ ] Document timeline

#### 4. Recovery
- [ ] Generate new credentials
- [ ] Patch vulnerability
- [ ] Restore from backup if needed
- [ ] Verify system integrity

#### 5. Post-Incident
- [ ] Write incident report
- [ ] Update security procedures
- [ ] Notify affected parties (if required by GDPR)
- [ ] Implement additional monitoring

### Contact
For security incidents, contact:
- Technical Lead: [your-email]
- Security Response: [security-email]

---

## Security Headers

The following headers are automatically added to all responses:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
```

## File Upload Security

1. **File type validation**: Magic bytes checked, not just extension
2. **Size limits**: 10MB maximum
3. **Malware scanning**: ClamAV integration
4. **Auto-deletion**: Files deleted after 24 hours

## Rate Limiting

- Upload: 10 requests per minute per IP+UserAgent
- Process: 10 requests per minute per IP+UserAgent
- Internal API: Requires API key authentication

---

*Last updated: 2026-01-15*
