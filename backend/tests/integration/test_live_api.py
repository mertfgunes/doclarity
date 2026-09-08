"""
Integration tests against a REAL running instance (Postgres + Redis +
FastAPI + Celery worker), not the unit-test mocks. Requires the stack to
already be up - see README.md "Local setup".

These auto-skip (not fail) if nothing is listening at LIVE_API_BASE_URL,
so they're safe to leave in the normal `pytest tests/` run.
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


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


def _upload(client, filename, content_type):
    path = os.path.join(SAMPLES_DIR, filename)
    with open(path, "rb") as f:
        response = client.post("/documents/upload", files={"file": (filename, f, content_type)})
    return response


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_then_appears_in_list_and_get(client):
    upload_response = _upload(client, "sample_invoices.csv", "text/csv")
    assert upload_response.status_code == 200
    doc = upload_response.json()
    assert doc["filename"] == "sample_invoices.csv"
    assert doc["status"] == "uploaded"

    list_response = client.get("/documents")
    assert list_response.status_code == 200
    assert any(d["id"] == doc["id"] for d in list_response.json())

    get_response = client.get(f"/documents/{doc['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == doc["id"]


def test_get_unknown_document_404s(client):
    response = client.get("/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_upload_rejects_unsupported_content_type(client):
    response = client.post(
        "/documents/upload",
        files={"file": ("archive.zip", b"not a real zip", "application/zip")},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "filename,content_type",
    [
        ("sample_invoices.csv", "text/csv"),
        ("sample_invoice.pdf", "application/pdf"),
    ],
)
def test_upload_is_picked_up_by_celery(client, filename, content_type):
    """Proves the real Celery pipeline runs end to end: upload -> task
    picked up -> document leaves "uploaded"/"processing". Without a real
    ANTHROPIC_API_KEY the terminal state will be "failed" (auth error) -
    that's expected here, not a bug; see seed_demo_data.py for a way to
    see real "processed" rows without a key.
    """
    upload_response = _upload(client, filename, content_type)
    assert upload_response.status_code == 200
    doc_id = upload_response.json()["id"]

    status = "uploaded"
    for _ in range(20):
        status = client.get(f"/documents/{doc_id}").json()["status"]
        if status not in ("uploaded", "processing"):
            break
        time.sleep(1)

    assert status in ("processed", "failed"), f"extraction never reached a terminal state (stuck at {status!r})"
