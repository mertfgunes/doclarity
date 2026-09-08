from dataclasses import dataclass

import pandas as pd

SAMPLE_ROWS_FOR_MAPPING = 5


@dataclass
class ParsedTable:
    columns: list[str]
    sample_rows: list[dict]
    rows: list[dict]


def parse_tabular_file(file_path: str, content_type: str) -> ParsedTable:
    """Parse a CSV or XLSX into rows, deterministically (no LLM).

    Column *meaning* (which column is the vendor, the total, etc.) is left to
    the LLM semantic-mapping step -- this just gets clean row dicts out.
    """
    if content_type == "text/csv":
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(file_path, dtype=str)
        df = df.fillna("")

    if df.empty:
        raise ValueError(f"No data rows found in tabular file: {file_path}")

    df.columns = [str(c).strip() for c in df.columns]
    rows = df.to_dict(orient="records")

    return ParsedTable(
        columns=list(df.columns),
        sample_rows=rows[:SAMPLE_ROWS_FOR_MAPPING],
        rows=rows,
    )
