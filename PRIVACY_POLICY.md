# Privacy Policy for ShiftSync

**Last updated:** January 15, 2026

## Introduction

ShiftSync ("we", "our", "us") respects your privacy and is committed to protecting your personal data. This privacy policy explains how we handle your information when you use our shift schedule conversion service.

## What Data We Collect

### Data We DO Collect (Anonymized)
- **File metadata**: File type (JPEG, PNG, PDF), file size
- **Processing metrics**: Number of shifts found, confidence score, processing time
- **Country-level location**: Derived from IP address (country only, not specific location)
- **Technical data**: Browser type, device type (for analytics only)

### Data We DO NOT Collect
- **Personal names** from shift schedules
- **Email addresses**
- **Phone numbers**
- **Raw IP addresses** (we only derive country, then discard)
- **Uploaded images** (deleted within 24 hours)
- **Calendar files** (generated on-demand, not stored)

## How We Process Your Data

### Uploaded Files
1. You upload a shift schedule image
2. Our OCR system extracts shift times (no names are stored)
3. You review and edit the shifts
4. You download the calendar file
5. **Your uploaded file is automatically deleted within 24 hours**

### IP Address Handling
- We hash your IP address with a salt immediately upon receipt
- The raw IP is never stored
- Only the country code is retained for aggregate statistics

## Legal Basis (GDPR Article 6)

We process data based on:
- **Legitimate interest**: To provide and improve our service
- **Contract**: To fulfill the service you requested

## Data Retention

| Data Type | Retention Period | Reason |
|-----------|-----------------|--------|
| Uploaded files | 24 hours | Service delivery |
| Processing metadata | 30 days | Service improvement |
| Aggregate statistics | Indefinite | Analytics |

## Your Rights (GDPR Articles 15-22)

You have the right to:

1. **Access** - Request a copy of data we hold about you
2. **Rectification** - Correct inaccurate data
3. **Erasure** - Request deletion of your data
4. **Restriction** - Limit how we use your data
5. **Portability** - Receive your data in a portable format
6. **Object** - Object to certain processing

**To exercise these rights**, contact us at: [your-email@domain.com]

Since we don't store personally identifiable information, most data cannot be linked back to you.

## Cookies

ShiftSync does **not** use cookies for tracking. We only use essential technical cookies for:
- Session management (if logged in)
- Security (CSRF protection)

No third-party tracking cookies are used.

## Third-Party Services

We use the following third-party services:

| Service | Purpose | Data Shared |
|---------|---------|-------------|
| OpenAI | AI-enhanced OCR | Uploaded images (processed, not stored) |
| Sentry | Error tracking | Anonymous error reports |
| Azure | Cloud hosting | Encrypted data storage |

All third parties are GDPR-compliant and have Data Processing Agreements in place.

## International Transfers

Your data may be processed in:
- Norway (primary)
- European Union (Azure data centers)
- United States (OpenAI, Sentry - with Standard Contractual Clauses)

## Security Measures

We implement:
- **Encryption**: All data encrypted in transit (TLS 1.3) and at rest (AES-256)
- **Access control**: Role-based access to systems
- **Monitoring**: Real-time security monitoring
- **Automatic deletion**: Files deleted after 24 hours
- **Regular audits**: Security assessments and penetration testing

## Children's Privacy

ShiftSync is not intended for children under 16. We do not knowingly collect data from children.

## Changes to This Policy

We may update this policy periodically. Changes will be posted on this page with an updated date.

## Contact Us

For privacy-related inquiries:
- **Email**: [privacy@shiftsync.no]
- **Address**: [Your business address]

## Data Protection Officer

[If applicable, include DPO contact information]

## Supervisory Authority

You have the right to lodge a complaint with the Norwegian Data Protection Authority (Datatilsynet):
- Website: https://www.datatilsynet.no
- Email: postkasse@datatilsynet.no
