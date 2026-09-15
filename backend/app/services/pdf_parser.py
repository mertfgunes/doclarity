import pdfplumber


def extract_pdf_pages(file_path: str) -> list[tuple[int, str]]:
    """Extract text and tables per page, keeping page numbers for citations.

    Page numbers are 1-indexed to match how PDF viewers display them.
    """
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            parts = []
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())

            for table in page.extract_tables():
                rows = [" | ".join(cell or "" for cell in row) for row in table]
                if rows:
                    parts.append("\n".join(rows))

            page_text = "\n\n".join(parts).strip()
            if page_text:
                pages.append((page_number, page_text))

    if not pages:
        raise ValueError(f"No extractable text found in PDF: {file_path}")
    return pages


def extract_pdf_text(file_path: str) -> str:
    """Extract text and any tables from a PDF, deterministically (no LLM).

    Tables are appended as pipe-delimited text after the page's prose text
    so the LLM extraction step sees both in reading order.
    """
    pages = extract_pdf_pages(file_path)
    return "\n\n".join(text for _, text in pages)
