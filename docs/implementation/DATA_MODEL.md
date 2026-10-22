# ThreatLens data model

The initial migration establishes the concepts required to preserve source lineage.

| Model | Purpose |
| --- | --- |
| `User` | Analyst identity, role, active state, and password hash |
| `Source` | Provider inventory, access metadata, configuration names, implementation state, and health |
| `SourceCapability` | Operation/entity support verified for one source |
| `Entity` | Canonical object such as a domain, hash, CVE, ASN, campaign, or ATT&CK technique |
| `CollectionJob` | One bounded connector run for a canonical entity, including requested sources and explicit outcome counts |
| `SourceRecord` | Deduplicated provider record with its retrieval time, original JSON, content hash, publication time, and source reference |
| `Observation` | What one source observed about one entity, with dates and raw lineage |
| `Evidence` | An observation used to support, conflict with, or contextualize an analytical claim |
| `EntityRelationship` | Typed, temporal link between two entities, optionally backed by evidence |
| `AuditEvent` | Immutable action record boundary for later operations |

An entity is not an observation. An observation is not automatically evidence. Evidence does not automatically establish a finding or attribution. These separations prevent provider scores and repeated upstream reports from becoming unsupported conclusions.

`Entity` uniqueness uses the entity type and normalized value. `SourceRecord` uniqueness uses the source, entity, and SHA-256 hash of the canonical provider record. A repeated lookup therefore creates a new `CollectionJob` while reusing matching entities, source records, and observations.

Phases 3–8 will add investigations, findings, assessments, detections, cases, playbooks, approvals, and monitoring through new Alembic revisions.

