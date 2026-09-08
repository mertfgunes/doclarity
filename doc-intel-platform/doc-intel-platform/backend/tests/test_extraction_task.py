from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.extraction import DocumentType, ExtractionStatus
from app.tasks import extraction as extraction_task


def test_parse_date_valid_and_invalid():
    assert extraction_task._parse_date("2026-01-15") == date(2026, 1, 15)
    assert extraction_task._parse_date("not a date") is None
    assert extraction_task._parse_date(None) is None


def test_parse_decimal_and_int():
    assert extraction_task._parse_decimal("110.50") == Decimal("110.50")
    assert extraction_task._parse_decimal("garbage") is None
    assert extraction_task._parse_int("30") == 30
    assert extraction_task._parse_int("thirty") is None


def test_rows_from_pdf_invoice(monkeypatch):
    monkeypatch.setattr(extraction_task, "extract_pdf_text", lambda path: "Invoice text")

    llm = MagicMock()
    llm.extract_document_fields.return_value = {
        "document_type": "invoice",
        "invoice": {
            "vendor_name": "Acme Co",
            "invoice_number": "INV-1",
            "invoice_date": "2026-01-01",
            "due_date": "2026-01-31",
            "total_amount": 110.0,
            "currency": "USD",
            "payment_terms_days": 30,
            "line_items": [{"description": "Widget", "amount": 110.0}],
        },
    }

    document = SimpleNamespace(id="doc-1", storage_path="fake.pdf", content_type="application/pdf")
    rows = extraction_task._rows_from_pdf(document, llm)

    assert len(rows) == 1
    row = rows[0]
    assert row.document_type == DocumentType.invoice
    assert row.vendor_name == "Acme Co"
    assert row.total_amount == Decimal("110.0")
    assert row.status == ExtractionStatus.completed


def test_rows_from_pdf_flags_low_confidence(monkeypatch):
    monkeypatch.setattr(extraction_task, "extract_pdf_text", lambda path: "Invoice text")

    llm = MagicMock()
    llm.extract_document_fields.return_value = {
        "document_type": "invoice",
        "invoice": {
            "vendor_name": "Acme Co",
            "total_amount": 110.0,
            "currency": "NOTREAL",
        },
    }

    document = SimpleNamespace(id="doc-1", storage_path="fake.pdf", content_type="application/pdf")
    rows = extraction_task._rows_from_pdf(document, llm)

    assert rows[0].status == ExtractionStatus.needs_review
    assert rows[0].confidence_flags


def test_rows_from_tabular_maps_columns(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text(
        "Vendor,Inv#,Amount,Date\n"
        "Acme Co,INV-1,100.00,2026-01-01\n"
        "Widgets Ltd,INV-2,250.50,2026-01-02\n"
    )

    llm = MagicMock()
    llm.map_csv_columns.return_value = {
        "vendor_name": "Vendor",
        "invoice_number": "Inv#",
        "total_amount": "Amount",
        "invoice_date": "Date",
    }

    document = SimpleNamespace(id="doc-2", storage_path=str(csv_path), content_type="text/csv")
    rows = extraction_task._rows_from_tabular(document, llm)

    assert len(rows) == 2
    assert rows[0].vendor_name == "Acme Co"
    assert rows[0].total_amount == Decimal("100.00")
    assert rows[0].document_type == DocumentType.invoice
    assert rows[1].invoice_number == "INV-2"
