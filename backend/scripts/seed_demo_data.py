"""
Seed the local database with demo extractions for every file in samples/,
without needing an ANTHROPIC_API_KEY.

Runs the real parsing (pdfplumber / pandas), the real DocumentExtraction
model, and the real validation layer - only the LLM call itself is stubbed
with a hand-written response standing in for what the model would return.
Useful for trying the app, or driving the frontend, with no API spend.

Usage (from backend/, with the venv active and Postgres reachable):
    python scripts/seed_demo_data.py
"""
import os
import shutil
import sys
import uuid
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal
from app.core.config import settings
from app.models.document import Document, ProcessingStatus
from app.tasks.extraction import _rows_from_pdf, _rows_from_tabular

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "samples")


def _mock_llm(**method_returns):
    llm = MagicMock()
    for method, value in method_returns.items():
        getattr(llm, method).return_value = value
    return llm


SPECS = [
    {
        "filename": "sample_invoices.csv",
        "content_type": "text/csv",
        "kind": "tabular",
        "llm": _mock_llm(
            map_csv_columns={
                "vendor_name": "Vendor",
                "invoice_number": "Invoice No",
                "total_amount": "Amount Due",
                "currency": "Currency Code",
                "invoice_date": "Billed On",
                "due_date": "Payment Due",
            }
        ),
    },
    {
        "filename": "sample_transactions.csv",
        "content_type": "text/csv",
        "kind": "tabular",
        "llm": _mock_llm(
            map_csv_columns={
                "vendor_name": "Supplier",
                "invoice_number": "Ref",
                "total_amount": "Total",
                "currency": "Cur",
                "invoice_date": "Issued",
                "payment_terms_days": "Terms (days)",
            }
        ),
    },
    {
        "filename": "sample_invoice.pdf",
        "content_type": "application/pdf",
        "kind": "pdf",
        "llm": _mock_llm(
            extract_document_fields={
                "document_type": "invoice",
                "invoice": {
                    "vendor_name": "Bluefin Hardware Ltd",
                    "invoice_number": "INV-77421",
                    "invoice_date": "2026-07-14",
                    "due_date": "2026-08-13",
                    "total_amount": 1385.00,
                    "currency": "EUR",
                    "payment_terms_days": 30,
                    "line_items": [
                        {"description": "Rack-mount server chassis", "quantity": 2, "unit_price": 410.00, "amount": 820.00},
                        {"description": "10Gb network switch", "quantity": 1, "unit_price": 295.00, "amount": 295.00},
                        {"description": "Installation labor (hrs)", "quantity": 6, "unit_price": 45.00, "amount": 270.00},
                    ],
                },
            }
        ),
    },
    {
        "filename": "sample_contract.pdf",
        "content_type": "application/pdf",
        "kind": "pdf",
        "llm": _mock_llm(
            extract_document_fields={
                "document_type": "contract",
                "contract": {
                    "parties": ["Doclarity Demo Client Inc.", "Meridian Consulting Group LLC"],
                    "effective_date": "2026-06-01",
                    "termination_date": "2027-05-31",
                    "governing_law": "Delaware",
                    "key_terms": [
                        "30 days written notice required to terminate",
                        "Monthly retainer per Exhibit A",
                        "Confidentiality obligations survive the term",
                    ],
                },
            }
        ),
    },
]


def seed():
    db = SessionLocal()
    os.makedirs(settings.upload_dir, exist_ok=True)

    for spec in SPECS:
        source_path = os.path.join(SAMPLES_DIR, spec["filename"])
        if not os.path.exists(source_path):
            print(f"skipping {spec['filename']}: not found in samples/")
            continue

        file_id = uuid.uuid4()
        ext = os.path.splitext(spec["filename"])[1]
        storage_path = os.path.join(settings.upload_dir, f"{file_id}{ext}")
        shutil.copy(source_path, storage_path)

        document = Document(
            id=file_id,
            filename=spec["filename"],
            content_type=spec["content_type"],
            storage_path=storage_path,
            status=ProcessingStatus.processing,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        if spec["kind"] == "tabular":
            rows = _rows_from_tabular(document, spec["llm"])
        else:
            rows = _rows_from_pdf(document, spec["llm"])

        db.add_all(rows)
        document.status = ProcessingStatus.processed
        db.commit()

        print(f"{spec['filename']}: document {document.id}, {len(rows)} extraction row(s)")

    db.close()


if __name__ == "__main__":
    seed()
