import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.extraction import DocumentExtraction, DocumentType, ExtractionStatus
from app.models.schemas import AnomalyResponse, AnomalyRow
from app.services.anomaly_detection import VendorBaseline, detect_anomalies
from app.services.llm_service import LLMService, LLMTransientError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["anomalies"])

# Same fixed-query rationale as app/api/dashboard.py: this is an app-authored
# stats query, not LLM-generated SQL, so it runs on the normal engine/session
# rather than Slice 4's sql_guard/doclarity_readonly pipeline. Scoped to one
# currency at a time for the same reason as revenue/vendor-breakdown - a
# vendor's mean/stddev across mixed currencies would be meaningless.
_INVOICE_FILTERS = (
    DocumentExtraction.status == ExtractionStatus.completed,
    DocumentExtraction.document_type == DocumentType.invoice,
    DocumentExtraction.total_amount.isnot(None),
)


@router.get("/anomalies", response_model=AnomalyResponse)
def anomalies(
    currency: str = Query(..., min_length=3, max_length=3),
    z_threshold: float = Query(3.0, ge=1.0, description="Flag invoices at least this many stddevs from their vendor's mean"),
    min_vendor_invoices: int = Query(3, ge=2, description="Vendors with fewer completed invoices than this have no reliable baseline"),
    db: Session = Depends(get_db),
):
    currency = currency.upper()

    stats_rows = (
        db.query(
            DocumentExtraction.vendor_name,
            func.avg(DocumentExtraction.total_amount).label("mean"),
            func.stddev_samp(DocumentExtraction.total_amount).label("stddev"),
            func.count().label("invoice_count"),
        )
        .filter(*_INVOICE_FILTERS, DocumentExtraction.currency == currency, DocumentExtraction.vendor_name.isnot(None))
        .group_by(DocumentExtraction.vendor_name)
        .having(func.count() >= min_vendor_invoices)
        .all()
    )
    baselines = {
        vendor: VendorBaseline(mean=float(mean), stddev=float(stddev or 0), invoice_count=count)
        for vendor, mean, stddev, count in stats_rows
    }
    if not baselines:
        return AnomalyResponse(
            currency=currency,
            anomalies=[],
            explanation="Not enough invoice history per vendor yet to establish a baseline.",
        )

    invoice_rows = (
        db.query(
            DocumentExtraction.id,
            DocumentExtraction.document_id,
            DocumentExtraction.vendor_name,
            DocumentExtraction.invoice_number,
            DocumentExtraction.invoice_date,
            DocumentExtraction.total_amount,
        )
        .filter(
            *_INVOICE_FILTERS,
            DocumentExtraction.currency == currency,
            DocumentExtraction.vendor_name.in_(baselines.keys()),
        )
        .all()
    )
    invoices = [
        {
            "extraction_id": extraction_id,
            "document_id": document_id,
            "vendor_name": vendor_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
        }
        for extraction_id, document_id, vendor_name, invoice_number, invoice_date, total_amount in invoice_rows
    ]

    flagged = detect_anomalies(invoices, baselines, z_threshold)

    explanation = "No anomalies found - every vendor's invoices fell within its own normal range."
    if flagged:
        try:
            explanation = LLMService().explain_anomalies(currency, flagged)
        except LLMTransientError as exc:
            raise HTTPException(status_code=503, detail=f"LLM backend unavailable: {exc}") from exc

    return AnomalyResponse(currency=currency, anomalies=[AnomalyRow(**row) for row in flagged], explanation=explanation)
