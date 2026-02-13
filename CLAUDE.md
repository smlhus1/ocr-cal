# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShiftSync is a SaaS application that converts shift schedule images to iCalendar (.ics) files using OCR. It has two parts:

1. **Standalone CLI script** (`vaktplan_konverter.py`) - the original local Python tool using Tesseract OCR
2. **Web application** - a full-stack SaaS with FastAPI backend + Next.js frontend

The product name is "ShiftSync", the domain is `shiftsync.no`.

## Commands

### Standalone CLI script
```powershell
py vaktplan_konverter.py
```
Reads images from `Bilder/`, outputs `KalenderFiler/alle_vakter.ics`.

### Backend (FastAPI)
```powershell
cd backend
py -m uvicorn app.main:app --reload --port 8000
```
API docs available at `http://localhost:8000/docs` in development.

### Frontend (Next.js)
```powershell
cd frontend
npm run dev          # Dev server on port 3000
npm run build        # Production build
npm run lint         # ESLint
npm run type-check   # TypeScript check (tsc --noEmit)
```

### Docker (full stack)
```powershell
docker-compose up              # Start all services (backend + PostgreSQL)
docker-compose build --no-cache  # Rebuild after dependency changes
```

### Dependencies
```powershell
# Root-level venv (CLI script)
py -m pip install -r requirements.txt

# Backend
py -m pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install
```

### Database
```powershell
# Apply migrations to PostgreSQL
psql "<DATABASE_URL>" -f backend/migrations/001_initial_schema.sql
```

### Tests
```powershell
# Backend security tests
cd backend && py -m pytest tests/
```

## Architecture

### Two-Track Design

The project runs two parallel systems from the same repo:

- **CLI track**: `vaktplan_konverter.py` + root `requirements.txt` + local venv (`Lib/`, `Scripts/`) - standalone, no network, reads local images
- **Web track**: `backend/` + `frontend/` + `docker-compose.yml` - full SaaS with auth-free anonymous processing

### Backend (`backend/app/`)

FastAPI application structured as:

- `main.py` - App factory with middleware stack (CORS, security headers, rate limiting, request timing/audit logging)
- `config.py` - Pydantic Settings loading from `.env` + optional Azure Key Vault in production
- `models.py` - Pydantic request/response models (NOT database models)
- `database.py` - SQLAlchemy async models (`UploadAnalytics`, `FeedbackLog`, `AnonymousSession`) + query helpers
- `security.py` - Rate limiter (slowapi), file validation (magic bytes), IP hashing, internal API key verification
- `api/` - Route handlers: `upload.py`, `process.py`, `download.py`, `feedback.py`, `analytics.py`, `payment.py`
- `ocr/processor.py` - `VaktplanProcessor` class: Tesseract-based OCR with image preprocessing, Norwegian shift text extraction
- `ocr/calendar_generator.py` - Standalone iCal generation (no Tesseract dependency)
- `ocr/vision_processor.py` - `VisionProcessor` class: GPT-4o Vision alternative for higher accuracy
- `ocr/confidence_scorer.py` - Confidence scoring for OCR results
- `storage/blob_storage.py` - Azure Blob Storage integration

**Processing pipeline**: Upload image -> Store in Azure Blob/local -> OCR (Tesseract or GPT-4 Vision) -> Extract shifts -> User reviews/edits -> Generate .ics -> Auto-delete after 24h

**Two OCR engines**: `method: "ocr"` uses Tesseract (free, local), `method: "ai"` uses GPT-4o Vision (paid, more accurate).

### Frontend (`frontend/`)

Next.js 15 with App Router, React 19, Tailwind CSS, TypeScript.

- `app/page.tsx` - Landing page with upload
- `app/preview/[id]/page.tsx` - Preview/edit OCR results
- `app/preview/batch/page.tsx` - Batch processing
- `components/DragDropUpload.tsx` - Drag & drop file upload (react-dropzone)
- `components/ShiftTable.tsx` - Editable shift table with inline editing
- `components/ConfidenceIndicator.tsx` - Visual confidence score indicator
- `lib/api-client.ts` - Typed API client (axios singleton) matching backend Pydantic models
- `lib/validation.ts` - Client-side file validation

The API URL is configured via `NEXT_PUBLIC_API_URL` env var.

### Database

PostgreSQL with only anonymized data (GDPR-compliant). Managed with **Alembic** migrations (`backend/alembic/`).

Tables:
- `upload_analytics` - Upload metadata, OCR results, session_id, auto-expires after 24h
- `feedback_log` - Anonymized user corrections for ML improvements
- `anonymous_sessions` - Session cookie -> Stripe subscription mapping for quota enforcement

No user accounts, no PII stored. Quota tracked via anonymous session cookies.

```powershell
# Run migrations
cd backend && alembic upgrade head

# Create new migration
cd backend && alembic revision -m "description"
```

### OCR Text Patterns

The Norwegian shift schedule regex pattern expects:
```
[month name] [4-digit year]
[weekday] HH:MM - HH:MM
[day number]
```
Supports all 12 Norwegian month names and 7 weekdays. Handles space-in-digits OCR artifacts (e.g., "2 3" -> 23) and multi-month images.

### Shift Type Classification

| Type    | Start time range |
|---------|-----------------|
| tidlig  | 06:00 - 11:59   |
| mellom  | 12:00 - 15:59   |
| kveld   | 16:00 - 21:59   |
| natt    | 22:00 - 05:59   |

### External Services

- **Tesseract OCR** - Required system dependency (Windows: `C:\Program Files\Tesseract-OCR\tesseract.exe`)
- **OpenAI GPT-4o** - Optional, for AI vision processing
- **Azure Blob Storage** - File storage (optional in dev, uses local)
- **Azure Key Vault** - Secrets management in production
- **Stripe** - Payment processing (freemium: 2 free/month, 99 NOK/month premium)
- **Sentry** - Error tracking
- **Azure Application Insights** - Monitoring

### Deployment

- Backend: Azure Container Apps (Docker)
- Frontend: Vercel
- Database: PostgreSQL (Supabase or Azure)
- CI/CD: GitHub Actions (`.github/workflows/`)

## Environment Variables

Backend requires at minimum: `DATABASE_URL`, `SECRET_SALT`. See `backend/.env.example` for full list.
Frontend requires: `NEXT_PUBLIC_API_URL`.
CLI script uses root `.env`: `TESSERACT_PATH`, `OCR_LANGUAGE`, `INPUT_FOLDER`, `OUTPUT_FOLDER`.
