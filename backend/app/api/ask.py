import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.schemas import AskRequest, AskResponse, Citation
from app.services.llm_service import LLMService, LLMTransientError

router = APIRouter(tags=["ask"])

TOP_K = 5
SNIPPET_MAX_CHARS = 300


def run_rag(question: str, document_id: uuid.UUID | None, db: Session, llm: LLMService) -> AskResponse:
    """Semantic search over document_chunks + a grounded answer with citations."""
    if not question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    if document_id is not None and not db.query(Document).filter(Document.id == document_id).first():
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        query_embedding = llm.embed([question])[0]
    except LLMTransientError as exc:
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc

    query = db.query(DocumentChunk, Document.filename).join(Document, DocumentChunk.document_id == Document.id)
    if document_id is not None:
        query = query.filter(DocumentChunk.document_id == document_id)
    matches = query.order_by(DocumentChunk.embedding.cosine_distance(query_embedding)).limit(TOP_K).all()

    if not matches:
        return AskResponse(
            answer="I don't have any indexed document content to answer from yet - upload a PDF and wait for it to finish processing.",
            citations=[],
        )

    context = "\n\n".join(
        f"[Source {i + 1}: {filename}, page {chunk.page_number}]\n{chunk.text}"
        for i, (chunk, filename) in enumerate(matches)
    )

    try:
        answer = llm.answer_question(question, context)
    except LLMTransientError as exc:
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc

    citations = [
        Citation(
            document_id=chunk.document_id,
            filename=filename,
            page_number=chunk.page_number,
            snippet=chunk.text[:SNIPPET_MAX_CHARS],
        )
        for chunk, filename in matches
    ]
    return AskResponse(answer=answer, citations=citations)


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, db: Session = Depends(get_db)):
    return run_rag(request.question, request.document_id, db, LLMService())
