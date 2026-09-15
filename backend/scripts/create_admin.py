"""
Create (or promote) an admin user. Registration via POST /auth/register
always creates a viewer - this is the only way to get an admin account, by
design, so the public API can never mint one.

Usage (from backend/, with the venv active and Postgres reachable):
    python scripts/create_admin.py <email> <password>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.db import SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import hash_password


def main(email: str, password: str) -> None:
    if len(password) < 8:
        raise SystemExit("password must be at least 8 characters")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, hashed_password=hash_password(password), role=UserRole.admin)
            db.add(user)
            print(f"Created admin user {email!r}.")
        else:
            user.hashed_password = hash_password(password)
            user.role = UserRole.admin
            print(f"Promoted existing user {email!r} to admin and reset their password.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python scripts/create_admin.py <email> <password>")
    main(sys.argv[1], sys.argv[2])
