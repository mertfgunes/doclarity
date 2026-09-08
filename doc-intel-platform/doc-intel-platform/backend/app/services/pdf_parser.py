import pdfplumber


def extract_pdf_text(file_path: str) -> str:
    """Extract text and any tables from a PDF, deterministically (no LLM).

    Tables are appended as pipe-delimited text after the page's prose text
    so the LLM extraction step sees both in reading order.
    """
    parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())

            for table in page.extract_tables():
                rows = [" | ".join(cell or "" for cell in row) for row in table]
                if rows:
                    parts.append("\n".join(rows))

    full_text = "\n\n".join(parts).strip()
    if not full_text:
        raise ValueError(f"No extractable text found in PDF: {file_path}")
    return full_text
