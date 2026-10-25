"""Add analyst evidence promotion links and metrics.

Revision ID: 20261025_0006
Revises: 20261025_0005
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261025_0006"
down_revision: str | None = "20261025_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("promoted_by", sa.Uuid()))
    op.create_foreign_key(
        op.f("fk_evidence_promoted_by_users"),
        "evidence",
        "users",
        ["promoted_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_evidence_promoted_by"), "evidence", ["promoted_by"])

    op.add_column(
        "intelligence_imports",
        sa.Column("promoted_objects", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("intelligence_imports", "promoted_objects", server_default=None)

    op.add_column("intelligence_import_objects", sa.Column("evidence_id", sa.Uuid()))
    op.create_foreign_key(
        op.f("fk_intelligence_import_objects_evidence_id_evidence"),
        "intelligence_import_objects",
        "evidence",
        ["evidence_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_intelligence_import_objects_evidence_id"),
        "intelligence_import_objects",
        ["evidence_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_intelligence_import_objects_evidence_id"),
        table_name="intelligence_import_objects",
    )
    op.drop_constraint(
        op.f("fk_intelligence_import_objects_evidence_id_evidence"),
        "intelligence_import_objects",
        type_="foreignkey",
    )
    op.drop_column("intelligence_import_objects", "evidence_id")
    op.drop_column("intelligence_imports", "promoted_objects")
    op.drop_index(op.f("ix_evidence_promoted_by"), table_name="evidence")
    op.drop_constraint(
        op.f("fk_evidence_promoted_by_users"), "evidence", type_="foreignkey"
    )
    op.drop_column("evidence", "promoted_by")
