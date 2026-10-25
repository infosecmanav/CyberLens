"""Add bounded TAXII 2.1 server and collection polling.

Revision ID: 20261025_0007
Revises: 20261025_0006
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261025_0007"
down_revision: str | None = "20261025_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "taxii_servers",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("discovery_url", sa.String(length=1000), nullable=False),
        sa.Column("api_root_url", sa.String(length=1000)),
        sa.Column("auth_environment_variable", sa.String(length=120)),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("page_size", sa.Integer(), nullable=False),
        sa.Column("max_pages", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discovery_url"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_taxii_servers_created_by"), "taxii_servers", ["created_by"])
    op.create_table(
        "taxii_collections",
        sa.Column("server_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("can_read", sa.Boolean(), nullable=False),
        sa.Column("can_write", sa.Boolean(), nullable=False),
        sa.Column("media_types", sa.JSON(), nullable=False),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("poll_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("added_after_cursor", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["taxii_servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "collection_id"),
    )
    op.create_index(op.f("ix_taxii_collections_server_id"), "taxii_collections", ["server_id"])
    op.create_index(op.f("ix_taxii_collections_next_run_at"), "taxii_collections", ["next_run_at"])
    op.create_table(
        "taxii_collection_runs",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("triggered_by", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "RUNNING",
                "COMPLETED",
                "COMPLETED_WITH_ISSUES",
                "FAILED",
                name="taxiirunstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("pages_fetched", sa.Integer(), nullable=False),
        sa.Column("manifest_objects", sa.Integer(), nullable=False),
        sa.Column("received_objects", sa.Integer(), nullable=False),
        sa.Column("accepted_objects", sa.Integer(), nullable=False),
        sa.Column("rejected_objects", sa.Integer(), nullable=False),
        sa.Column("import_ids", sa.JSON(), nullable=False),
        sa.Column("cursor_started_at", sa.DateTime(timezone=True)),
        sa.Column("cursor_completed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["taxii_collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_taxii_collection_runs_collection_id"), "taxii_collection_runs", ["collection_id"]
    )
    op.create_index(
        op.f("ix_taxii_collection_runs_triggered_by"), "taxii_collection_runs", ["triggered_by"]
    )
    op.create_index(op.f("ix_taxii_collection_runs_status"), "taxii_collection_runs", ["status"])


def downgrade() -> None:
    op.drop_table("taxii_collection_runs")
    op.drop_table("taxii_collections")
    op.drop_table("taxii_servers")
