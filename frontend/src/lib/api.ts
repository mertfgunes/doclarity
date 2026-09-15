const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ProcessingStatus = "uploaded" | "processing" | "processed" | "failed";
export type DocumentType = "invoice" | "contract" | "unknown";
export type ExtractionStatus = "completed" | "needs_review" | "failed";

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  status: ProcessingStatus;
  uploaded_at: string;
}

export interface LineItem {
  description: string;
  quantity: number | null;
  unit_price: number | null;
  amount: number | null;
}

export interface DocumentExtraction {
  id: string;
  document_id: string;
  document_type: DocumentType;
  status: ExtractionStatus;
  vendor_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  total_amount: string | null;
  currency: string | null;
  payment_terms_days: number | null;
  line_items: LineItem[] | null;
  raw_extraction: Record<string, unknown> | null;
  confidence_flags: string[];
  error_message: string | null;
  created_at: string;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function unwrap<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail ?? response.statusText, response.status);
  }
  return response.json();
}

export function listDocuments(): Promise<Document[]> {
  return fetch(`${API_URL}/documents`).then(unwrap<Document[]>);
}

export function getDocumentExtractions(documentId: string): Promise<DocumentExtraction[]> {
  return fetch(`${API_URL}/documents/${documentId}/extractions`).then(unwrap<DocumentExtraction[]>);
}

export function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${API_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  }).then(unwrap<Document>);
}

export interface Citation {
  document_id: string;
  filename: string;
  page_number: number | null;
  snippet: string;
}

export type QueryRoute = "rag" | "sql" | "both";

export interface QueryResponse {
  route: QueryRoute;
  answer: string;
  citations: Citation[];
  sql: string | null;
  rows: Record<string, unknown>[] | null;
}

// Slice 5: a single entry point that decides for itself whether a question
// needs semantic search over document text, a SQL query over structured
// records, or both - see docs/ROADMAP.md Slice 5.
export function askQuestion(question: string, documentId?: string): Promise<QueryResponse> {
  return fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_id: documentId ?? null }),
  }).then(unwrap<QueryResponse>);
}

export interface DashboardSummary {
  total_documents: number;
  total_extractions: number;
  needs_review_count: number;
}

export interface CurrencyOption {
  currency: string;
  invoice_count: number;
}

export interface RevenuePoint {
  period: string;
  total_amount: string;
  invoice_count: number;
}

export interface VendorBreakdownRow {
  vendor_name: string;
  total_amount: string;
  invoice_count: number;
}

export interface StatusDistributionRow {
  status: ExtractionStatus;
  count: number;
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return fetch(`${API_URL}/analytics/dashboard/summary`).then(unwrap<DashboardSummary>);
}

export function getDashboardCurrencies(): Promise<CurrencyOption[]> {
  return fetch(`${API_URL}/analytics/dashboard/currencies`).then(unwrap<CurrencyOption[]>);
}

export function getRevenueOverTime(currency: string, interval: "day" | "week" | "month" = "month"): Promise<RevenuePoint[]> {
  const params = new URLSearchParams({ currency, interval });
  return fetch(`${API_URL}/analytics/dashboard/revenue-over-time?${params}`).then(unwrap<RevenuePoint[]>);
}

export function getVendorBreakdown(currency: string, limit = 10): Promise<VendorBreakdownRow[]> {
  const params = new URLSearchParams({ currency, limit: String(limit) });
  return fetch(`${API_URL}/analytics/dashboard/vendor-breakdown?${params}`).then(unwrap<VendorBreakdownRow[]>);
}

export function getStatusDistribution(): Promise<StatusDistributionRow[]> {
  return fetch(`${API_URL}/analytics/dashboard/status-distribution`).then(unwrap<StatusDistributionRow[]>);
}

export interface AnomalyRow {
  extraction_id: string;
  document_id: string;
  vendor_name: string;
  invoice_number: string | null;
  invoice_date: string | null;
  total_amount: string;
  vendor_mean: string;
  vendor_stddev: string;
  vendor_invoice_count: number;
  z_score: number;
  ratio: number;
}

export interface AnomalyResponse {
  currency: string;
  anomalies: AnomalyRow[];
  explanation: string;
}

// Slice 7: per-vendor mean/stddev baseline, flagging invoices that deviate
// from their own vendor's history rather than from an absolute threshold -
// see docs/ROADMAP.md Slice 7.
export function getAnomalies(currency: string): Promise<AnomalyResponse> {
  const params = new URLSearchParams({ currency });
  return fetch(`${API_URL}/analytics/anomalies?${params}`).then(unwrap<AnomalyResponse>);
}

export { ApiError };
