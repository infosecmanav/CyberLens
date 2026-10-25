"""Add durable intelligence import history and object outcomes.

Revision ID: 20261025_0004
Revises: 20261024_0003
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261025_0004"
down_revision: str | None = "20261024_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_imports",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=False),
        sa.Column("bundle_id", sa.String(100), nullable=False),
        sa.Column("bundle_hash", sa.String(64), nullable=False),
        sa.Column("format", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("source_reference", sa.String(1000)),
        sa.Column("contract", sa.JSON(), nullable=False),
        sa.Column("received_objects", sa.Integer(), nullable=False),
        sa.Column("accepted_objects", sa.Integer(), nullable=False),
        sa.Column("imported_observations", sa.Integer(), nullable=False),
        sa.Column("deduplicated_observations", sa.Integer(), nullable=False),
        sa.Column("created_entities", sa.Integer(), nullable=False),
        sa.Column("reused_entities", sa.Integer(), nullable=False),
        sa.Column("rejected_objects", sa.Integer(), nullable=False),
        sa.Column("skipped_objects", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_intelligence_imports_source_id_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"],
            ["users.id"],
            name=op.f("fk_intelligence_imports_submitted_by_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intelligence_imports")),
    )
    op.create_index(
        op.f("ix_intelligence_imports_bundle_hash"),
        "intelligence_imports",
        ["bundle_hash"],
    )
    op.create_index(
        op.f("ix_intelligence_imports_bundle_id"), "intelligence_imports", ["bundle_id"]
    )
    op.create_index(
        op.f("ix_intelligence_imports_source_id"), "intelligence_imports", ["source_id"]
    )
    op.create_index(
        op.f("ix_intelligence_imports_status"), "intelligence_imports", ["status"]
    )
    op.create_index(
        op.f("ix_intelligence_imports_submitted_by"),
        "intelligence_imports",
        ["submitted_by"],
    )

    op.create_table(
        "intelligence_import_objects",
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("object_index", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(500)),
        sa.Column("disposition", sa.String(24), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("observation_id", sa.Uuid()),
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
            ["entity_id"],
            ["entities.id"],
            name=op.f("fk_intelligence_import_objects_entity_id_entities"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["intelligence_imports.id"],
            name=op.f("fk_intelligence_import_objects_import_batch_id_intelligence_imports"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observations.id"],
            name=op.f("fk_intelligence_import_objects_observation_id_observations"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intelligence_import_objects")),
        sa.UniqueConstraint(
            "import_batch_id",
            "object_index",
            name=op.f("uq_intelligence_import_objects_import_batch_id"),
        ),
    )
    op.create_index(
        op.f("ix_intelligence_import_objects_disposition"),
        "intelligence_import_objects",
        ["disposition"],
    )
    op.create_index(
        op.f("ix_intelligence_import_objects_entity_id"),
        "intelligence_import_objects",
        ["entity_id"],
    )
    op.create_index(
        op.f("ix_intelligence_import_objects_import_batch_id"),
        "intelligence_import_objects",
        ["import_batch_id"],
    )
    op.create_index(
        op.f("ix_intelligence_import_objects_observation_id"),
        "intelligence_import_objects",
        ["observation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_intelligence_import_objects_observation_id"),
        table_name="intelligence_import_objects",
    )
    op.drop_index(
        op.f("ix_intelligence_import_objects_import_batch_id"),
        table_name="intelligence_import_objects",
    )
    op.drop_index(
        op.f("ix_intelligence_import_objects_entity_id"),
        table_name="intelligence_import_objects",
    )
    op.drop_index(
        op.f("ix_intelligence_import_objects_disposition"),
        table_name="intelligence_import_objects",
    )
    op.drop_table("intelligence_import_objects")
    op.drop_index(
        op.f("ix_intelligence_imports_submitted_by"), table_name="intelligence_imports"
    )
    op.drop_index(op.f("ix_intelligence_imports_status"), table_name="intelligence_imports")
    op.drop_index(op.f("ix_intelligence_imports_source_id"), table_name="intelligence_imports")
    op.drop_index(op.f("ix_intelligence_imports_bundle_id"), table_name="intelligence_imports")
    op.drop_index(op.f("ix_intelligence_imports_bundle_hash"), table_name="intelligence_imports")
    op.drop_table("intelligence_imports")
