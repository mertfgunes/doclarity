from app.services.chunking import CHUNK_SIZE_CHARS, chunk_pdf_pages


def test_short_page_is_a_single_chunk():
    chunks = chunk_pdf_pages([(1, "short page text")])
    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].text == "short page text"


def test_long_page_splits_with_overlap_and_keeps_page_number():
    long_text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_pdf_pages([(3, long_text)])

    assert len(chunks) > 1
    assert all(c.page_number == 3 for c in chunks)
    assert all(len(c.text) <= CHUNK_SIZE_CHARS for c in chunks)
    # overlap: the chunk boundary should share some trailing/leading words
    assert chunks[1].text.split()[0] in chunks[0].text.split()


def test_chunks_never_span_pages():
    chunks = chunk_pdf_pages([(1, "page one text"), (2, "page two text")])
    pages_seen = {c.page_number for c in chunks}
    assert pages_seen == {1, 2}


def test_empty_pages_list_returns_no_chunks():
    assert chunk_pdf_pages([]) == []
