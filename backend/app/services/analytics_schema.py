SCHEMA_DESCRIPTION = """
You can query the following read-only PostgreSQL tables:

documents
  id            uuid, primary key
  filename      text
  content_type  text (MIME type, e.g. "application/pdf", "text/csv")
  status        text enum: uploaded | processing | processed | failed
  uploaded_at   timestamp

document_extractions
  id                    uuid, primary key
  document_id           uuid, foreign key -> documents.id
  document_type         text enum: invoice | contract | unknown
  status                text enum: completed | needs_review | failed
  vendor_name           text, nullable
  invoice_number        text, nullable
  invoice_date          date, nullable
  due_date              date, nullable
  total_amount          numeric(14,2), nullable
  currency              text, ISO 4217 code (e.g. USD, EUR), nullable
  payment_terms_days    integer, nullable
  line_items            jsonb, nullable - array of {description, quantity, unit_price, amount}
  confidence_flags      jsonb, array of strings - empty if the row passed validation
  created_at            timestamp

One document_extractions row = one invoice/contract (from a PDF) or one row
of a CSV/XLSX file. A row with status = 'needs_review' has a low-confidence
extraction (see confidence_flags) - exclude those from totals/sums unless
the question is explicitly about data quality or review status.
""".strip()
