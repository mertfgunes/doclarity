"""Initial schema: documents, document_extractions, document_chunks

Baseline migration - captures the schema exactly as it already existed via
Base.metadata.create_all() before Slice 8 switched to Alembic. A fresh DB
should run `alembic upgrade head`; a DB that already has these three tables
from create_all should run `alembic stamp 0001` instead, to mark this
revision as already applied without re-running its DDL, then `alembic
upgrade head` to pick up 0002 (the new `users` table) for real (see README).

Revision ID: 0001
Revises:
Create Date: 2026-09-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("storage_path", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("uploaded", "processing", "processed", "failed", name="processing_status"),
            nullable=False,
        ),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "document_extractions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column(
            "document_type",
            sa.Enum("invoice", "contract", "unknown", name="document_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("completed", "needs_review", "failed", name="extraction_status"),
            nullable=False,
        ),
        sa.Column("vendor_name", sa.String(), nullable=True),
        sa.Column("invoice_number", sa.String(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("payment_terms_days", sa.Integer(), nullable=True),
        sa.Column("line_items", JSONB(), nullable=True),
        sa.Column("raw_extraction", JSONB(), nullable=True),
        sa.Column("confidence_flags", JSONB(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False, index=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("document_extractions")
    op.drop_table("documents")
    op.execute("DROP TYPE IF EXISTS extraction_status")
    op.execute("DROP TYPE IF EXISTS document_type")
    op.execute("DROP TYPE IF EXISTS processing_status")
