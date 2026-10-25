"""Add controlled TAXII export policies and approval ledger.

Revision ID: 20261025_0009
Revises: 20261025_0008
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261025_0009"
down_revision: str | None = "20261025_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "taxii_export_policies",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("allowed_marking_refs", sa.JSON(), nullable=False),
        sa.Column("allow_unmarked", sa.Boolean(), nullable=False),
        sa.Column("max_objects", sa.Integer(), nullable=False),
        sa.Column("require_approval", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["taxii_collections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_taxii_export_policies_collection_id"),
        "taxii_export_policies",
        ["collection_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_taxii_export_policies_created_by"),
        "taxii_export_policies",
        ["created_by"],
    )
    op.create_table(
        "taxii_export_requests",
        sa.Column("policy_id", sa.Uuid(), nullable=False),
        sa.Column("approval_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_APPROVAL",
                "APPROVED",
                "REJECTED",
                "DELIVERING",
                "DELIVERED",
                "FAILED",
                name="exportstatus",
                native_enum=False,
                length=24,
            ),
            nullable=False,
        ),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("bundle_id", sa.String(length=100), nullable=False),
        sa.Column("bundle_hash", sa.String(length=64), nullable=False),
        sa.Column("stix_bundle", sa.JSON(), nullable=False),
        sa.Column("object_count", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_attempts", sa.Integer(), nullable=False),
        sa.Column("delivery_receipt", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["approval_id"], ["approval_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["policy_id"], ["taxii_export_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_taxii_export_requests_policy_id"), "taxii_export_requests", ["policy_id"]
    )
    op.create_index(
        op.f("ix_taxii_export_requests_approval_id"),
        "taxii_export_requests",
        ["approval_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_taxii_export_requests_requested_by"),
        "taxii_export_requests",
        ["requested_by"],
    )
    op.create_index(
        op.f("ix_taxii_export_requests_status"), "taxii_export_requests", ["status"]
    )
    op.create_index(
        op.f("ix_taxii_export_requests_bundle_id"),
        "taxii_export_requests",
        ["bundle_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("taxii_export_requests")
    op.drop_table("taxii_export_policies")
