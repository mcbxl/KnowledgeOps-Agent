# Deployment Guide

This guide describes local development, production-like configuration, and the environment variables needed to demonstrate the full system.

## Services

KnowledgeOps Agent uses:

- FastAPI backend
- React/Vite frontend
- MySQL metadata store
- Qdrant vector database
- Optional OpenAI-compatible model access through LangChain

## Local Development

Start infrastructure:

```powershell
docker compose up -d mysql qdrant
```

Install and run backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Install and run frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Production-Like Backend Configuration

Create `backend/.env` from `backend/.env.example`.

Recommended production-like values:

```text
KNOWLEDGEOPS_ENVIRONMENT=production
KNOWLEDGEOPS_DATABASE_URL=mysql+pymysql://knowledgeops:knowledgeops@127.0.0.1:3306/knowledgeops?charset=utf8mb4
KNOWLEDGEOPS_API_KEY=replace-with-a-long-random-secret

KNOWLEDGEOPS_ALLOW_WEB_INGEST=true
KNOWLEDGEOPS_ALLOW_PRIVATE_WEB_INGEST=false
KNOWLEDGEOPS_MAX_UPLOAD_BYTES=5242880
KNOWLEDGEOPS_ALLOWED_UPLOAD_EXTENSIONS=txt,md,markdown,pdf

KNOWLEDGEOPS_EMBEDDING_PROVIDER=openai
KNOWLEDGEOPS_EMBEDDING_MODEL=text-embedding-3-small
KNOWLEDGEOPS_EMBEDDING_DIMENSIONS=256

KNOWLEDGEOPS_LLM_PROVIDER=openai
KNOWLEDGEOPS_LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=replace-with-provider-key

KNOWLEDGEOPS_ENABLE_QDRANT=true
KNOWLEDGEOPS_QDRANT_URL=http://127.0.0.1:6333
KNOWLEDGEOPS_QDRANT_COLLECTION=knowledgeops_chunks

KNOWLEDGEOPS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Install production integrations:

```powershell
cd backend
pip install -e .[prod]
```

## Frontend Configuration

Create `frontend/.env`:

```text
VITE_API_BASE=http://127.0.0.1:8000/api
VITE_API_KEY=replace-with-the-same-api-key
```

If `KNOWLEDGEOPS_API_KEY` is empty in development, `VITE_API_KEY` can also be empty.

## Runtime Readiness

After booting the backend, check:

```text
GET http://127.0.0.1:8000/api/runtime/status
```

In the frontend, open the Runtime tab.

Expected local fallback state:

- Metadata Store: ok
- Embedding Model: degraded if local deterministic embedding is used
- Answer Generator: degraded if local citation generator is used
- Vector Index: degraded if Qdrant is disabled
- Security Guardrails: ok unless private web ingest is enabled

Expected production-like state:

- Metadata Store: ok
- Embedding Model: ok
- Answer Generator: ok
- Vector Index: ok
- Security Guardrails: ok

## Verification

Backend:

```powershell
cd backend
python -m pytest
python -m ruff check .
```

Frontend:

```powershell
cd frontend
npm run build
```

Current expected result:

```text
backend pytest: pass
backend ruff: pass
frontend build: pass
```

## Security Notes

- API key protection is enabled when `KNOWLEDGEOPS_API_KEY` is set.
- The client must send `X-API-Key`.
- Every response includes `X-Request-ID`.
- URL ingestion blocks localhost, private IP, link-local, reserved, multicast, and unspecified IP targets unless explicitly allowed.
- Uploads are constrained by max byte size and extension whitelist.
- Model provider keys are loaded only from environment variables.

## Migration Note

The project currently uses SQLAlchemy `metadata.create_all` to keep local development simple. For a long-running production deployment, the next operational step would be adding Alembic migrations for table evolution.
