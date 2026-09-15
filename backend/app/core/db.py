from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Bound to the least-privilege doclarity_readonly role (see
# db/init/01_readonly_role.sql) - used only to execute LLM-generated SQL
# for Slice 4 analytics, so a query can't write even if validation misses it.
analytics_engine = create_engine(settings.analytics_database_url)


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
