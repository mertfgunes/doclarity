from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.db import Base, engine
from app.models import chunk, document, extraction  # noqa: F401 -- import so create_all sees their tables
from app.api import analytics, anomalies, ask, dashboard, documents, query

# Creates tables directly for now; swap for Alembic migrations once the schema stabilizes.
with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Doclarity")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(ask.router)
app.include_router(analytics.router)
app.include_router(query.router)
app.include_router(dashboard.router)
app.include_router(anomalies.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
