"""Add reproducible import filters and filtered counts.

Revision ID: 20261025_0005
Revises: 20261025_0004
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261025_0005"
down_revision: str | None = "20261025_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "intelligence_imports",
        sa.Column(
            "filter_definition",
            sa.JSON(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column(
        "intelligence_imports",
        sa.Column("filtered_objects", sa.Integer(), server_default="0", nullable=False),
    )
    op.alter_column("intelligence_imports", "filter_definition", server_default=None)
    op.alter_column("intelligence_imports", "filtered_objects", server_default=None)


def downgrade() -> None:
    op.drop_column("intelligence_imports", "filtered_objects")
    op.drop_column("intelligence_imports", "filter_definition")
