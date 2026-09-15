import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel

from app.models.document import ProcessingStatus
from app.models.extraction import DocumentType, ExtractionStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    status: ProcessingStatus
    uploaded_at: datetime

    class Config:
        from_attributes = True


class Citation(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_number: Optional[int] = None
    snippet: str


class AskRequest(BaseModel):
    question: str
    document_id: Optional[uuid.UUID] = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


class AnalyticsAskRequest(BaseModel):
    question: str


class AnalyticsAskResponse(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    explanation: str


class QueryRequest(BaseModel):
    question: str
    document_id: Optional[uuid.UUID] = None


class QueryResponse(BaseModel):
    route: Literal["rag", "sql", "both"]
    answer: str
    citations: list[Citation] = []
    sql: Optional[str] = None
    rows: Optional[list[dict[str, Any]]] = None


class CurrencyOption(BaseModel):
    currency: str
    invoice_count: int


class RevenuePoint(BaseModel):
    period: date
    total_amount: Decimal
    invoice_count: int


class VendorBreakdownRow(BaseModel):
    vendor_name: str
    total_amount: Decimal
    invoice_count: int


class StatusDistributionRow(BaseModel):
    status: ExtractionStatus
    count: int


class DashboardSummary(BaseModel):
    total_documents: int
    total_extractions: int
    needs_review_count: int


class DocumentExtractionOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_type: DocumentType
    status: ExtractionStatus

    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    payment_terms_days: Optional[int] = None

    line_items: Optional[list[dict[str, Any]]] = None
    raw_extraction: Optional[dict[str, Any]] = None
    confidence_flags: list[str] = []

    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
