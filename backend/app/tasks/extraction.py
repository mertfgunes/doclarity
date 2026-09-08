import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import anthropic
from celery.exceptions import MaxRetriesExceededError
from dateutil import parser as dateutil_parser

from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.models.extraction import DocumentExtraction, DocumentType, ExtractionStatus
from app.services.csv_parser import parse_tabular_file
from app.services.llm_service import CANONICAL_INVOICE_FIELDS, LLMService
from app.services.pdf_parser import extract_pdf_text
from app.services.validation import validate_extraction

logger = logging.getLogger(__name__)

PDF_CONTENT_TYPE = "application/pdf"
TABULAR_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Transient failures worth retrying; anything else (bad file, missing tool
# call, unparseable data) is a permanent failure and retrying won't help.
TRANSIENT_LLM_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


def _parse_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return dateutil_parser.parse(value).date()
    except (ValueError, OverflowError):
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _make_row(
    document_id,
    document_type: DocumentType,
    *,
    vendor_name: str | None = None,
    invoice_number: str | None = None,
    invoice_date: date | None = None,
    due_date: date | None = None,
    total_amount: Decimal | None = None,
    currency: str | None = None,
    payment_terms_days: int | None = None,
    line_items: list[dict] | None = None,
    raw_extraction: dict | None = None,
    error_message: str | None = None,
) -> DocumentExtraction:
    if error_message:
        flags: list[str] = []
        status = ExtractionStatus.failed
    else:
        flags = validate_extraction(
            total_amount, currency, invoice_date, due_date, line_items, document_type=document_type.value
        )
        status = ExtractionStatus.needs_review if flags else ExtractionStatus.completed

    return DocumentExtraction(
        document_id=document_id,
        document_type=document_type,
        status=status,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        total_amount=total_amount,
        currency=currency.upper() if currency else None,
        payment_terms_days=payment_terms_days,
        line_items=line_items,
        raw_extraction=raw_extraction,
        confidence_flags=flags,
        error_message=error_message,
    )


def _rows_from_pdf(document, llm: LLMService) -> list[DocumentExtraction]:
    text = extract_pdf_text(document.storage_path)
    result = llm.extract_document_fields(text)
    doc_type = DocumentType(result.get("document_type", "unknown"))

    if doc_type == DocumentType.invoice:
        invoice = result.get("invoice") or {}
        row = _make_row(
            document.id,
            DocumentType.invoice,
            vendor_name=invoice.get("vendor_name"),
            invoice_number=invoice.get("invoice_number"),
            invoice_date=_parse_date(invoice.get("invoice_date")),
            due_date=_parse_date(invoice.get("due_date")),
            total_amount=_parse_decimal(invoice.get("total_amount")),
            currency=invoice.get("currency"),
            payment_terms_days=_parse_int(invoice.get("payment_terms_days")),
            line_items=invoice.get("line_items"),
            raw_extraction=result,
        )
    elif doc_type == DocumentType.contract:
        row = _make_row(document.id, DocumentType.contract, raw_extraction=result)
    else:
        row = _make_row(document.id, DocumentType.unknown, raw_extraction=result)

    return [row]


def _rows_from_tabular(document, llm: LLMService) -> list[DocumentExtraction]:
    parsed = parse_tabular_file(document.storage_path, document.content_type)
    mapping = llm.map_csv_columns(parsed.columns, parsed.sample_rows)
    mapping = {field: col for field, col in mapping.items() if field in CANONICAL_INVOICE_FIELDS}

    rows = []
    for source_row in parsed.rows:
        try:
            mapped = {field: source_row.get(col) for field, col in mapping.items()}
            total_amount = _parse_decimal(mapped.get("total_amount"))
            invoice_number = mapped.get("invoice_number") or None
            doc_type = DocumentType.invoice if (total_amount is not None or invoice_number) else DocumentType.unknown

            rows.append(
                _make_row(
                    document.id,
                    doc_type,
                    vendor_name=mapped.get("vendor_name") or None,
                    invoice_number=invoice_number,
                    invoice_date=_parse_date(mapped.get("invoice_date")),
                    due_date=_parse_date(mapped.get("due_date")),
                    total_amount=total_amount,
                    currency=mapped.get("currency") or None,
                    payment_terms_days=_parse_int(mapped.get("payment_terms_days")),
                    raw_extraction=source_row,
                )
            )
        except Exception as exc:  # noqa: BLE001 -- one bad row shouldn't kill the batch
            rows.append(
                _make_row(
                    document.id,
                    DocumentType.unknown,
                    raw_extraction=source_row,
                    error_message=str(exc),
                )
            )

    return rows


def _build_extraction_rows(document) -> list[DocumentExtraction]:
    llm = LLMService()
    if document.content_type == PDF_CONTENT_TYPE:
        return _rows_from_pdf(document, llm)
    if document.content_type in TABULAR_CONTENT_TYPES:
        return _rows_from_tabular(document, llm)
    raise ValueError(f"No Slice 2 extraction path for content type: {document.content_type}")


@celery_app.task(bind=True, max_retries=5)
def extract_document(self, document_id: str):
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            logger.warning("extract_document: document %s not found", document_id)
            return

        document.status = ProcessingStatus.processing
        db.commit()

        try:
            rows = _build_extraction_rows(document)
        except TRANSIENT_LLM_ERRORS as exc:
            logger.warning("extract_document: transient error for %s, retrying: %s", document_id, exc)
            try:
                raise self.retry(exc=exc, countdown=min(2**self.request.retries * 10, 600))
            except MaxRetriesExceededError:
                document.status = ProcessingStatus.failed
                db.commit()
                logger.error("extract_document: giving up on %s after retries: %s", document_id, exc)
                return
        except Exception as exc:  # noqa: BLE001 -- permanent failure, no retry
            document.status = ProcessingStatus.failed
            db.commit()
            logger.error("extract_document: permanent failure for %s: %s", document_id, exc)
            return

        db.query(DocumentExtraction).filter(DocumentExtraction.document_id == document.id).delete()
        db.add_all(rows)
        document.status = ProcessingStatus.processed
        db.commit()
    finally:
        db.close()
