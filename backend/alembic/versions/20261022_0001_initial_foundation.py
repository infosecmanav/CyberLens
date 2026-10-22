"""Initial ThreatLens foundation schema.

Revision ID: 20261022_0001
Revises:
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261022_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "sources",
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("official_url", sa.String(500)),
        sa.Column("api_documentation_url", sa.String(500)),
        sa.Column("access_method", sa.String(80), nullable=False),
        sa.Column("auth_scheme", sa.String(80), nullable=False),
        sa.Column("environment_variables", sa.JSON(), nullable=False),
        sa.Column("free_access_status", sa.String(120), nullable=False),
        sa.Column("commercial_usage_status", sa.String(120), nullable=False),
        sa.Column("terms_and_licensing_notes", sa.Text()),
        sa.Column("supported_entity_types", sa.JSON(), nullable=False),
        sa.Column("supported_operations", sa.JSON(), nullable=False),
        sa.Column("rate_limit_policy", sa.JSON(), nullable=False),
        sa.Column("caching_policy", sa.JSON(), nullable=False),
        sa.Column("attribution_requirements", sa.Text()),
        sa.Column("implementation_status", sa.String(40), nullable=False),
        sa.Column("last_checked", sa.DateTime(timezone=True)),
        sa.Column("last_success", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("health_status", sa.String(24), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("name", name=op.f("uq_sources_name")),
    )
    op.create_index(op.f("ix_sources_category"), "sources", ["category"])
    op.create_index(op.f("ix_sources_implementation_status"), "sources", ["implementation_status"])
    op.create_index(op.f("ix_sources_source_id"), "sources", ["source_id"], unique=True)

    op.create_table(
        "entities",
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("value", sa.String(2048), nullable=False),
        sa.Column("normalized_value", sa.String(2048), nullable=False),
        sa.Column("display_name", sa.String(500)),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entities")),
        sa.UniqueConstraint(
            "entity_type", "normalized_value", name=op.f("uq_entities_entity_type")
        ),
    )
    op.create_index("ix_entities_value", "entities", ["normalized_value"])

    op.create_table(
        "source_capabilities",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text()),
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
            ondelete="CASCADE",
            name=op.f("fk_source_capabilities_source_id_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_capabilities")),
        sa.UniqueConstraint(
            "source_id",
            "operation",
            "entity_type",
            name=op.f("uq_source_capabilities_source_id"),
        ),
    )
    op.create_index(op.f("ix_source_capabilities_source_id"), "source_capabilities", ["source_id"])

    op.create_table(
        "observations",
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("observation_type", sa.String(100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True)),
        sa.Column("confidence", sa.Float()),
        sa.Column("source_reference", sa.String(1000)),
        sa.Column("upstream_provenance", sa.String(500)),
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
            ondelete="CASCADE",
            name=op.f("fk_observations_entity_id_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            ondelete="RESTRICT",
            name=op.f("fk_observations_source_id_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_observations")),
    )
    op.create_index(op.f("ix_observations_entity_id"), "observations", ["entity_id"])
    op.create_index(op.f("ix_observations_observation_type"), "observations", ["observation_type"])
    op.create_index(op.f("ix_observations_source_id"), "observations", ["source_id"])

    op.create_table(
        "evidence",
        sa.Column("observation_id", sa.Uuid(), nullable=False),
        sa.Column("polarity", sa.String(20), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("uncertainty_notes", sa.Text()),
        sa.Column("analyst_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observations.id"],
            ondelete="CASCADE",
            name=op.f("fk_evidence_observation_id_observations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence")),
    )
    op.create_index(op.f("ix_evidence_observation_id"), "evidence", ["observation_id"])

    op.create_table(
        "entity_relationships",
        sa.Column("source_entity_id", sa.Uuid(), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("evidence_id", sa.Uuid()),
        sa.Column("first_seen", sa.DateTime(timezone=True)),
        sa.Column("last_seen", sa.DateTime(timezone=True)),
        sa.Column("confidence", sa.Float()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence.id"],
            ondelete="SET NULL",
            name=op.f("fk_entity_relationships_evidence_id_evidence"),
        ),
        sa.ForeignKeyConstraint(
            ["source_entity_id"],
            ["entities.id"],
            ondelete="CASCADE",
            name=op.f("fk_entity_relationships_source_entity_id_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["target_entity_id"],
            ["entities.id"],
            ondelete="CASCADE",
            name=op.f("fk_entity_relationships_target_entity_id_entities"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_entity_relationships")),
        sa.UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name=op.f("uq_entity_relationships_source_entity_id"),
        ),
    )
    op.create_index(
        op.f("ix_entity_relationships_evidence_id"), "entity_relationships", ["evidence_id"]
    )
    op.create_index(
        op.f("ix_entity_relationships_source_entity_id"),
        "entity_relationships",
        ["source_entity_id"],
    )
    op.create_index(
        op.f("ix_entity_relationships_target_entity_id"),
        "entity_relationships",
        ["target_entity_id"],
    )

    op.create_table(
        "audit_events",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("object_type", sa.String(100), nullable=False),
        sa.Column("object_id", sa.String(100)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            ondelete="SET NULL",
            name=op.f("fk_audit_events_actor_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("entity_relationships")
    op.drop_table("evidence")
    op.drop_table("observations")
    op.drop_table("source_capabilities")
    op.drop_table("entities")
    op.drop_table("sources")
    op.drop_table("users")
