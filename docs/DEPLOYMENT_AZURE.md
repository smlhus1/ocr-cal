# Azure Deployment Guide for ShiftSync

This guide covers deploying ShiftSync to Azure services.

## Architecture Overview

```
┌─────────────────┐      HTTPS/API      ┌──────────────────┐
│   Vercel        │ ←─────────────────→ │  Azure Container │
│   Frontend      │                      │  Instances       │
│   (Next.js)     │                      │  (FastAPI)       │
└─────────────────┘                      └──────────────────┘
                                                  │
                    ┌─────────────────────────────┴─────────────────────────────┐
                    │                             │                              │
            ┌───────▼───────┐           ┌────────▼────────┐           ┌─────────▼─────────┐
            │  Azure DB     │           │  Azure Blob     │           │  Azure Key Vault  │
            │  PostgreSQL   │           │  Storage        │           │  (Secrets)        │
            └───────────────┘           └─────────────────┘           └───────────────────┘
```

## Prerequisites

- Azure subscription
- Azure CLI installed
- Docker installed locally
- GitHub repository for CI/CD

## 1. Resource Group Setup

```bash
# Create resource group in Norway East
az group create \
  --name shiftsync-rg \
  --location norwayeast
```

## 2. Azure Key Vault (Secrets Management)

### Create Key Vault
```bash
az keyvault create \
  --name shiftsync-vault \
  --resource-group shiftsync-rg \
  --location norwayeast \
  --enable-rbac-authorization true
```

### Add Secrets
```bash
# Database connection string
az keyvault secret set \
  --vault-name shiftsync-vault \
  --name DATABASE-URL \
  --value "postgresql://user:pass@shiftsync-db.postgres.database.azure.com:5432/shiftsync?sslmode=require"

# OpenAI API key
az keyvault secret set \
  --vault-name shiftsync-vault \
  --name OPENAI-API-KEY \
  --value "sk-proj-your-key-here"

# Internal API key (generate random)
az keyvault secret set \
  --vault-name shiftsync-vault \
  --name INTERNAL-API-KEY \
  --value "$(openssl rand -hex 32)"

# Secret salt (generate random)
az keyvault secret set \
  --vault-name shiftsync-vault \
  --name SECRET-SALT \
  --value "$(openssl rand -hex 32)"

# Stripe keys (if using payments)
az keyvault secret set \
  --vault-name shiftsync-vault \
  --name STRIPE-SECRET-KEY \
  --value "sk_live_your-key"
```

### Grant Access to Container
```bash
# Get container identity and grant Key Vault access
az keyvault set-policy \
  --name shiftsync-vault \
  --object-id <container-managed-identity-id> \
  --secret-permissions get list
```

## 3. Azure Database for PostgreSQL

```bash
# Create flexible server
az postgres flexible-server create \
  --resource-group shiftsync-rg \
  --name shiftsync-db \
  --location norwayeast \
  --admin-user shiftsync_admin \
  --admin-password "$(openssl rand -base64 24)" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15

# Create database
az postgres flexible-server db create \
  --resource-group shiftsync-rg \
  --server-name shiftsync-db \
  --database-name shiftsync

# Allow Azure services
az postgres flexible-server firewall-rule create \
  --resource-group shiftsync-rg \
  --name shiftsync-db \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

# Enable SSL
az postgres flexible-server parameter set \
  --resource-group shiftsync-rg \
  --server-name shiftsync-db \
  --name require_secure_transport \
  --value on
```

## 4. Azure Blob Storage

```bash
# Create storage account
az storage account create \
  --name shiftsyncfiles \
  --resource-group shiftsync-rg \
  --location norwayeast \
  --sku Standard_LRS \
  --kind StorageV2

# Create container
az storage container create \
  --name shiftsync-uploads \
  --account-name shiftsyncfiles \
  --public-access off

# Get connection string
az storage account show-connection-string \
  --name shiftsyncfiles \
  --resource-group shiftsync-rg \
  --output tsv

# Enable lifecycle management (24h auto-delete)
cat > lifecycle-policy.json << 'EOF'
{
  "rules": [
    {
      "name": "delete-old-uploads",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "blobTypes": ["blockBlob"],
          "prefixMatch": ["shiftsync-uploads/"]
        },
        "actions": {
          "baseBlob": {
            "delete": {
              "daysAfterCreationGreaterThan": 1
            }
          }
        }
      }
    }
  ]
}
EOF

az storage account management-policy create \
  --account-name shiftsyncfiles \
  --resource-group shiftsync-rg \
  --policy @lifecycle-policy.json
```

## 5. Azure Container Registry

```bash
# Create container registry
az acr create \
  --name shiftsyncregistry \
  --resource-group shiftsync-rg \
  --sku Basic \
  --admin-enabled true

# Login to registry
az acr login --name shiftsyncregistry

# Build and push image
az acr build \
  --registry shiftsyncregistry \
  --image shiftsync-backend:latest \
  ./backend
```

## 6. Azure Container Instances

```bash
# Create container instance
az container create \
  --resource-group shiftsync-rg \
  --name shiftsync-backend \
  --image shiftsyncregistry.azurecr.io/shiftsync-backend:latest \
  --cpu 1 \
  --memory 2 \
  --ports 8000 \
  --dns-name-label shiftsync-api \
  --registry-login-server shiftsyncregistry.azurecr.io \
  --registry-username $(az acr credential show -n shiftsyncregistry --query username -o tsv) \
  --registry-password $(az acr credential show -n shiftsyncregistry --query "passwords[0].value" -o tsv) \
  --environment-variables \
    ENVIRONMENT=production \
    KEY_VAULT_URL=https://shiftsync-vault.vault.azure.net \
    FRONTEND_URL=https://shiftsync.no \
  --assign-identity

# Get public URL
az container show \
  --resource-group shiftsync-rg \
  --name shiftsync-backend \
  --query ipAddress.fqdn \
  --output tsv
```

## 7. Application Insights (Monitoring)

```bash
# Create Application Insights
az monitor app-insights component create \
  --app shiftsync-insights \
  --location norwayeast \
  --resource-group shiftsync-rg \
  --kind web

# Get connection string
az monitor app-insights component show \
  --app shiftsync-insights \
  --resource-group shiftsync-rg \
  --query connectionString \
  --output tsv
```

## 8. Environment Variables Summary

For production, set these in Key Vault:

| Secret Name | Description |
|-------------|-------------|
| DATABASE-URL | PostgreSQL connection string with SSL |
| OPENAI-API-KEY | OpenAI API key (project-scoped) |
| INTERNAL-API-KEY | API key for internal endpoints |
| SECRET-SALT | Salt for hashing user identifiers |
| STRIPE-SECRET-KEY | Stripe API key (if using payments) |
| AZURE-STORAGE-CONNECTION-STRING | Blob storage connection |
| APPLICATIONINSIGHTS-CONNECTION-STRING | App Insights connection |

## 9. Custom Domain & SSL

```bash
# Add custom domain (requires DNS verification)
# Update your DNS with CNAME pointing to:
# shiftsync-api.norwayeast.azurecontainer.io

# For full SSL, consider using Azure Front Door or App Service
```

## 10. Backup Strategy

### Database Backups
Azure Postgres Flexible Server has automatic backups:
- Point-in-time recovery for 35 days
- Geo-redundant backups available

```bash
# Enable geo-redundant backups
az postgres flexible-server update \
  --resource-group shiftsync-rg \
  --name shiftsync-db \
  --backup-retention 35 \
  --geo-redundant-backup Enabled
```

### Manual Backup
```bash
# Export database
pg_dump -h shiftsync-db.postgres.database.azure.com \
  -U shiftsync_admin \
  -d shiftsync \
  --format=custom \
  --file=backup_$(date +%Y%m%d).dump
```

## Estimated Costs (Monthly)

| Service | SKU | Est. Cost |
|---------|-----|-----------|
| Container Instances | 1 CPU, 2GB | ~$30 |
| PostgreSQL Flexible | Burstable B1ms | ~$15 |
| Blob Storage | 50GB Hot | ~$1 |
| Key Vault | Standard | ~$1 |
| Application Insights | Basic | ~$5 |
| **Total** | | **~$52/month** |

## Security Checklist

- [ ] Key Vault configured with RBAC
- [ ] Database SSL enforced
- [ ] Blob storage private access only
- [ ] Container runs as non-root user
- [ ] Network security groups configured
- [ ] Application Insights PII filtering enabled
- [ ] Backup geo-redundancy enabled
