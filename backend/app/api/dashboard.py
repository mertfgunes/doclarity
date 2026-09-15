from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models.document import Document
from app.models.extraction import DocumentExtraction, DocumentType, ExtractionStatus
from app.models.schemas import (
    CurrencyOption,
    DashboardSummary,
    RevenuePoint,
    StatusDistributionRow,
    VendorBreakdownRow,
)

router = APIRouter(prefix="/analytics/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])

# Fixed, app-authored queries for known dashboard widgets - not LLM-generated,
# so these run against the normal engine/session, not the sql_guard/
# doclarity_readonly pipeline built for Slice 4's free-form text-to-SQL.

# Revenue and vendor-breakdown are scoped to ONE currency at a time (a filter,
# not a chart dimension): summing/charting mixed currencies on one axis would
# imply they're directly comparable, which they're not without a conversion
# rate this app doesn't have. See docs/ROADMAP.md Slice 6.
_INVOICE_FILTERS = (
    DocumentExtraction.status == ExtractionStatus.completed,
    DocumentExtraction.document_type == DocumentType.invoice,
    DocumentExtraction.total_amount.isnot(None),
)


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    total_documents = db.query(func.count(Document.id)).scalar()
    total_extractions = db.query(func.count(DocumentExtraction.id)).scalar()
    needs_review_count = (
        db.query(func.count(DocumentExtraction.id))
        .filter(DocumentExtraction.status == ExtractionStatus.needs_review)
        .scalar()
    )
    return DashboardSummary(
        total_documents=total_documents,
        total_extractions=total_extractions,
        needs_review_count=needs_review_count,
    )


@router.get("/currencies", response_model=list[CurrencyOption])
def list_currencies(db: Session = Depends(get_db)):
    """Which currencies have completed invoice data, for the filter control -
    ordered by how much data backs each, so the frontend can default to the
    currency actually worth looking at.
    """
    rows = (
        db.query(DocumentExtraction.currency, func.count().label("invoice_count"))
        .filter(*_INVOICE_FILTERS, DocumentExtraction.currency.isnot(None))
        .group_by(DocumentExtraction.currency)
        .order_by(func.count().desc())
        .all()
    )
    return [CurrencyOption(currency=currency, invoice_count=count) for currency, count in rows]


@router.get("/revenue-over-time", response_model=list[RevenuePoint])
def revenue_over_time(
    currency: str = Query(..., min_length=3, max_length=3),
    interval: Literal["day", "week", "month"] = "month",
    db: Session = Depends(get_db),
):
    period = func.date_trunc(interval, DocumentExtraction.invoice_date).label("period")
    rows = (
        db.query(
            period,
            func.sum(DocumentExtraction.total_amount).label("total_amount"),
            func.count().label("invoice_count"),
        )
        .filter(*_INVOICE_FILTERS, DocumentExtraction.currency == currency.upper(), DocumentExtraction.invoice_date.isnot(None))
        .group_by(period)
        .order_by(period)
        .all()
    )
    return [
        RevenuePoint(period=period_start.date(), total_amount=total, invoice_count=count)
        for period_start, total, count in rows
    ]


@router.get("/vendor-breakdown", response_model=list[VendorBreakdownRow])
def vendor_breakdown(
    currency: str = Query(..., min_length=3, max_length=3),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            DocumentExtraction.vendor_name,
            func.sum(DocumentExtraction.total_amount).label("total_amount"),
            func.count().label("invoice_count"),
        )
        .filter(*_INVOICE_FILTERS, DocumentExtraction.currency == currency.upper(), DocumentExtraction.vendor_name.isnot(None))
        .group_by(DocumentExtraction.vendor_name)
        .order_by(func.sum(DocumentExtraction.total_amount).desc())
        .limit(limit)
        .all()
    )
    return [
        VendorBreakdownRow(vendor_name=vendor, total_amount=total, invoice_count=count)
        for vendor, total, count in rows
    ]


@router.get("/status-distribution", response_model=list[StatusDistributionRow])
def status_distribution(db: Session = Depends(get_db)):
    """Part-to-whole over ALL extraction rows regardless of currency or
    document_type - this is about extraction confidence/data quality, not
    financial amounts.
    """
    rows = db.query(DocumentExtraction.status, func.count().label("count")).group_by(DocumentExtraction.status).all()
    return [StatusDistributionRow(status=status, count=count) for status, count in rows]
