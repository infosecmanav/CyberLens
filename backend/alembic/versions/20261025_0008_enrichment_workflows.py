"""Add bounded automated enrichment workflows.

Revision ID: 20261025_0008
Revises: 20261025_0007
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261025_0008"
down_revision: str | None = "20261025_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrichment_policies",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("entity_types", sa.JSON(), nullable=False),
        sa.Column("source_ids", sa.JSON(), nullable=False),
        sa.Column("max_entities_per_run", sa.Integer(), nullable=False),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_enrichment_policies_created_by"), "enrichment_policies", ["created_by"]
    )
    op.create_index(
        op.f("ix_enrichment_policies_next_run_at"), "enrichment_policies", ["next_run_at"]
    )
    op.create_table(
        "enrichment_runs",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("triggered_by", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "PARTIAL",
                "FAILED",
                name="collectionjobstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("candidate_entities", sa.Integer(), nullable=False),
        sa.Column("processed_entities", sa.Integer(), nullable=False),
        sa.Column("new_observations", sa.Integer(), nullable=False),
        sa.Column("source_outcomes", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["policy_id"], ["enrichment_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_enrichment_runs_policy_id"), "enrichment_runs", ["policy_id"])
    op.create_index(
        op.f("ix_enrichment_runs_triggered_by"), "enrichment_runs", ["triggered_by"]
    )
    op.create_index(op.f("ix_enrichment_runs_status"), "enrichment_runs", ["status"])
    op.create_table(
        "enrichment_items",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("collection_job_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "COMPLETED",
                "PARTIAL",
                "FAILED",
                name="collectionjobstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("source_outcomes", sa.JSON(), nullable=False),
        sa.Column("observation_ids", sa.JSON(), nullable=False),
        sa.Column("new_observation_ids", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collection_job_id"], ["collection_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["enrichment_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "entity_id"),
    )
    op.create_index(op.f("ix_enrichment_items_run_id"), "enrichment_items", ["run_id"])
    op.create_index(op.f("ix_enrichment_items_entity_id"), "enrichment_items", ["entity_id"])
    op.create_index(
        op.f("ix_enrichment_items_collection_job_id"),
        "enrichment_items",
        ["collection_job_id"],
    )
    op.create_index(op.f("ix_enrichment_items_status"), "enrichment_items", ["status"])


def downgrade() -> None:
    op.drop_table("enrichment_items")
    op.drop_table("enrichment_runs")
    op.drop_table("enrichment_policies")
