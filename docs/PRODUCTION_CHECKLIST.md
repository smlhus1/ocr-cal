# Production Deployment Checklist

Use this checklist before deploying ShiftSync to production.

## Pre-Deployment

### 1. Secrets Configuration
- [ ] All secrets stored in Azure Key Vault (not in .env)
- [ ] `DATABASE_URL` configured with SSL
- [ ] `OPENAI_API_KEY` is project-scoped with spending limit
- [ ] `INTERNAL_API_KEY` is a random 32+ character string
- [ ] `SECRET_SALT` is a random 32+ character string
- [ ] `SENTRY_DSN` configured for error tracking
- [ ] Stripe keys are live (not test) keys

### 2. Environment Variables
- [ ] `ENVIRONMENT=production`
- [ ] `FRONTEND_URL` points to production domain (with https://)
- [ ] `KEY_VAULT_URL` is set correctly

### 3. Database
- [ ] PostgreSQL server created in Azure
- [ ] SSL mode enforced
- [ ] Firewall rules configured (Azure services only)
- [ ] Initial schema migrated
- [ ] Backup retention enabled (35 days recommended)
- [ ] Geo-redundant backup enabled

### 4. Storage
- [ ] Azure Blob Storage container created
- [ ] Lifecycle management policy set (24h auto-delete)
- [ ] Private access only (no public blobs)

### 5. Security Review
- [ ] `.gitignore` includes all sensitive files
- [ ] No secrets in Git history
- [ ] HTTPS redirect enabled
- [ ] Security headers configured
- [ ] Rate limiting active
- [ ] ClamAV configured (or disabled with documented reason)

## Deployment

### 6. Container Registry
- [ ] Backend image built and pushed to ACR
- [ ] Image tagged with commit SHA and `latest`
- [ ] Previous versions retained for rollback

### 7. Container Instance
- [ ] Container deployed to Azure Container Instances
- [ ] Managed identity configured
- [ ] Key Vault access granted to container
- [ ] Health check endpoint responding

### 8. Frontend (Vercel)
- [ ] Frontend deployed to Vercel
- [ ] Environment variables set in Vercel
- [ ] Production branch configured
- [ ] Custom domain configured

### 9. DNS & SSL
- [ ] Custom domain DNS configured
- [ ] CNAME for www redirects to root
- [ ] SSL certificates issued (automatic with Vercel/Azure)
- [ ] HSTS header enabled

## Post-Deployment

### 10. Verification
- [ ] Health endpoint returns 200: `https://api.shiftsync.no/health`
- [ ] Frontend loads correctly: `https://shiftsync.no`
- [ ] Upload flow works end-to-end
- [ ] AI processing works (if API key configured)
- [ ] Calendar download works
- [ ] Rate limiting triggers after 10 requests

### 11. Monitoring
- [ ] Sentry receiving events
- [ ] Application Insights dashboard accessible
- [ ] Alerts configured for:
  - [ ] Error rate > 5%
  - [ ] Response time > 10s
  - [ ] Container health failure
  - [ ] Database connection errors

### 12. Documentation
- [ ] Privacy Policy accessible at /privacy
- [ ] Terms of Service accessible at /terms
- [ ] API documentation available (internal only)

### 13. Backup Verification
- [ ] Run test backup: `./scripts/backup_database.sh`
- [ ] Verify backup file created
- [ ] Test restore procedure in staging

## Rollback Plan

If deployment fails:

1. **Identify issue** in logs/Sentry
2. **Rollback container**: 
   ```bash
   az container create ... --image shiftsyncregistry.azurecr.io/backend:previous-sha
   ```
3. **Rollback frontend**: Redeploy previous commit in Vercel
4. **Rollback database**: Only if schema changed (use Azure PITR)
5. **Notify team** of incident

## Emergency Contacts

- **On-call**: [your-oncall-system]
- **Azure Support**: [support-link]
- **Vercel Support**: [support-link]

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Reviewer | | | |
| Operations | | | |

---

*Last updated: January 15, 2026*
