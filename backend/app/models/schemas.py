import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.models.document import ProcessingStatus
from app.models.extraction import DocumentType, ExtractionStatus
from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


class AnomalyRow(BaseModel):
    extraction_id: uuid.UUID
    document_id: uuid.UUID
    vendor_name: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    total_amount: Decimal
    vendor_mean: Decimal
    vendor_stddev: Decimal
    vendor_invoice_count: int
    z_score: float
    ratio: float


class AnomalyResponse(BaseModel):
    currency: str
    anomalies: list[AnomalyRow]
    explanation: str


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
