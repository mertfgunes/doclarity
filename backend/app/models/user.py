import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.db import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    viewer = "viewer"


class User(Base):
    """
    Slice 8: admin can upload documents and do everything a viewer can;
    viewer is read-only (query/ask/dashboard, not upload). Registration
    (app/api/auth.py) always creates a viewer - see scripts/create_admin.py
    for the only way to get an admin account.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.viewer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
