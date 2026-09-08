from app.services.csv_parser import parse_tabular_file


def test_parse_csv(tmp_path):
    csv_path = tmp_path / "invoices.csv"
    csv_path.write_text(
        "Vendor,Inv#,Amount,Date\n"
        "Acme Co,INV-1,100.00,2026-01-01\n"
        "Widgets Ltd,INV-2,250.50,2026-01-02\n"
    )

    parsed = parse_tabular_file(str(csv_path), "text/csv")

    assert parsed.columns == ["Vendor", "Inv#", "Amount", "Date"]
    assert len(parsed.rows) == 2
    assert parsed.rows[0]["Vendor"] == "Acme Co"
    assert len(parsed.sample_rows) == 2


def test_parse_csv_empty_raises(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("Vendor,Inv#,Amount,Date\n")

    try:
        parse_tabular_file(str(csv_path), "text/csv")
        assert False, "expected ValueError"
    except ValueError:
        pass
