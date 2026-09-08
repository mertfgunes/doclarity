from datetime import date
from decimal import Decimal

from app.services.validation import validate_extraction


def test_clean_extraction_has_no_flags():
    flags = validate_extraction(
        total_amount=Decimal("110.00"),
        currency="USD",
        invoice_date=date(2026, 1, 1),
        due_date=date(2026, 1, 31),
        line_items=[{"description": "Widget", "amount": 100}, {"description": "Tax", "amount": 10}],
    )
    assert flags == []


def test_flags_unrecognized_currency():
    flags = validate_extraction(Decimal("100"), "ZZZ", None, None, None)
    assert any("currency" in f.lower() for f in flags)


def test_flags_due_date_before_invoice_date():
    flags = validate_extraction(
        Decimal("100"), "USD", date(2026, 2, 1), date(2026, 1, 1), None
    )
    assert any("due date" in f.lower() for f in flags)


def test_flags_line_items_mismatch():
    flags = validate_extraction(
        total_amount=Decimal("500.00"),
        currency="USD",
        invoice_date=None,
        due_date=None,
        line_items=[{"description": "Widget", "amount": 100}],
    )
    assert any("line items sum" in f.lower() for f in flags)


def test_tolerates_small_rounding_difference():
    flags = validate_extraction(
        total_amount=Decimal("100.00"),
        currency="USD",
        invoice_date=None,
        due_date=None,
        line_items=[{"description": "Widget", "amount": "99.99"}],
    )
    assert flags == []


def test_flags_missing_total():
    flags = validate_extraction(None, "USD", None, None, None)
    assert any("total_amount" in f for f in flags)
