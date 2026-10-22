"""Add Phase 2 collection jobs and source records.

Revision ID: 20261022_0002
Revises: 20261022_0001
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261022_0002"
down_revision: str | None = "20261022_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collection_jobs",
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("requested_source_ids", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("outcome_summary", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entities.id"], ondelete="CASCADE",
            name=op.f("fk_collection_jobs_entity_id_entities"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collection_jobs")),
    )
    op.create_index(op.f("ix_collection_jobs_entity_id"), "collection_jobs", ["entity_id"])
    op.create_index(op.f("ix_collection_jobs_status"), "collection_jobs", ["status"])

    op.create_table(
        "source_records",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(500)),
        sa.Column("source_reference", sa.String(1000)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("raw_record", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"], ["entities.id"], ondelete="CASCADE",
            name=op.f("fk_source_records_entity_id_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], ondelete="RESTRICT",
            name=op.f("fk_source_records_source_id_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_records")),
        sa.UniqueConstraint(
            "source_id", "entity_id", "content_hash",
            name=op.f("uq_source_records_source_id"),
        ),
    )
    op.create_index(op.f("ix_source_records_entity_id"), "source_records", ["entity_id"])
    op.create_index("ix_source_records_reference", "source_records", ["source_reference"])
    op.create_index(op.f("ix_source_records_source_id"), "source_records", ["source_id"])

    op.add_column("observations", sa.Column("source_record_id", sa.Uuid()))
    op.create_foreign_key(
        op.f("fk_observations_source_record_id_source_records"),
        "observations", "source_records", ["source_record_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_observations_source_record_id"), "observations", ["source_record_id"]
    )
    op.create_unique_constraint(
        op.f("uq_observations_source_record_id"),
        "observations", ["source_record_id", "observation_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_observations_source_record_id"), "observations", type_="unique"
    )
    op.drop_index(op.f("ix_observations_source_record_id"), table_name="observations")
    op.drop_constraint(
        op.f("fk_observations_source_record_id_source_records"),
        "observations", type_="foreignkey",
    )
    op.drop_column("observations", "source_record_id")
    op.drop_table("source_records")
    op.drop_table("collection_jobs")
