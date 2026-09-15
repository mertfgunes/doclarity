import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base

# Fixed to nomic-embed-text's output size. pgvector requires a column's
# dimension to be fixed at table-creation time - changing EMBEDDING_PROVIDER
# to a model with a different dimension would need this column (and the
# table) recreated. Acceptable simplicity trade-off at this project's scale,
# same reasoning as pgvector itself (see README "Why this architecture").
EMBEDDING_DIM = 768


class DocumentChunk(Base):
    """
    A slice of a document's raw text plus its embedding, for RAG retrieval.

    One row per chunk. Only PDFs are chunked for now - CSV/XLSX rows are
    already structured data (see document_extractions) with no natural
    "page" to cite, and structured tabular Q&A is Slice 4's job (text-to-SQL),
    not semantic search.
    """

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)

    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    text = Column(String, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
