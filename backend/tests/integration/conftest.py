"""
Shared fixtures for the live integration tests (tests/integration/). Seeds
known admin/viewer users directly via the DB session (no insecure "make me
admin" API - see scripts/create_admin.py), then logs in through the real
POST /auth/login endpoint to get a real token, so the login endpoint itself
is exercised too, not just bypassed.
"""
import os

import httpx
import pytest

from app.core.db import SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import hash_password

BASE_URL = os.environ.get("LIVE_API_BASE_URL", "http://localhost:8000")


def _seed_user_and_login(email: str, password: str, role: UserRole) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            db.add(User(email=email, hashed_password=hash_password(password), role=role))
        else:
            user.hashed_password = hash_password(password)
            user.role = role
        db.commit()
    finally:
        db.close()

    response = httpx.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password}, timeout=10)
    response.raise_for_status()
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    return _seed_user_and_login("test-admin@doclarity.local", "test-admin-password", UserRole.admin)


@pytest.fixture(scope="session")
def viewer_token():
    return _seed_user_and_login("test-viewer@doclarity.local", "test-viewer-password", UserRole.viewer)


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def viewer_headers(viewer_token):
    return {"Authorization": f"Bearer {viewer_token}"}
