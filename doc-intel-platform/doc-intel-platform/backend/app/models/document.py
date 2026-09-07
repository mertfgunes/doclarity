import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class ProcessingStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class Document(Base):
    """
    Slice 1 model: just enough to upload a file, store it, and list it.
    Later slices will add: document_chunks (embeddings), extracted_fields,
    transactions/invoices (structured data), processing_jobs (Celery tracking).
    """

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.uploaded, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
