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

## Slice 3 — Embed → RAG Q&A with citations
- [ ] `document_chunks` table (raw text chunks + pgvector embedding column) —
      not needed until RAG, so it wasn't built in Slice 2
- [ ] Generate embeddings for each chunk (store in pgvector column)
- [ ] `/ask` endpoint: embed the question, vector search, pass top chunks +
      question to Claude, return answer + source doc/page
- [ ] Frontend: simple chat box showing answer + citation links

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
