import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.analytics import run_analytics
from app.api.ask import run_rag
from app.core.db import get_db
from app.models.schemas import QueryRequest, QueryResponse
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest, db: Session = Depends(get_db)):
    """The Slice 5 differentiator: decide whether a question needs semantic
    search over document text (RAG), aggregation over structured records
    (SQL), or both - then answer it accordingly.

    "Both" questions (e.g. "why did revenue drop") run RAG and SQL
    independently and synthesize one answer from both findings. Either half
    failing (guard rejection, bad generated SQL, LLM backend down) aborts
    the whole request rather than silently returning a partial answer -
    for a "why" question, an answer missing either the number or the
    explanation isn't the answer that was asked for.
    """
    llm = LLMService()
    route = llm.classify_route(request.question)
    logger.info("query: routed %r -> %s", request.question, route)

    if route == "sql":
        analytics = run_analytics(request.question, llm)
        return QueryResponse(route="sql", answer=analytics.explanation, sql=analytics.sql, rows=analytics.rows)

    if route == "rag":
        rag = run_rag(request.question, request.document_id, db, llm)
        return QueryResponse(route="rag", answer=rag.answer, citations=rag.citations)

    rag = run_rag(request.question, request.document_id, db, llm)
    analytics = run_analytics(request.question, llm)
    combined = llm.synthesize_answer(request.question, rag.answer, analytics.explanation)
    return QueryResponse(
        route="both",
        answer=combined,
        citations=rag.citations,
        sql=analytics.sql,
        rows=analytics.rows,
    )
