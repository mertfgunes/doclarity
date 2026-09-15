import { clearToken, getToken } from "@/lib/auth";

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

function authHeaders(): HeadersInit {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Used for every protected route. A 401 means the token is missing/expired/
// invalid - there's no refresh flow, so the simplest correct behavior is to
// drop it and send the user back to log in.
async function unwrap<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    clearToken();
    // A plain module has no router context, and a full reload is actually
    // desirable here anyway (no refresh-token flow - drop all client state).
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    if (typeof window !== "undefined") window.location.href = "/login";
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail ?? response.statusText, response.status);
  }
  return response.json();
}

// Used only for /auth/login and /auth/register - a 401/400 there is a normal
// "wrong password" / "email taken" result to show on the form, not a reason
// to redirect away from the page the user is already on.
async function unwrapAuth<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail ?? response.statusText, response.status);
  }
  return response.json();
}

export interface AuthUser {
  id: string;
  email: string;
  role: "admin" | "viewer";
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export function registerUser(email: string, password: string): Promise<AuthUser> {
  return fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  }).then(unwrapAuth<AuthUser>);
}

export function loginUser(email: string, password: string): Promise<Token> {
  const body = new URLSearchParams({ username: email, password });
  return fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  }).then(unwrapAuth<Token>);
}

export function listDocuments(): Promise<Document[]> {
  return fetch(`${API_URL}/documents`, { headers: authHeaders() }).then(unwrap<Document[]>);
}

export function getDocumentExtractions(documentId: string): Promise<DocumentExtraction[]> {
  return fetch(`${API_URL}/documents/${documentId}/extractions`, { headers: authHeaders() }).then(
    unwrap<DocumentExtraction[]>,
  );
}

export function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return fetch(`${API_URL}/documents/upload`, {
    method: "POST",
    headers: authHeaders(),
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
    headers: { "Content-Type": "application/json", ...authHeaders() },
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
  return fetch(`${API_URL}/analytics/dashboard/summary`, { headers: authHeaders() }).then(unwrap<DashboardSummary>);
}

export function getDashboardCurrencies(): Promise<CurrencyOption[]> {
  return fetch(`${API_URL}/analytics/dashboard/currencies`, { headers: authHeaders() }).then(
    unwrap<CurrencyOption[]>,
  );
}

export function getRevenueOverTime(currency: string, interval: "day" | "week" | "month" = "month"): Promise<RevenuePoint[]> {
  const params = new URLSearchParams({ currency, interval });
  return fetch(`${API_URL}/analytics/dashboard/revenue-over-time?${params}`, { headers: authHeaders() }).then(
    unwrap<RevenuePoint[]>,
  );
}

export function getVendorBreakdown(currency: string, limit = 10): Promise<VendorBreakdownRow[]> {
  const params = new URLSearchParams({ currency, limit: String(limit) });
  return fetch(`${API_URL}/analytics/dashboard/vendor-breakdown?${params}`, { headers: authHeaders() }).then(
    unwrap<VendorBreakdownRow[]>,
  );
}

export function getStatusDistribution(): Promise<StatusDistributionRow[]> {
  return fetch(`${API_URL}/analytics/dashboard/status-distribution`, { headers: authHeaders() }).then(
    unwrap<StatusDistributionRow[]>,
  );
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
  return fetch(`${API_URL}/analytics/anomalies?${params}`, { headers: authHeaders() }).then(unwrap<AnomalyResponse>);
}

export { ApiError };
