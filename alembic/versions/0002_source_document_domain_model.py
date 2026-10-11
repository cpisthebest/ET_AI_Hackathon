"""Introduce common source documents for regulations, controls and evidence."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002_source_doc_model"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("source_uri", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_source_documents_type", "source_documents", ["document_type"])
    op.create_index("ix_source_documents_sha256", "source_documents", ["sha256"], unique=True)

    # Backfill every existing regulatory document into the generic source layer.
    op.execute("""
        INSERT INTO source_documents (id, document_type, title, sha256, source_uri, created_at)
        SELECT id, 'REGULATION', title, sha256, source_uri, created_at
        FROM regulatory_documents
    """)

    op.add_column(
        "regulatory_documents",
        sa.Column("source_document_id", sa.UUID(), nullable=True),
    )
    op.execute("""
        UPDATE regulatory_documents
        SET source_document_id = id
    """)
    op.alter_column("regulatory_documents", "source_document_id", nullable=False)
    op.create_unique_constraint(
        "uq_regulatory_documents_source_document_id",
        "regulatory_documents",
        ["source_document_id"],
    )
    op.create_foreign_key(
        "fk_regulatory_documents_source_document",
        "regulatory_documents",
        "source_documents",
        ["source_document_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Move document chunks to the common source-document namespace.
    op.drop_constraint("document_chunks_document_id_fkey", "document_chunks", type_="foreignkey")
    op.execute("DROP INDEX IF EXISTS ix_chunks_document_index")
    op.create_foreign_key(
        "fk_document_chunks_source_document",
        "document_chunks",
        "source_documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_chunks_document_index", "document_chunks", ["document_id", "chunk_index"])

    op.create_table(
        "control_documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("control_id", sa.UUID(), sa.ForeignKey("controls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_document_id", sa.UUID(), sa.ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("source_document_id", name="uq_control_documents_source_document_id"),
    )

    op.add_column(
        "evidence",
        sa.Column("source_document_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_evidence_source_document",
        "evidence",
        "source_documents",
        ["source_document_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_evidence_source_document", "evidence", type_="foreignkey")
    op.drop_column("evidence", "source_document_id")
    op.drop_table("control_documents")
    op.drop_constraint("fk_document_chunks_source_document", "document_chunks", type_="foreignkey")
    op.drop_constraint("uq_regulatory_documents_source_document_id", "regulatory_documents", type_="unique")
    op.drop_constraint("fk_regulatory_documents_source_document", "regulatory_documents", type_="foreignkey")
    op.drop_column("regulatory_documents", "source_document_id")
    op.drop_index("ix_source_documents_sha256", table_name="source_documents")
    op.drop_index("ix_source_documents_type", table_name="source_documents")
    op.drop_table("source_documents")
    op.create_foreign_key(
        "document_chunks_document_id_fkey",
        "document_chunks",
        "regulatory_documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_chunks_document_index", "document_chunks", ["document_id", "chunk_index"])
