# Doclarity

AI analytics & document intelligence platform. Upload invoices, contracts,
and financial docs → extract structured data → ask
questions in natural language (RAG for document Q&A, text-to-SQL for
analytics) → get dashboards and anomaly alerts, with citations back to source
documents.

## Status

**Slice 2 (this commit): Extract → structure.** Upload now kicks off a Celery
task that parses the file (pdfplumber for PDF, pandas for CSV/XLSX) and calls
the LLM with a forced tool-use schema to pull structured fields into
`document_extractions`, with a validation pass flagging low-confidence rows.
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
   cp .env.example .env   # fill in ANTHROPIC_API_KEY (see "Trying it without
                           # an API key" below if you don't have one yet)
   uvicorn app.main:app --reload
   ```
   The app creates its tables on startup (`documents`, `document_extractions`)
   — no separate migration step yet.
3. Celery worker (separate terminal, same venv — Windows needs the `solo`
   pool since the default `prefork` pool doesn't work there):
   ```bash
   cd backend
   celery -A app.core.celery_app worker --loglevel=info --pool=solo
   ```
4. Check the API's alive: `curl http://localhost:8000/health`

## Using it

The easiest way to click through the API is the interactive docs FastAPI
generates automatically: **http://localhost:8000/docs**. Every endpoint can
be run from there with a "Try it out" button — no curl needed.

### Uploading a document

```bash
curl -F "file=@samples/sample_invoice.pdf" http://localhost:8000/documents/upload
curl http://localhost:8000/documents
curl http://localhost:8000/documents/{id}/extractions
```

Upload enqueues a Celery task immediately; poll `GET /documents/{id}` until
`status` moves off `"uploaded"`/`"processing"` to `"processed"` or `"failed"`,
then check `GET /documents/{id}/extractions` for the structured rows. A row's
own `status` is `"completed"`, `"needs_review"` (validation flagged
something — see `confidence_flags`), or `"failed"`.

### Sample files

`samples/` has a few files to try, chosen to exercise different paths:

| File | Type | What it tests |
|---|---|---|
| `sample_invoice.pdf` | PDF invoice | pdfplumber text/table extraction, line-items-vs-total validation (deliberately balances exactly) |
| `sample_contract.pdf` | PDF contract | the `document_type: contract` path — no canonical invoice fields expected |
| `sample_invoices.csv` | CSV | column-mapping to the canonical schema; row 3 has a bogus `ZZZ` currency to trigger `needs_review` |
| `sample_transactions.csv` | CSV | differently-named columns, a missing amount, a negative amount, and a malformed `payment_terms_days` value |

### Trying it without an API key

The extraction step calls the Anthropic API, which is billed separately from
a Claude.ai subscription — if you don't have a key yet (or don't want to
spend one testing), seed the database with the same files run through the
*real* parsing, database, and validation code, with only the LLM's response
stubbed out:

```bash
cd backend
python scripts/seed_demo_data.py
```

This inserts real `documents`/`document_extractions` rows for every file in
`samples/`, so `GET /documents` and the extractions endpoint have real data
to look at immediately. It does **not** touch the network. Once you do have
a key, uploads through the API (or the Swagger UI) will run the real thing.

## Running the tests

```bash
cd backend
pytest tests/ -v
```

This runs both the unit tests (parsers, validation, row-building — no
network or database needed) and `tests/integration/test_live_api.py`, which
exercises the actual running stack: upload → Celery pickup → a terminal
status, plus the list/get/404 endpoints. The integration tests auto-skip if
nothing is listening on `http://localhost:8000`, so `pytest tests/` is safe
to run whether or not the server is up.

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
