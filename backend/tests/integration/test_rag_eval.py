"""
A small RAG eval set (Slice 8): does /ask's retrieval surface the right
source document for a handful of known questions? Citations are exactly
the retrieved chunks (see Slice 3), so this checks retrieval quality
directly rather than grading the LLM's phrasing of the answer.

Requires the live stack - see README.md "Local setup". Auto-skips the same
way test_live_api.py does if nothing is listening, or if a document never
finishes embedding (LLM/embedding backend unavailable).
"""
import os
import time

import httpx
import pytest

BASE_URL = os.environ.get("LIVE_API_BASE_URL", "http://localhost:8000")
SAMPLES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "samples"
)

try:
    httpx.get(f"{BASE_URL}/health", timeout=2)
except httpx.HTTPError:
    pytest.skip(f"no live server reachable at {BASE_URL} - skipping integration tests", allow_module_level=True)

EVAL_CASES = [
    ("What is the vendor on this invoice?", "sample_invoice.pdf"),
    ("What is the total amount due on the invoice?", "sample_invoice.pdf"),
    ("What is the governing law of this contract?", "sample_contract.pdf"),
    ("Who are the parties to this contract?", "sample_contract.pdf"),
]


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=60) as c:
        yield c


def _upload_and_wait_until_embedded(client, headers, filename, content_type):
    path = os.path.join(SAMPLES_DIR, filename)
    with open(path, "rb") as f:
        upload_response = client.post("/documents/upload", files={"file": (filename, f, content_type)}, headers=headers)
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["id"]

    for _ in range(30):
        response = client.post("/ask", json={"question": "anything", "document_id": doc_id}, headers=headers)
        if response.json()["citations"]:
            return True
        time.sleep(1)
    return False


@pytest.fixture(scope="module")
def eval_documents_ready(client, admin_headers):
    """Uploads both eval fixture documents and waits for embedding to
    finish on each - shared across every eval case so it only happens once.
    """
    ready = _upload_and_wait_until_embedded(client, admin_headers, "sample_invoice.pdf", "application/pdf")
    ready = ready and _upload_and_wait_until_embedded(client, admin_headers, "sample_contract.pdf", "application/pdf")
    return ready


@pytest.mark.parametrize("question,expected_filename", EVAL_CASES)
def test_retrieval_surfaces_the_right_source_document(client, viewer_headers, eval_documents_ready, question, expected_filename):
    if not eval_documents_ready:
        pytest.skip("eval documents never finished embedding - LLM/embedding backend may be unavailable")

    response = client.post("/ask", json={"question": question}, headers=viewer_headers)
    assert response.status_code == 200
    citations = response.json()["citations"]
    if not citations:
        pytest.skip("no citations returned - embedding backend may be unavailable")

    top_filenames = {citation["filename"] for citation in citations}
    assert expected_filename in top_filenames, f"expected a citation from {expected_filename!r}, got {top_filenames!r}"
