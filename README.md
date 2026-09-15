# Doclarity

AI analytics & document intelligence platform. Upload invoices, contracts,
and financial docs → extract structured data → ask
questions in natural language (RAG for document Q&A, text-to-SQL for
analytics) → get dashboards and anomaly alerts, with citations back to source
documents.

## Status

**Slice 5 (this commit): Route between RAG and SQL.** A new `POST /query`
endpoint decides for itself whether a question needs semantic search over
document text, a SQL query over structured records, or both - and for
"both" questions, synthesizes one coherent answer from both findings
instead of concatenating them. This is now the main way to use the app -
see "Asking questions (routed - the main way to use this)" below. See
`docs/ROADMAP.md` for the full slice-by-slice plan.

## Stack

- Backend: FastAPI + SQLAlchemy + PostgreSQL (pgvector) + Celery/Redis
- Frontend: Next.js + TypeScript + Tailwind
- LLM: Anthropic API or a local [Ollama](https://ollama.com) model (default -
  see "Choosing an LLM backend" below). Anthropic has no embeddings API, so
  embeddings always go through Ollama regardless of which one is used for
  extraction.

## Local setup

1. Start infra:
   ```bash
   docker compose up -d
   ```
   On a fresh volume this also creates the `doclarity_readonly` Postgres role
   used by Slice 4's analytics endpoint (`db/init/01_readonly_role.sql` runs
   automatically). If you already had the `postgres` container running from
   before that file existed, apply it once by hand:
   ```bash
   docker exec -i doclarity_postgres psql -U doclarity -d doclarity < db/init/01_readonly_role.sql
   ```
2. Backend:
   ```bash
   cd backend
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env   # defaults to the local Ollama backend - see
                           # "Choosing an LLM backend" below for the Anthropic option
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

## Choosing an LLM backend

`LLM_PROVIDER` in `.env` picks what extraction/column-mapping calls run
against; `EMBEDDING_PROVIDER` (Slice 3) is separate because Anthropic has no
embeddings endpoint at all.

- **`ollama` (default)** - free, runs locally, no API key needed. Install
  [Ollama](https://ollama.com), make sure `ollama serve` is running, then pull
  the two models this project uses:
  ```bash
  ollama pull llama3.2:3b       # chat/extraction, tool-schema-capable
  ollama pull nomic-embed-text  # embeddings (Slice 3)
  ```
  `OLLAMA_BASE_URL`/`OLLAMA_CHAT_MODEL`/`OLLAMA_EMBED_MODEL` in `.env` let you
  point at different models or a remote Ollama instance.
- **`anthropic`** - real model quality, billed separately from a Claude.ai
  subscription. Set `LLM_PROVIDER=anthropic` and fill in `ANTHROPIC_API_KEY`.
  Good for an occasional high-fidelity demo run; `EMBEDDING_PROVIDER` stays
  `ollama` either way.

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

### Asking questions (routed - the main way to use this)

`POST /query` decides on its own whether a question needs semantic search
over document text, a SQL query over structured records, or both:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total invoice amount, and which vendor is it from?"}'
```

The response includes `route` (`"rag"`, `"sql"`, or `"both"`), the `answer`,
and - depending on the route - `citations` (document/page/snippet),
`sql`, and `rows`. Add `"document_id": "<uuid>"` to scope the RAG half to
one document. This is what the frontend's chat box calls.

### Asking questions directly (RAG or SQL only)

To force one path instead of letting `/query` decide, the two underlying
endpoints still work standalone.

RAG, once a PDF has finished processing (chunked + embedded in the
background):

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total amount due?"}'
```

Same `document_id` scoping as `/query`; omit it to search across everything
uploaded so far. Only PDFs are chunked for RAG - CSV/XLSX rows go through
structured extraction instead (see `document_extractions`), since tabular
data doesn't have a natural "page" to cite and text-to-SQL is a better fit.

Text-to-SQL, for aggregation across many documents - queries
`documents`/`document_extractions` directly rather than searching text:

```bash
curl -X POST http://localhost:8000/analytics/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the total invoice amount by currency, for completed extractions only?"}'
```

The response includes the generated `sql` (so you can see exactly what ran,
not just trust a black box), the result `rows`, and a plain-language
`explanation`. Only `SELECT` statements over `documents`/`document_extractions`
are allowed - see the guardrails note further down. A query that fails
that check comes back as `422` with the reason; a query that's valid SQL but
fails to execute (e.g. references a column that doesn't exist) comes back as
`400`.

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

### Trying it without any LLM backend running

Even with the free Ollama default, you may not want a model server running
just to click through the app (or you're offline). Seed the database with
the same files run through the *real* parsing, database, and validation
code, with only the LLM's response stubbed out:

```bash
cd backend
python scripts/seed_demo_data.py
```

This inserts real `documents`/`document_extractions` rows for every file in
`samples/`, so `GET /documents` and the extractions endpoint have real data
to look at immediately. It does **not** touch the network. Once Ollama (or
an Anthropic key) is set up, uploads through the API (or the Swagger UI)
will run the real thing.

## Running the tests

```bash
cd backend
pytest tests/ -v
```

This runs both the unit tests (parsers, validation, chunking, the SQL
guardrail, row-building — no network or database needed) and
`tests/integration/test_live_api.py`, which exercises the actual running
stack: upload → Celery pickup → a terminal status, `/ask` returning a
grounded answer with a citation, `/analytics/ask` returning real SQL results
(and rejecting an attempted write), `/query` dispatching to a shape
consistent with whichever route it picked, plus the list/get/404 endpoints.
The integration tests auto-skip if nothing is listening on
`http://localhost:8000`, so `pytest tests/` is safe to run whether or not
the server is up.

## Why this architecture

- **pgvector instead of a dedicated vector DB** — one less service to run,
  and it's genuinely fine at portfolio-project scale. Worth mentioning in
  interviews as a deliberate simplicity trade-off, not an oversight.
- **Celery for background processing** — large PDFs shouldn't block the
  upload request. This becomes the answer to "how does this handle a
  200-page contract?"
- **Explicit RAG-vs-SQL routing (Slice 5), done** — `/query` classifies each
  question and reuses the exact same `run_rag`/`run_analytics` functions the
  standalone endpoints call, rather than duplicating logic per route. A
  "both" question (numbers + explanation) runs both independently and makes
  a third LLM call to synthesize one answer — the differentiator vs. a
  typical "chat with your PDF" student project, and worth being able to
  explain in detail in an interview.
- **Two independent guardrail layers for text-to-SQL, not one** — an
  app-level `sqlglot` parse that rejects anything but a single `SELECT` over
  an explicit table allowlist, *and* a dedicated `doclarity_readonly`
  Postgres role that physically cannot write regardless of what SQL reaches
  it. The interesting failure mode for LLM-generated SQL isn't "the query is
  slightly wrong" — it's "the query does something you didn't ask for", so
  the second layer exists specifically to survive the first one having a bug.
