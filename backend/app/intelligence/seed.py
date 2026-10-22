from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.catalog import SOURCE_CATALOG
from app.models import Source, SourceCapability
from app.models.enums import SourceHealth


async def seed_source_catalog(session: AsyncSession) -> int:
    existing = {
        source.source_id: source for source in (await session.scalars(select(Source))).all()
    }
    existing_capabilities = {
        (capability.source_id, capability.operation, capability.entity_type): capability
        for capability in (await session.scalars(select(SourceCapability))).all()
    }
    created = 0
    for item in SOURCE_CATALOG:
        source = existing.get(item.source_id)
        if source is None:
            source = Source(
                source_id=item.source_id,
                name=item.name,
                category=item.category,
                official_url=item.official_url,
                health_status=(
                    SourceHealth.HEALTHY
                    if item.source_id == "local-fixtures"
                    else SourceHealth.UNKNOWN
                ),
            )
            session.add(source)
            await session.flush()
            existing[item.source_id] = source
            created += 1
        source.name = item.name
        source.category = item.category
        source.official_url = item.official_url
        source.api_documentation_url = item.api_documentation_url
        source.access_method = item.access_method
        source.auth_scheme = item.auth_scheme
        source.environment_variables = list(item.environment_variables)
        source.free_access_status = item.free_access_status
        source.commercial_usage_status = item.commercial_usage_status
        source.terms_and_licensing_notes = item.terms_and_licensing_notes
        source.supported_entity_types = list(item.supported_entity_types)
        source.supported_operations = list(item.supported_operations)
        source.rate_limit_policy = item.rate_limit_policy
        source.caching_policy = item.caching_policy
        source.attribution_requirements = item.attribution_requirements
        source.implementation_status = item.status
        for operation in item.supported_operations:
            for entity_type in item.supported_entity_types:
                key = (source.id, operation, entity_type)
                capability = existing_capabilities.get(key)
                if capability is None:
                    capability = SourceCapability(
                        source_id=source.id,
                        operation=operation,
                        entity_type=entity_type,
                        enabled=True,
                    )
                    session.add(capability)
                    existing_capabilities[key] = capability
                else:
                    capability.enabled = True
    await session.commit()
    return created
