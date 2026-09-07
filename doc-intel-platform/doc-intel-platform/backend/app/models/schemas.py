import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.document import ProcessingStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    status: ProcessingStatus
    uploaded_at: datetime

    class Config:
        from_attributes = True
