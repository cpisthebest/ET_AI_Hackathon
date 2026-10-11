from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("regulatory_documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("regulator", sa.String(200), nullable=False),
        sa.Column("publication_date", sa.Date()),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("source_uri", sa.String(1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_regulatory_documents_sha256", "regulatory_documents", ["sha256"], unique=True)
    op.create_table("regulation_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("regulatory_documents.id", ondelete="CASCADE")),
        sa.Column("version_label", sa.String(100), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()),
        sa.Column("supersedes_id", sa.UUID(), sa.ForeignKey("regulation_versions.id")),
        sa.Column("status", sa.String(30), nullable=False))
    op.create_table("document_chunks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("document_id", sa.UUID(), sa.ForeignKey("regulatory_documents.id", ondelete="CASCADE")),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_tsv", sa.Text()),
        sa.Column("embedding", Vector(384)))
    op.create_index("ix_chunks_document_index", "document_chunks", ["document_id", "chunk_index"])
    op.create_index("ix_chunks_embedding_hnsw", "document_chunks", ["embedding"], postgresql_using="hnsw", postgresql_ops={"embedding":"vector_cosine_ops"})
    op.create_table("obligations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("regulation_version_id", sa.UUID(), sa.ForeignKey("regulation_versions.id", ondelete="CASCADE")),
        sa.Column("obligation_key", sa.String(200), unique=True, nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("action", sa.String(300), nullable=False),
        sa.Column("frequency", sa.String(100)),
        sa.Column("retention_years", sa.Integer()),
        sa.Column("applicability_rule", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()))
    op.create_table("controls",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("control_key", sa.String(200), unique=True, nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(200), nullable=False),
        sa.Column("frequency", sa.String(100)),
        sa.Column("retention_years", sa.Integer()),
        sa.Column("status", sa.String(50), nullable=False))
    op.create_table("obligation_control_mappings",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("obligation_id", sa.UUID(), sa.ForeignKey("obligations.id", ondelete="CASCADE")),
        sa.Column("control_id", sa.UUID(), sa.ForeignKey("controls.id", ondelete="CASCADE")),
        sa.Column("mapping_confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False))
    op.create_table("evidence",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("control_id", sa.UUID(), sa.ForeignKey("controls.id", ondelete="CASCADE")),
        sa.Column("evidence_key", sa.String(200), unique=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_date", sa.Date()),
        sa.Column("source_uri", sa.String(1000)),
        sa.Column("sha256", sa.String(64)),
        sa.Column("metadata_json", sa.JSON(), nullable=False))
    op.create_table("test_results",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("control_id", sa.UUID(), sa.ForeignKey("controls.id", ondelete="CASCADE")),
        sa.Column("evidence_id", sa.UUID(), sa.ForeignKey("evidence.id")),
        sa.Column("test_name", sa.String(500), nullable=False),
        sa.Column("result", sa.String(50), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("findings", sa.Text(), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("gaps",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("obligation_id", sa.UUID(), sa.ForeignKey("obligations.id", ondelete="CASCADE")),
        sa.Column("control_id", sa.UUID(), sa.ForeignKey("controls.id")),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_basis", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("human_approved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("remediations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("gap_id", sa.UUID(), sa.ForeignKey("gaps.id", ondelete="CASCADE")),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(200)),
        sa.Column("due_date", sa.Date()),
        sa.Column("status", sa.String(50), nullable=False))
    op.create_table("audit_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

def downgrade():
    for t in ["audit_events","remediations","gaps","test_results","evidence","obligation_control_mappings","controls","obligations","document_chunks","regulation_versions","regulatory_documents"]:
        op.drop_table(t)
