# Roadmap — build in vertical slices, not layers

Each slice should be runnable end-to-end and demoable before moving to the
next one. Don't start Slice N+1 until Slice N works.

## Slice 1 — Upload → store → list  [scaffolded]
- [x] `Document` model, upload endpoint, list endpoint
- [ ] Basic Next.js page: drag-and-drop upload + document list table

## Slice 2 — Extract → structure
- [ ] Celery worker triggered on upload
- [ ] PDF text extraction (pypdf), CSV/XLSX parsing (pandas)
- [ ] `document_chunks` table (raw text chunks, for embedding later)
- [ ] For structured docs (invoices): an extraction prompt to Claude that
      returns JSON (customer, amount, currency, due date) → save to an
      `invoices`/`transactions` table

## Slice 3 — Embed → RAG Q&A with citations
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
