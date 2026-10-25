# ThreatLens data model

The schema preserves the path from source retrieval to analyst action. An entity is not an observation; an observation is not automatically evidence; evidence does not automatically establish a finding, detection, or attribution.

| Area | Models | Purpose |
| --- | --- | --- |
| Access | `User` | Analyst identity, role, active state, and password hash |
| Sources | `Source`, `SourceCapability` | Provider inventory, access requirements, capabilities, implementation state, and health |
| Collection | `Entity`, `CollectionJob`, `SourceRecord`, `Observation`, `Evidence` | Canonical objects, bounded runs, deduplicated provider data, observations, and claim-level support/conflict/context |
| Correlation | `EntityRelationship`, `SimilarityScore` | Typed links with provenance and uncertainty; transparent shared-factor similarity |
| Investigation | `Investigation`, `InvestigationEntity`, `InvestigationStep`, `InvestigationEvent` | Durable plans, roles, execution state, budgets, attempts, and timeline |
| Analysis | `Finding`, `FindingEvidence`, `Assessment`, `AssessmentEvidence`, `AnalystDecision` | Evidence-backed claims, separate confidence dimensions, limitations, and immutable human verdict history |
| Detection | `DetectionCandidate`, `DetectionValidation` | Evidence-linked rule drafts, telemetry assumptions, false positives, and environment-specific validation |
| Operations | `Case`, `CaseTask`, `CaseEvidence`, `Playbook`, `PlaybookExecution`, `ApprovalRequest` | Owned work, seeded procedures, dry runs, and human approval gates |
| Monitoring | `MonitoringObjective`, `MonitoringRun`, `IntelligenceChange` | Schedules, fingerprints, baseline/deduplication state, material changes, and acknowledgement |
| Audit | `AuditEvent` | Append-only security and operational action records |

`Entity` uniqueness uses entity type plus normalized value. `SourceRecord` uniqueness uses source, entity, and the SHA-256 hash of canonical provider data. Repeat lookups therefore create distinct collection jobs while reusing matching entities, provider records, and observations.

`ImportBatch` records each submitted bundle independently, including repeated submissions of the same bundle hash. This preserves who submitted it, when it ran, the active parsing contract, and its aggregate outcomes. `ImportObjectOutcome` is unique by batch and object index. Accepted outcomes reference their canonical entity and observation; rejected or skipped outcomes retain the raw bounded object for review. Deleting an entity or observation clears the optional link without deleting the historical outcome.

Relationships may cite evidence and always carry provenance plus uncertainty notes. Findings and assessments use join models so evidence polarity and rationale are retained. Analyst decisions supersede prior decisions instead of updating them in place. Approvals retain requester, resolver, rationale, and timestamps.

Migration `20261024_0003` adds the Phase 3–8 operational schema and extends relationships with provenance and uncertainty. Migration `20261025_0004` adds the import ledger and ordered object outcomes. Alembic applies both transactionally after the foundation and collection revisions.
