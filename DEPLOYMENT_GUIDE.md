# Deployment Guide - ShiftSync

Denne guiden viser steg-for-steg hvordan du deployer ShiftSync til Azure (backend) og Vercel (frontend).

## 📋 Forutsetninger

Før du starter:

- [ ] Azure-konto med aktiv subscription
- [ ] Vercel-konto
- [ ] GitHub repository opprettet
- [ ] Stripe-konto (for betalingsfunksjonalitet)
- [ ] PostgreSQL database (Azure eller ekstern)

## 🔧 Del 1: Lokal Forberedelse

### 1. Last opp kode til GitHub

```bash
# Initialiser Git (hvis ikke allerede gjort)
git init
git add .
git commit -m "Initial commit: ShiftSync v1.0"

# Opprett remote repository på GitHub
# Deretter push:
git remote add origin https://github.com/<ditt-brukernavn>/shiftsync.git
git branch -M main
git push -u origin main
```

### 2. Opprett `.gitignore` (hvis ikke eksisterer)

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
.env
.venv
venv/
*.egg-info/

# Node
node_modules/
.next/
out/
.vercel

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Uploads (lokal testing)
uploads/
KalenderFiler/
Bilder/
```

### 3. Valider Docker-bygg lokalt

```bash
# Test backend Docker-bygg
cd backend
docker build -t shiftsync-backend:test .
docker run -p 8000:8000 shiftsync-backend:test

# Test med docker-compose
cd ..
docker-compose up
```

## 🚀 Del 2: Azure Deployment (Backend)

### Steg 1: Opprett Azure Resources

#### 1.1 Resource Group

```bash
az login

az group create \
  --name shiftsync-rg \
  --location northeurope
```

#### 1.2 PostgreSQL Database

**Alternativ A: Azure Database for PostgreSQL (Anbefalt)**

```bash
az postgres flexible-server create \
  --resource-group shiftsync-rg \
  --name shiftsync-db \
  --location northeurope \
  --admin-user shiftsyncadmin \
  --admin-password '<STERKT_PASSORD>' \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15

# Opprett database
az postgres flexible-server db create \
  --resource-group shiftsync-rg \
  --server-name shiftsync-db \
  --database-name shiftsync
```

**Alternativ B: Supabase / Neon (Billigere)**
- Gå til https://supabase.com eller https://neon.tech
- Opprett gratis PostgreSQL database
- Kopier `DATABASE_URL` connection string

#### 1.3 Azure Storage Account

```bash
az storage account create \
  --name shiftsyncstore \
  --resource-group shiftsync-rg \
  --location northeurope \
  --sku Standard_LRS

# Opprett container for uploads
az storage container create \
  --name shiftsync-uploads \
  --account-name shiftsyncstore \
  --public-access off

# Hent connection string
az storage account show-connection-string \
  --name shiftsyncstore \
  --resource-group shiftsync-rg
```

#### 1.4 Azure Key Vault (Valgfritt, men anbefalt)

```bash
az keyvault create \
  --name shiftsync-kv \
  --resource-group shiftsync-rg \
  --location northeurope

# Legg til secrets
az keyvault secret set \
  --vault-name shiftsync-kv \
  --name DATABASE-URL \
  --value "postgresql://..."

az keyvault secret set \
  --vault-name shiftsync-kv \
  --name STRIPE-SECRET-KEY \
  --value "sk_live_..."
```

#### 1.5 Azure Container Apps Environment

```bash
az containerapp env create \
  --name shiftsync-env \
  --resource-group shiftsync-rg \
  --location northeurope
```

### Steg 2: Konfigurer GitHub Secrets

Gå til GitHub repository → Settings → Secrets and variables → Actions

Legg til følgende secrets:

- `AZURE_CREDENTIALS` (for GitHub Actions deploy)
- `DATABASE_URL`
- `AZURE_STORAGE_CONNECTION_STRING`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SECRET_SALT` (generer med: `openssl rand -hex 32`)

**For å få AZURE_CREDENTIALS:**

```bash
az ad sp create-for-rbac \
  --name "shiftsync-github" \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/shiftsync-rg \
  --sdk-auth
```

Kopier hele JSON-outputen til `AZURE_CREDENTIALS`-secreten.

### Steg 3: Deploy via GitHub Actions

GitHub Actions vil automatisk deploye når du pusher til `main`. Men for første gang:

```bash
git push origin main
```

Gå til GitHub → Actions og følg deployment-prosessen.

**Manuell deploy (hvis ønskelig):**

```bash
az containerapp create \
  --name shiftsync-backend \
  --resource-group shiftsync-rg \
  --environment shiftsync-env \
  --image ghcr.io/<github-username>/shiftsync-backend:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    TESSERACT_PATH=/usr/bin/tesseract \
    AZURE_STORAGE_CONNECTION_STRING=secretref:azure-storage \
    STRIPE_SECRET_KEY=secretref:stripe-key \
    ENVIRONMENT=production \
  --secrets \
    database-url="postgresql://..." \
    azure-storage="DefaultEndpointsProtocol=..." \
    stripe-key="sk_live_..."
```

### Steg 4: Kjør Database Migrations

```bash
# SSH inn i container eller kjør via Azure CLI
az containerapp exec \
  --name shiftsync-backend \
  --resource-group shiftsync-rg \
  --command "psql $DATABASE_URL -f migrations/001_initial_schema.sql"
```

Alternativt, bruk lokal psql:

```bash
psql "<DATABASE_URL>" -f backend/migrations/001_initial_schema.sql
```

## 🌐 Del 3: Vercel Deployment (Frontend)

### Steg 1: Installer Vercel CLI

```bash
npm install -g vercel
```

### Steg 2: Deploy til Vercel

```bash
cd frontend
vercel login

# Link til Vercel project
vercel link

# Deploy
vercel --prod
```

### Steg 3: Konfigurer Environment Variables i Vercel

Gå til Vercel Dashboard → Project → Settings → Environment Variables

Legg til:
- `NEXT_PUBLIC_API_URL` = `https://shiftsync-backend.azurecontainerapps.io` (din Azure URL)

### Steg 4: Oppdater GitHub Actions Secrets

Legg til i GitHub Secrets:
- `VERCEL_TOKEN` (fra https://vercel.com/account/tokens)
- `VERCEL_ORG_ID` (finn i Vercel project settings)
- `VERCEL_PROJECT_ID` (finn i Vercel project settings)
- `NEXT_PUBLIC_API_URL`

### Steg 5: Test Deployment

```bash
# Test backend health check
curl https://shiftsync-backend.azurecontainerapps.io/health

# Test frontend
open https://shiftsync.vercel.app
```

## 💳 Del 4: Stripe-konfigurasjon

### 1. Opprett Stripe Products

Gå til Stripe Dashboard → Products → Add Product

- **Navn:** ShiftSync Premium
- **Pris:** 99 NOK/måned
- **Recurring:** Monthly
- **Billing period:** Monthly

### 2. Konfigurer Webhook

Stripe Dashboard → Developers → Webhooks → Add endpoint

**Endpoint URL:**
```
https://shiftsync-backend.azurecontainerapps.io/api/payment/webhook
```

**Events to send:**
- `checkout.session.completed`
- `customer.subscription.deleted`
- `invoice.payment_failed`

Kopier **Signing secret** og legg til i Azure secrets som `STRIPE_WEBHOOK_SECRET`.

### 3. Test Betaling

Bruk Stripe test cards:
- **Successful:** `4242 4242 4242 4242`
- **Declined:** `4000 0000 0000 0002`

## 📊 Del 5: Monitoring Setup (Azure Application Insights)

### 1. Opprett Application Insights

```bash
az monitor app-insights component create \
  --app shiftsync-insights \
  --location northeurope \
  --resource-group shiftsync-rg \
  --application-type web

# Hent Instrumentation Key
az monitor app-insights component show \
  --app shiftsync-insights \
  --resource-group shiftsync-rg \
  --query instrumentationKey
```

### 2. Legg til i Azure Container App

```bash
az containerapp update \
  --name shiftsync-backend \
  --resource-group shiftsync-rg \
  --set-env-vars AZURE_APPLICATION_INSIGHTS_KEY=<instrumentation-key>
```

### 3. Konfigurer Alerts

Azure Portal → Application Insights → Alerts → New Alert Rule

**Anbefalte alerts:**
- Response time > 2 sekunder
- Failed requests > 5% av totalen
- Unhealthy health checks
- Database connection failures

## ✅ Del 6: Verifiser Deployment

### Sjekkliste:

- [ ] Backend health check: `https://<backend-url>/health`
- [ ] Frontend laster: `https://<frontend-url>`
- [ ] File upload fungerer
- [ ] OCR processing fungerer
- [ ] Calendar download fungerer
- [ ] Stripe checkout fungerer (test mode)
- [ ] Rate limiting fungerer (test med 10+ requests)
- [ ] HTTPS aktivert på begge
- [ ] CORS fungerer mellom frontend og backend
- [ ] Application Insights logger events
- [ ] Database migrations kjørt

## 🔧 Feilsøking

### Backend vil ikke starte

```bash
# Sjekk logger
az containerapp logs show \
  --name shiftsync-backend \
  --resource-group shiftsync-rg \
  --follow

# Sjekk environment variables
az containerapp show \
  --name shiftsync-backend \
  --resource-group shiftsync-rg \
  --query properties.template.containers[0].env
```

### Frontend kan ikke nå backend

- Sjekk at `NEXT_PUBLIC_API_URL` er riktig
- Verifiser CORS settings i backend (`frontend_url` i config)
- Test backend direkte med `curl`

### Database connection errors

```bash
# Test connection
psql "$DATABASE_URL" -c "SELECT 1;"

# Sjekk firewall rules (Azure)
az postgres flexible-server firewall-rule create \
  --resource-group shiftsync-rg \
  --name shiftsync-db \
  --rule-name AllowAllAzure \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

## 💰 Kostnadsoversikt

**Estimerte månedlige kostnader (Norsk produksjon, <1000 brukere):**

| Tjeneste | Anbefalt tier | Månedlig kostnad |
|----------|---------------|------------------|
| Azure Container Apps | Consumption plan | ~100-300 NOK |
| PostgreSQL (Supabase Free) | Free | 0 NOK |
| Azure Blob Storage | Standard LRS | ~50 NOK |
| Application Insights | Basic | ~100 NOK |
| Vercel | Hobby | 0 NOK (eller 200 NOK for Pro) |
| **Total** | | **~250-550 NOK/måned** |

**Alternativ billig-løsning (<100 NOK/måned):**
- Railway.app eller Render.com for backend (~$5/måned)
- Supabase for database (gratis)
- Cloudflare R2 for storage (gratis tier)
- Vercel Hobby (gratis)

## 🎯 Neste Steg

1. Sett opp custom domain (f.eks. `shiftsync.no`)
2. Konfigurer SSL certificate (automatisk via Azure/Vercel)
3. Aktiver Stripe live mode med ekte betalinger
4. Markedsfør løsningen! 🚀

---

**Lykke til med deployment!** 🎉

*Ved spørsmål eller problemer, sjekk logs og dokumentasjon først. For avansert feilsøking, kontakt Azure/Vercel support.*

