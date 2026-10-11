"""Add source-document provenance to extracted/derived compliance artifacts."""
from alembic import op
import sqlalchemy as sa

revision = "0004_document_provenance"
down_revision = "0003_document_driven_domain"
branch_labels = None
depends_on = None

TABLES = [
    "obligations",
    "obligation_control_mappings",
    "test_results",
    "gaps",
    "remediations",
]


def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("source_document_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_source_document",
            table,
            "source_documents",
            ["source_document_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    for table in reversed(TABLES):
        op.drop_constraint(f"fk_{table}_source_document", table, type_="foreignkey")
        op.drop_column(table, "source_document_id")
