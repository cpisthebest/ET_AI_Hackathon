"""Allow document-driven multi-control/evidence extraction."""

from alembic import op

revision = "0003_document_driven_domain"
down_revision = "0002_source_doc_model"
branch_labels = None
depends_on = None


def upgrade():
    # A source document may describe multiple controls.
    op.drop_constraint("uq_control_documents_source_document_id", "control_documents", type_="unique")
    op.create_unique_constraint(
        "uq_control_documents_control_source",
        "control_documents",
        ["control_id", "source_document_id"],
    )
    # Evidence can exist before a reliable control mapping is established.
    op.alter_column("evidence", "control_id", nullable=True)
    op.drop_constraint("evidence_control_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key(
        "evidence_control_id_fkey",
        "evidence",
        "controls",
        ["control_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("evidence_control_id_fkey", "evidence", type_="foreignkey")
    op.create_foreign_key(
        "evidence_control_id_fkey",
        "evidence",
        "controls",
        ["control_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("evidence", "control_id", nullable=False)
    op.drop_constraint("uq_control_documents_control_source", "control_documents", type_="unique")
    op.create_unique_constraint(
        "uq_control_documents_source_document_id",
        "control_documents",
        ["source_document_id"],
    )
