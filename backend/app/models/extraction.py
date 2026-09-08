import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Numeric, Integer, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.db import Base


class DocumentType(str, enum.Enum):
    invoice = "invoice"
    contract = "contract"
    unknown = "unknown"


class ExtractionStatus(str, enum.Enum):
    completed = "completed"
    needs_review = "needs_review"
    failed = "failed"


class DocumentExtraction(Base):
    """
    One row per extracted "record" for a document. A PDF invoice or contract
    produces exactly one row. A CSV/XLSX produces one row per data row, since
    each row maps to its own vendor/invoice/transaction.

    Canonical columns are invoice-shaped (the structured type Slice 4's
    text-to-SQL analytics will query most). Contract-specific and anything
    that doesn't fit the canonical columns lives in raw_extraction.
    """

    __tablename__ = "document_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)

    document_type = Column(Enum(DocumentType), default=DocumentType.unknown, nullable=False)
    status = Column(Enum(ExtractionStatus), nullable=False)

    vendor_name = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    invoice_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    total_amount = Column(Numeric(14, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    payment_terms_days = Column(Integer, nullable=True)

    line_items = Column(JSONB, nullable=True)
    raw_extraction = Column(JSONB, nullable=True)
    confidence_flags = Column(JSONB, nullable=False, default=list)

    error_message = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
