from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, anomalies, ask, auth, dashboard, documents, query
from app.core.config import settings

app = FastAPI(title="Doclarity")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(ask.router)
app.include_router(analytics.router)
app.include_router(query.router)
app.include_router(dashboard.router)
app.include_router(anomalies.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
