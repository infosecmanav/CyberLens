"""Add persisted evidence reconciliation to assessments.

Revision ID: 20261026_0011
Revises: 20261025_0010
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261026_0011"
down_revision: str | None = "20261025_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column(
            "evidence_reconciliation",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
    )
    op.alter_column("assessments", "evidence_reconciliation", server_default=None)


def downgrade() -> None:
    op.drop_column("assessments", "evidence_reconciliation")
