from dataclasses import dataclass

CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150


@dataclass
class Chunk:
    page_number: int
    text: str


def chunk_pdf_pages(pages: list[tuple[int, str]]) -> list[Chunk]:
    """Split each page's text into overlapping, roughly fixed-size chunks.

    Chunks never span pages, so every chunk keeps one unambiguous page
    number for citations. Packing is word-based so a chunk never splits a
    word, even at the overlap boundary.
    """
    chunks: list[Chunk] = []
    for page_number, page_text in pages:
        for piece in _split_text(page_text):
            chunks.append(Chunk(page_number=page_number, text=piece))
    return chunks


def _split_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []

    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    i = 0
    while i < len(words):
        word = words[i]
        added_len = len(word) + (1 if current else 0)
        if current and current_len + added_len > CHUNK_SIZE_CHARS:
            pieces.append(" ".join(current))
            current = _trailing_words_within(current, CHUNK_OVERLAP_CHARS)
            current_len = sum(len(w) for w in current) + max(len(current) - 1, 0)
            continue
        current.append(word)
        current_len += added_len
        i += 1

    if current:
        pieces.append(" ".join(current))
    return pieces


def _trailing_words_within(words: list[str], max_chars: int) -> list[str]:
    """The longest suffix of `words` whose joined length fits within max_chars."""
    total = 0
    result: list[str] = []
    for word in reversed(words):
        total += len(word) + (1 if result else 0)
        if total > max_chars:
            break
        result.insert(0, word)
    return result
