from app.services.anomaly_detection import VendorBaseline, detect_anomalies


def _invoice(vendor, amount, extraction_id="e1"):
    return {"extraction_id": extraction_id, "vendor_name": vendor, "total_amount": amount}


def test_flags_invoice_far_above_vendor_mean():
    baselines = {"Acme": VendorBaseline(mean=100.0, stddev=10.0, invoice_count=5)}
    invoices = [_invoice("Acme", 100), _invoice("Acme", 3500)]

    result = detect_anomalies(invoices, baselines, z_threshold=3.0)

    assert len(result) == 1
    assert result[0]["total_amount"] == 3500
    assert result[0]["z_score"] > 3
    assert result[0]["ratio"] == 35.0


def test_does_not_flag_invoice_within_threshold():
    baselines = {"Acme": VendorBaseline(mean=100.0, stddev=10.0, invoice_count=5)}
    invoices = [_invoice("Acme", 115)]

    assert detect_anomalies(invoices, baselines, z_threshold=3.0) == []


def test_skips_vendor_with_zero_stddev():
    # Every invoice on file is identical - no variance to divide by, and a
    # single repeated amount isn't an outlier by definition.
    baselines = {"Acme": VendorBaseline(mean=100.0, stddev=0.0, invoice_count=5)}
    invoices = [_invoice("Acme", 100), _invoice("Acme", 9999)]

    assert detect_anomalies(invoices, baselines, z_threshold=3.0) == []


def test_ignores_invoices_from_vendors_without_a_baseline():
    baselines = {"Acme": VendorBaseline(mean=100.0, stddev=10.0, invoice_count=5)}
    invoices = [_invoice("Unknown Vendor", 99999)]

    assert detect_anomalies(invoices, baselines, z_threshold=3.0) == []


def test_flags_both_high_and_low_outliers():
    baselines = {"Acme": VendorBaseline(mean=100.0, stddev=10.0, invoice_count=5)}
    invoices = [_invoice("Acme", 500, "high"), _invoice("Acme", 1, "low")]

    result = detect_anomalies(invoices, baselines, z_threshold=3.0)

    flagged_ids = {row["extraction_id"] for row in result}
    assert flagged_ids == {"high", "low"}


def test_sorts_most_anomalous_first():
    baselines = {"Acme": VendorBaseline(mean=100.0, stddev=10.0, invoice_count=5)}
    invoices = [_invoice("Acme", 400, "mild"), _invoice("Acme", 1000, "extreme")]

    result = detect_anomalies(invoices, baselines, z_threshold=3.0)

    assert [row["extraction_id"] for row in result] == ["extreme", "mild"]
