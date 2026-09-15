import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sa_text
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import get_current_user
from app.core.db import analytics_engine
from app.models.schemas import AnalyticsAskRequest, AnalyticsAskResponse
from app.services.analytics_schema import SCHEMA_DESCRIPTION
from app.services.llm_service import LLMService, LLMTransientError
from app.services.sql_guard import SQLGuardError, validate_select_only

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])

MAX_RESULT_ROWS = 500
# Keep the explanation prompt small regardless of how many rows came back.
EXPLAIN_ROW_SAMPLE = 50


def run_analytics(question: str, llm: LLMService) -> AnalyticsAskResponse:
    """Text-to-SQL: generate -> validate -> execute -> explain.

    Shared by the standalone /analytics/ask endpoint and /query's routed
    "sql"/"both" paths.
    """
    if not question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    try:
        sql = llm.generate_sql(question, SCHEMA_DESCRIPTION)
    except LLMTransientError as exc:
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc
    sql = sql.strip().rstrip(";").strip()

    try:
        validate_select_only(sql)
    except SQLGuardError as exc:
        logger.warning("analytics: generated SQL rejected by guard: %s | sql=%s", exc, sql)
        raise HTTPException(status_code=422, detail=f"Generated query failed a safety check: {exc}") from exc

    try:
        rows, truncated = _execute_readonly(sql)
    except SQLAlchemyError as exc:
        logger.warning("analytics: generated SQL failed to execute: %s | sql=%s", exc, sql)
        raise HTTPException(status_code=400, detail=f"Generated query failed to execute: {exc}") from exc

    try:
        explanation = llm.explain_query_results(question, sql, rows[:EXPLAIN_ROW_SAMPLE])
    except LLMTransientError as exc:
        raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc

    return AnalyticsAskResponse(sql=sql, rows=rows, row_count=len(rows), truncated=truncated, explanation=explanation)


@router.post("/ask", response_model=AnalyticsAskResponse)
def ask_analytics(request: AnalyticsAskRequest):
    return run_analytics(request.question, LLMService())


def _execute_readonly(sql: str, limit: int = MAX_RESULT_ROWS) -> tuple[list[dict], bool]:
    """Run `sql` (already validated as a single read-only SELECT) against the
    least-privilege analytics role, with a hard row cap applied regardless of
    whether the generated query included its own LIMIT.
    """
    wrapped = f"SELECT * FROM ({sql}) AS analytics_subquery LIMIT :limit"
    with analytics_engine.connect() as conn:
        result = conn.execute(sa_text(wrapped), {"limit": limit + 1})
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]

    truncated = len(rows) > limit
    return rows[:limit], truncated
