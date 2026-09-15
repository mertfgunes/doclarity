import os
import uuid
from typing import List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.core.config import settings
from app.core.db import get_db
from app.models.document import Document, ProcessingStatus
from app.models.extraction import DocumentExtraction
from app.models.schemas import DocumentExtractionOut, DocumentOut
from app.tasks.embedding import embed_document
from app.tasks.extraction import extract_document

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}


@router.post("/upload", response_model=DocumentOut, dependencies=[Depends(require_admin)])
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    os.makedirs(settings.upload_dir, exist_ok=True)

    file_id = uuid.uuid4()
    ext = os.path.splitext(file.filename)[1]
    storage_path = os.path.join(settings.upload_dir, f"{file_id}{ext}")

    contents = await file.read()
    with open(storage_path, "wb") as f:
        f.write(contents)

    doc = Document(
        id=file_id,
        filename=file.filename,
        content_type=file.content_type,
        storage_path=storage_path,
        status=ProcessingStatus.uploaded,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    extract_document.delay(str(doc.id))
    embed_document.delay(str(doc.id))

    return doc


@router.get("", response_model=List[DocumentOut])
def list_documents(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/extractions", response_model=List[DocumentExtractionOut])
def get_document_extractions(document_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return (
        db.query(DocumentExtraction)
        .filter(DocumentExtraction.document_id == document_id)
        .order_by(DocumentExtraction.created_at)
        .all()
    )
