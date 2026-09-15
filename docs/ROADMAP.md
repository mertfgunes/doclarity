# Roadmap — build in vertical slices, not layers

Each slice should be runnable end-to-end and demoable before moving to the
next one. Don't start Slice N+1 until Slice N works.

## Slice 1 — Upload → store → list  [done]
- [x] `Document` model, upload endpoint, list endpoint
- [x] Basic Next.js page: drag-and-drop upload + document list table

## Slice 2 — Extract → structure  [scaffolded]
- [x] Celery worker triggered on upload (`extract_document` task, retry with
      backoff on transient LLM errors, permanent failures fail fast)
- [x] PDF text + table extraction (pdfplumber), CSV/XLSX parsing (pandas) —
      both deterministic, no LLM
- [x] `document_type` (invoice / contract / unknown) decided per document by
      the LLM, with type-specific extraction fields — not one flexible schema
- [x] `document_extractions` table: canonical invoice-shaped columns
      (vendor_name, invoice_number, invoice_date, due_date, total_amount,
      currency, payment_terms_days) + `line_items`/`raw_extraction` JSONB +
      `confidence_flags`. One row per PDF invoice/contract; one row per CSV
      row (CSV columns are semantically mapped to the canonical schema by a
      single LLM call, then applied deterministically per row)
- [x] Structuring via forced tool-use (JSON-schema enforced), not free-text
      parsing of the LLM response
- [x] Validation layer: line items vs. total, plausible dates, real ISO 4217
      currency codes → flags low-confidence rows as `needs_review` rather
      than trusting the extraction blindly
- [x] Verified end-to-end against a live Postgres + Redis + Celery worker:
      `tests/integration/test_live_api.py` uploads real sample files through
      the real API and confirms Celery picks them up and reaches a terminal
      status (auto-skips if the server isn't running). Ran without a real
      `ANTHROPIC_API_KEY`, so the terminal status observed is `failed` (401
      from Anthropic, handled cleanly - no retry storm); `scripts/seed_demo_data.py`
      exercises the same parsing/validation/DB path with the LLM call stubbed,
      to see real `processed` rows without API spend. Still open: one true
      run with a real key, to confirm the actual extraction prompt behaves
      as expected end to end.

## Slice 3 — Embed → RAG Q&A with citations  [done]
- [x] `document_chunks` table (raw text chunks + pgvector embedding column) —
      PDFs only for now; CSV/XLSX rows are already structured data with no
      natural "page" to cite, and tabular Q&A is Slice 4's job (text-to-SQL),
      not semantic search
- [x] Chunking keeps page numbers per chunk (word-based packing, ~1000 chars,
      150-char overlap, never spans pages) for citations
- [x] Generate embeddings for each chunk (`nomic-embed-text` via Ollama,
      768-dim, stored in the pgvector column) - own Celery task
      (`embed_document`), independent of Slice 2's `extract_document` so
      neither blocks or races the other on `Document.status`
- [x] `/ask` endpoint: embeds the question, vector search
      (`cosine_distance`) over `document_chunks` (optionally scoped to one
      `document_id`), passes top-5 chunks + question to the LLM, returns
      answer + citations (filename/page/snippet) - citations are exactly
      the retrieved chunks, not model-reported, so they can't be wrong
- [x] Frontend: `AskBox` chat component on the main page, question in,
      answer + citations out
- [x] **LLM backend decision (the other open item from last session):**
      `LLMService` now supports Ollama (free/local, default) alongside
      Anthropic, via separate `LLM_PROVIDER`/`EMBEDDING_PROVIDER` settings -
      Anthropic has no embeddings API at all, so Slice 3 needed a second
      provider regardless of what extraction used. See README "Choosing an
      LLM backend".
- [x] Verified for real, not just unit-tested: live Postgres/Redis/Celery/
      Ollama stack, a real PDF uploaded through the actual API, both Celery
      tasks completing, `document_chunks` rows landing with real 768-dim
      embeddings, `/ask` returning a correct grounded answer with an
      accurate citation - and a Playwright-driven Edge browser screenshot of
      the working chat box against the live backend, console-error-free.
      Notably, RAG answered a question (`total_amount`) that Slice 2's
      structured extraction had missed - the raw-text retrieval path doesn't
      depend on the smaller local model's forced-JSON output being complete.

## Slice 4 — Text-to-SQL analytics
- [ ] `/analytics/ask` endpoint: natural language → SQL generation → execute
      against `invoices`/`transactions` → return results + LLM explanation
- [ ] Guardrails: read-only DB role for the LLM-generated queries, query
      allowlist/validation before execution

## Slice 5 — Route between RAG and SQL (the differentiator)
- [ ] Lightweight intent classifier (rule-based or LLM call) deciding:
      RAG-only / SQL-only / both
- [ ] Handle "why did revenue drop" style questions that need both

## Slice 6 — Analytics dashboard
- [ ] Aggregation endpoints (revenue over time, customer breakdown,
      invoice status distribution)
- [ ] Frontend charts + filters (date, customer, status)

## Slice 7 — Anomaly detection
- [ ] Per-customer historical baseline (mean/stddev of invoice amounts)
- [ ] Flag + explain outliers ("35x higher than this customer's average")

## Slice 8 — Production engineering
- [ ] Auth (JWT), role-based access
- [ ] Alembic migrations replacing `create_all`
- [ ] Unit + integration tests, a small RAG eval set (does retrieval surface
      the right chunk for known questions?)
- [ ] CI (GitHub Actions): lint + test on push
- [ ] Deploy: frontend → Vercel, backend → a cloud host, Postgres → managed

## Slice 9 — Ship it
- [ ] Record a 2–3 min demo video
- [ ] README architecture-decisions section (why pgvector, why the routing
      approach, what you'd do differently at scale)
