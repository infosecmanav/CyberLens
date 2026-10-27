"""Add analytical dimensions to evidence.

Revision ID: 20261027_0012
Revises: 20261026_0011
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261027_0012"
down_revision: str | None = "20261026_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_DIMENSIONS = (
    "MALICIOUSNESS",
    "VULNERABILITY_CONTEXT",
    "MALWARE_ASSOCIATION",
    "INFRASTRUCTURE_ASSOCIATION",
    "BEHAVIORAL_ASSOCIATION",
    "THREAT_ACTOR_ATTRIBUTION",
    "DETECTION_APPLICABILITY",
    "GENERAL_CONTEXT",
)


def upgrade() -> None:
    op.add_column(
        "evidence",
        sa.Column(
            "assessment_dimension",
            sa.Enum(
                *_DIMENSIONS,
                name="evidencedimension",
                native_enum=False,
                length=40,
            ),
            server_default="GENERAL_CONTEXT",
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE evidence SET assessment_dimension = 'MALICIOUSNESS'
        WHERE observation_id IN (
            SELECT id FROM observations WHERE observation_type IN (
                'BENIGN_CLASSIFICATION', 'BOTNET_COMMAND_AND_CONTROL',
                'COMMUNITY_ABUSE_REPORTS', 'KNOWN_EXPLOITED_VULNERABILITY',
                'PHISHING_URL_FEED_ENTRY', 'VIRUSTOTAL_REPUTATION'
            )
        )
        """
    )
    op.execute(
        """
        UPDATE evidence SET assessment_dimension = 'VULNERABILITY_CONTEXT'
        WHERE observation_id IN (
            SELECT id FROM observations WHERE observation_type IN (
                'CVE_RECORD', 'NVD_CVE', 'VULNERABILITY_ADVISORY'
            )
        )
        """
    )
    op.execute(
        """
        UPDATE evidence SET assessment_dimension = 'MALWARE_ASSOCIATION'
        WHERE observation_id IN (
            SELECT id FROM observations WHERE observation_type IN (
                'MALWARE_DISTRIBUTION_CONTEXT', 'MALWARE_SAMPLE_CONTEXT',
                'THREATFOX_IOC_MATCH'
            )
        )
        """
    )
    op.execute(
        """
        UPDATE evidence SET assessment_dimension = 'INFRASTRUCTURE_ASSOCIATION'
        WHERE observation_id IN (
            SELECT id FROM observations WHERE observation_type IN (
                'CERTIFICATE_TRANSPARENCY', 'INTERNET_EXPOSURE',
                'INTERNET_SCANNER_CONTEXT', 'REGISTRATION_CONTEXT',
                'URLSCAN_SEARCH_CONTEXT'
            )
        )
        """
    )
    op.execute(
        """
        UPDATE evidence SET assessment_dimension = 'BEHAVIORAL_ASSOCIATION'
        WHERE observation_id IN (
            SELECT id FROM observations WHERE observation_type = 'ATTACK_TECHNIQUE'
        )
        """
    )
    op.alter_column("evidence", "assessment_dimension", server_default=None)


def downgrade() -> None:
    op.drop_column("evidence", "assessment_dimension")
