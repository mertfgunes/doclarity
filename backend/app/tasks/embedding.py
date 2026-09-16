import logging

from celery.exceptions import MaxRetriesExceededError

from app.core import storage
from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.services.chunking import chunk_pdf_pages
from app.services.llm_service import LLMService, LLMTransientError
from app.services.pdf_parser import extract_pdf_pages

logger = logging.getLogger(__name__)

PDF_CONTENT_TYPE = "application/pdf"

# Batch embed calls so one large PDF doesn't send hundreds of tiny requests.
EMBED_BATCH_SIZE = 32


def _build_chunk_rows(document) -> list[DocumentChunk]:
    llm = LLMService()
    with storage.open_local(document.storage_path) as path:
        pages = extract_pdf_pages(path)
    chunks = chunk_pdf_pages(pages)

    rows = []
    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + EMBED_BATCH_SIZE]
        embeddings = llm.embed([chunk.text for chunk in batch])
        for offset, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            rows.append(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=batch_start + offset,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    embedding=embedding,
                )
            )
    return rows


@celery_app.task(bind=True, max_retries=5)
def embed_document(self, document_id: str):
    """Chunk + embed a document for RAG retrieval (Slice 3).

    Independent of extract_document (Slice 2) - it doesn't touch
    Document.status, since that field tracks the extraction pipeline. A
    document is searchable for RAG once its document_chunks rows exist.
    """
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            logger.warning("embed_document: document %s not found", document_id)
            return

        if document.content_type != PDF_CONTENT_TYPE:
            return

        try:
            rows = _build_chunk_rows(document)
        except LLMTransientError as exc:
            logger.warning("embed_document: transient error for %s, retrying: %s", document_id, exc)
            try:
                raise self.retry(exc=exc, countdown=min(2**self.request.retries * 10, 600))
            except MaxRetriesExceededError:
                logger.error("embed_document: giving up on %s after retries: %s", document_id, exc)
                return
        except Exception as exc:  # noqa: BLE001 -- permanent failure, no retry
            logger.error("embed_document: permanent failure for %s: %s", document_id, exc)
            return

        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        db.add_all(rows)
        db.commit()
    finally:
        db.close()
