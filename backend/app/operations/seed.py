from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Playbook

DEFAULT_PLAYBOOKS: tuple[tuple[str, str, str, list[dict[str, object]]], ...] = (
    (
        "suspicious-ioc-triage",
        "Suspicious IOC triage",
        "Normalize, enrich, cross-check, assess, and assign a suspicious indicator.",
        [
            {"name": "Normalize indicator", "action": "NORMALIZE", "high_impact": False},
            {"name": "Collect intelligence", "action": "ENRICH", "high_impact": False},
            {"name": "Review evidence", "action": "ANALYST_REVIEW", "high_impact": False},
        ],
    ),
    (
        "malware-hash-investigation",
        "Malware hash investigation",
        "Collect metadata and behavioral evidence without downloading or executing samples.",
        [{"name": "Enrich hash metadata", "action": "ENRICH", "high_impact": False}],
    ),
    (
        "phishing-domain-url",
        "Phishing domain or URL investigation",
        "Review URL, domain, registration, certificate, and phishing evidence.",
        [{"name": "Analyze URL safely", "action": "ENRICH", "high_impact": False}],
    ),
    (
        "infrastructure-pivoting",
        "Infrastructure pivoting",
        "Explore bounded, evidence-backed infrastructure relationships.",
        [{"name": "Expand graph", "action": "GRAPH_EXPAND", "high_impact": False}],
    ),
    (
        "exploited-vulnerability",
        "Exploited vulnerability assessment",
        "Review exploitation evidence, affected assets, and remediation context.",
        [{"name": "Check exploitation evidence", "action": "ENRICH", "high_impact": False}],
    ),
    (
        "campaign-investigation",
        "Campaign investigation",
        "Correlate campaign reports, malware, infrastructure, and ATT&CK techniques.",
        [{"name": "Correlate campaign", "action": "CORRELATE", "high_impact": False}],
    ),
    (
        "public-research-processing",
        "Public research report processing",
        "Treat report text as untrusted data and extract reviewable intelligence.",
        [{"name": "Parse untrusted report", "action": "REPORT_PARSE", "high_impact": False}],
    ),
    (
        "detection-engineering-review",
        "Detection engineering review",
        "Review telemetry assumptions, candidate logic, false positives, and validation evidence.",
        [{"name": "Review candidate", "action": "DETECTION_REVIEW", "high_impact": False}],
    ),
    (
        "sector-threat-monitoring",
        "Sector-specific threat monitoring",
        "Track a bounded objective and create tasks for material intelligence changes.",
        [{"name": "Run monitoring objective", "action": "MONITOR", "high_impact": False}],
    ),
)


async def seed_playbooks(session: AsyncSession) -> int:
    existing = set((await session.scalars(select(Playbook.slug))).all())
    created = 0
    for slug, name, description, steps in DEFAULT_PLAYBOOKS:
        if slug in existing:
            continue
        session.add(
            Playbook(
                slug=slug,
                name=name,
                description=description,
                steps=steps,
                is_active=True,
                version=1,
            )
        )
        created += 1
    await session.commit()
    return created
