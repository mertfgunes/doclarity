import pytest

from app.services.sql_guard import SQLGuardError, validate_select_only


def test_allows_simple_select_on_allowed_table():
    validate_select_only("SELECT vendor_name, total_amount FROM document_extractions")


def test_allows_join_across_allowed_tables():
    validate_select_only(
        "SELECT d.filename, e.total_amount FROM document_extractions e "
        "JOIN documents d ON d.id = e.document_id"
    )


def test_allows_cte_using_allowed_tables():
    validate_select_only(
        "WITH totals AS (SELECT vendor_name, total_amount FROM document_extractions) "
        "SELECT * FROM totals"
    )


def test_rejects_multiple_statements():
    with pytest.raises(SQLGuardError, match="one SQL statement"):
        validate_select_only("SELECT * FROM documents; DROP TABLE documents;")


def test_rejects_delete():
    with pytest.raises(SQLGuardError, match="SELECT statements"):
        validate_select_only("DELETE FROM documents")


def test_rejects_insert():
    with pytest.raises(SQLGuardError, match="SELECT statements"):
        validate_select_only("INSERT INTO documents (filename) VALUES ('x')")


def test_rejects_drop():
    with pytest.raises(SQLGuardError, match="SELECT statements"):
        validate_select_only("DROP TABLE documents")


def test_rejects_table_outside_allowlist():
    with pytest.raises(SQLGuardError, match="allowlist"):
        validate_select_only("SELECT * FROM document_chunks")


def test_rejects_unparseable_sql():
    # sqlglot is lenient and may not always raise a parse error outright for
    # garbage input - either way it must never be accepted as a valid SELECT.
    with pytest.raises(SQLGuardError):
        validate_select_only("SELEKT * FORM documents")


def test_rejects_garbled_input_that_sqlglot_cannot_parse_at_all():
    with pytest.raises(SQLGuardError, match="Could not parse"):
        validate_select_only("@@@ not sql at all (((")
