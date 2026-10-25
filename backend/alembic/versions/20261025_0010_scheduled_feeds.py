"""Add scheduled feed subscriptions and durable run ledger.

Revision ID: 20261025_0010
Revises: 20261025_0009
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261025_0010"
down_revision: str | None = "20261025_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feed_subscriptions",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False),
        sa.Column("max_records", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_feed_subscriptions_source_id", "feed_subscriptions", ["source_id"], unique=True)
    op.create_index(op.f("ix_feed_subscriptions_created_by"), "feed_subscriptions", ["created_by"])
    op.create_index(op.f("ix_feed_subscriptions_next_run_at"), "feed_subscriptions", ["next_run_at"])
    op.create_table(
        "feed_runs",
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("triggered_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "COMPLETED", "PARTIAL", "FAILED", name="collectionjobstatus", native_enum=False, length=20), nullable=False),
        sa.Column("connector_outcome", sa.String(length=40)),
        sa.Column("received_records", sa.Integer(), nullable=False),
        sa.Column("accepted_records", sa.Integer(), nullable=False),
        sa.Column("rejected_records", sa.Integer(), nullable=False),
        sa.Column("created_entities", sa.Integer(), nullable=False),
        sa.Column("reused_entities", sa.Integer(), nullable=False),
        sa.Column("new_observations", sa.Integer(), nullable=False),
        sa.Column("deduplicated_observations", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["feed_subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feed_runs_subscription_id"), "feed_runs", ["subscription_id"])
    op.create_index(op.f("ix_feed_runs_triggered_by"), "feed_runs", ["triggered_by"])
    op.create_index(op.f("ix_feed_runs_status"), "feed_runs", ["status"])
    op.create_table(
        "feed_run_items",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=500)),
        sa.Column("disposition", sa.String(length=24), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("observation_id", sa.Uuid()),
        sa.Column("source_record_id", sa.Uuid()),
        sa.Column("content_hash", sa.String(length=64)),
        sa.Column("raw_record", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["observation_id"], ["observations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["feed_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "record_index"),
    )
    op.create_index(op.f("ix_feed_run_items_run_id"), "feed_run_items", ["run_id"])
    op.create_index(op.f("ix_feed_run_items_disposition"), "feed_run_items", ["disposition"])
    op.create_index(op.f("ix_feed_run_items_entity_id"), "feed_run_items", ["entity_id"])
    op.create_index(op.f("ix_feed_run_items_observation_id"), "feed_run_items", ["observation_id"])
    op.create_index(op.f("ix_feed_run_items_source_record_id"), "feed_run_items", ["source_record_id"])


def downgrade() -> None:
    op.drop_table("feed_run_items")
    op.drop_table("feed_runs")
    op.drop_table("feed_subscriptions")
