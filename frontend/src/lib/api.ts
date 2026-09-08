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

export { ApiError };
