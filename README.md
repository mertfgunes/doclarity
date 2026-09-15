# Doclarity

AI analytics & document intelligence platform. Upload invoices, contracts,
and financial docs → extract structured data → ask
questions in natural language (RAG for document Q&A, text-to-SQL for
analytics) → get dashboards and anomaly alerts, with citations back to source
documents.

## Status

**Slice 8 (this commit): Production engineering.** JWT auth + role-based
access (`admin` can upload, `viewer` is read-only - everything else needs
either), Alembic migrations replacing `create_all`, a small RAG eval set,
and CI (lint + test on push). See "Auth" and "Running the tests" below.
Deploy is intentionally not part of this slice - see `docs/ROADMAP.md`.

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
   alembic upgrade head   # creates all tables - see "Migrations" below if you
                           # already had tables from before Slice 8
   uvicorn app.main:app --reload
   ```
3. Celery worker (separate terminal, same venv — Windows needs the `solo`
   pool since the default `prefork` pool doesn't work there):
   ```bash
   cd backend
   celery -A app.core.celery_app worker --loglevel=info --pool=solo
   ```
4. Check the API's alive: `curl http://localhost:8000/health`

## Migrations

Schema is Alembic-owned (Slice 8) - `create_all` is gone from `app/main.py`.

- **Fresh DB**: `alembic upgrade head` creates everything (`documents`,
  `document_extractions`, `document_chunks`, `users`).
- **A DB that already has the first three tables** (i.e. you were running
  this before Slice 8): `alembic stamp 0001` marks that baseline as already
  applied without re-running its DDL, then `alembic upgrade head` actually
  creates the new `users` table.

## Auth

Every route except `/health`, `/auth/register`, and `/auth/login` requires
a JWT. Two roles: `admin` (can upload documents, plus everything a viewer
can) and `viewer` (read-only - ask/query/dashboard, not upload).

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "a-real-password"}'
# always creates a viewer - registration can never mint an admin

curl -X POST http://localhost:8000/auth/login \
  -d "username=you@example.com&password=a-real-password"
# -> {"access_token": "...", "token_type": "bearer"}
```

Send the token back as `Authorization: Bearer <access_token>` on every
other request. The Swagger UI at `/docs` has an "Authorize" button that
does this for you after you log in there.

**Getting an admin account**: there's no public "become admin" endpoint by
design - run `python scripts/create_admin.py <email> <password>` (from
`backend/`, same convention as `scripts/seed_demo_data.py`) to create or
promote one directly against the DB.

The frontend has minimal `/login` and `/register` pages that store the
token in `localStorage` and attach it to every API call automatically.

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
generates automatically: **http://localhost:8000/docs** - log in there via
"Authorize" (see "Auth" above) and every endpoint can be run with a "Try it
out" button, no curl needed. The examples below assume `$TOKEN` holds an
admin token (`curl`'s `-H "Authorization: Bearer $TOKEN"`), since uploading
needs one; a viewer token works for everything except upload.

### Uploading a document

```bash
curl -F "file=@samples/sample_invoice.pdf" -H "Authorization: Bearer $TOKEN" http://localhost:8000/documents/upload
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/documents
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/documents/{id}/extractions
```

### Asking questions (routed - the main way to use this)

`POST /query` decides on its own whether a question needs semantic search
over document text, a SQL query over structured records, or both:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
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
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
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
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
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

### Using the dashboard

Open **http://localhost:3000/dashboard** (linked from the main page via
"Dashboard →") for an aggregate view across everything uploaded: document/
extraction counts, a needs-review count, an extraction status breakdown,
and - scoped to one currency at a time via the filter control - revenue
over time and a top-vendors-by-amount breakdown. The currency scoping is
deliberate: summing amounts across currencies on one shared axis would
imply a conversion rate this app doesn't have, so revenue/vendor data is
filtered rather than combined.

The underlying endpoints (`GET /analytics/dashboard/summary`,
`/currencies`, `/revenue-over-time?currency=EUR`,
`/vendor-breakdown?currency=EUR`, `/status-distribution`) are fixed,
app-authored SQL, unrelated to the text-to-SQL guardrails described below -
those only apply to the LLM-generated free-form queries from
`/analytics/ask`.

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
guardrail, auth hashing/JWT, row-building — no network or database needed)
and the live integration tests: `test_live_api.py` (upload → Celery pickup
→ a terminal status, `/ask` returning a grounded answer with a citation,
`/analytics/ask` returning real SQL results and rejecting an attempted
write, `/query` dispatching to a shape consistent with whichever route it
picked, auth - register/login/401/403 - plus the list/get/404 endpoints)
and `test_rag_eval.py` (a small eval set - does `/ask` cite the right
source document for a handful of known questions?). Both auto-skip if
nothing is listening on `http://localhost:8000`, so `pytest tests/` is safe
to run whether or not the server is up.

CI (`.github/workflows/ci.yml`) runs `ruff check .` + `pytest tests/ -v` on
the backend and `npm run lint` on the frontend, on every push - no service
containers needed, since the integration tests above already auto-skip
without a live server.

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
- **Registration can never mint an admin** — `POST /auth/register` always
  creates a viewer; the only way to get an admin account is
  `scripts/create_admin.py`, a direct DB write with no HTTP surface at all.
  A "give yourself any role you like" field on a public endpoint is exactly
  the kind of privilege-escalation bug worth designing out rather than
  trusting validation to catch.
