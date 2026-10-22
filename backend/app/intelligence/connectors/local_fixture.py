from datetime import UTC, datetime

from app.intelligence.connectors.base import BaseIntelligenceConnector
from app.intelligence.connectors.models import (
    ConnectorCapability,
    ConnectorManifest,
    ConnectorOutcome,
    ConnectorRequest,
    ConnectorResult,
    NormalizedObservation,
)


class LocalFixtureConnector(BaseIntelligenceConnector):
    """Deterministic local data used for development and tests, never labelled as live CTI."""

    manifest = ConnectorManifest(
        source_id="local-fixtures",
        name="Local development fixtures",
        capabilities=[
            ConnectorCapability(
                operation="lookup",
                entity_types={"IPV4", "DOMAIN", "URL", "SHA256", "CVE"},
                notes="Returns explicitly labelled demonstration observations",
            )
        ],
    )

    async def health_check(self) -> ConnectorResult:
        return ConnectorResult(source_id=self.manifest.source_id, outcome=ConnectorOutcome.SUCCESS)

    async def lookup(self, request: ConnectorRequest) -> ConnectorResult:
        if request.entity is None:
            return self.not_supported("lookup without an entity")
        return ConnectorResult(
            source_id=self.manifest.source_id,
            outcome=ConnectorOutcome.SUCCESS,
            observations=[
                NormalizedObservation(
                    entity=request.entity,
                    observation_type="DEMONSTRATION_ONLY",
                    summary="Local fixture response; this is not external threat intelligence.",
                    observed_at=datetime.now(UTC),
                    attributes={"demonstration": True},
                    raw_record={
                        "fixture": "demonstration",
                        "entity_type": request.entity.entity_type,
                        "entity_value": request.entity.value,
                    },
                    external_id=(
                        f"fixture:{request.entity.entity_type}:{request.entity.value}"
                    ),
                )
            ],
        )
