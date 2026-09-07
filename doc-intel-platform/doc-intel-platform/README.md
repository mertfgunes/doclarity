# AI Analytics & Document Intelligence Platform

Upload invoices, contracts, and financial docs → extract structured data → ask
questions in natural language (RAG for document Q&A, text-to-SQL for
analytics) → get dashboards and anomaly alerts, with citations back to source
documents.

## Status

**Slice 1 (this commit): Upload → store → list.**
See `docs/ROADMAP.md` for the full slice-by-slice plan.

## Stack

- Backend: FastAPI + SQLAlchemy + PostgreSQL (pgvector) + Celery/Redis
- Frontend: Next.js + TypeScript + Tailwind
- LLM: Anthropic API

## Local setup

1. Start infra:
   ```bash
   docker compose up -d
   ```
2. Backend:
   ```bash
   cd backend
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # fill in ANTHROPIC_API_KEY
   uvicorn app.main:app --reload
   ```
3. Check it's alive: `curl http://localhost:8000/health`
4. Try an upload:
   ```bash
   curl -F "file=@sample.pdf" http://localhost:8000/documents/upload
   curl http://localhost:8000/documents
   ```

Frontend scaffolding comes in the next slice, once the upload/list API is
solid.

## Why this architecture

- **pgvector instead of a dedicated vector DB** — one less service to run,
  and it's genuinely fine at portfolio-project scale. Worth mentioning in
  interviews as a deliberate simplicity trade-off, not an oversight.
- **Celery for background processing** — large PDFs shouldn't block the
  upload request. This becomes the answer to "how does this handle a
  200-page contract?"
- **Explicit RAG-vs-SQL routing (Slice 5)** — the differentiator vs. a
  typical "chat with your PDF" student project. Worth being able to explain
  in detail in an interview.
