# ThreatLens data model

The schema preserves the path from source retrieval to analyst action. An entity is not an observation; an observation is not automatically evidence; evidence does not automatically establish a finding, detection, or attribution.

| Area | Models | Purpose |
| --- | --- | --- |
| Access | `User` | Analyst identity, role, active state, and password hash |
| Sources | `Source`, `SourceCapability` | Provider inventory, access requirements, capabilities, implementation state, and health |
| Collection | `Entity`, `CollectionJob`, `SourceRecord`, `Observation`, `Evidence`, `FeedSubscription`, `FeedRun`, `FeedRunItem` | Canonical objects, bounded lookups and feeds, deduplicated provider data, per-record outcomes, observations, and claim-level support/conflict/context |
| Correlation | `EntityRelationship`, `SimilarityScore` | Typed links with provenance and uncertainty; transparent shared-factor similarity |
| Investigation | `Investigation`, `InvestigationEntity`, `InvestigationStep`, `InvestigationEvent` | Durable plans, roles, execution state, budgets, attempts, and timeline |
| Analysis | `Finding`, `FindingEvidence`, `Assessment`, `AssessmentEvidence`, `AnalystDecision` | Evidence-backed claims, provenance-aware reconciliation, separate confidence dimensions, limitations, and immutable human verdict history |
| Detection | `DetectionCandidate`, `DetectionValidation` | Evidence-linked rule drafts, telemetry assumptions, false positives, and environment-specific validation |
| Operations | `Case`, `CaseTask`, `CaseEvidence`, `Playbook`, `PlaybookExecution`, `ApprovalRequest` | Owned work, seeded procedures, dry runs, and human approval gates |
| Monitoring | `MonitoringObjective`, `MonitoringRun`, `IntelligenceChange` | Schedules, fingerprints, baseline/deduplication state, material changes, and acknowledgement |
| Audit | `AuditEvent` | Append-only security and operational action records |

`Entity` uniqueness uses entity type plus normalized value. `SourceRecord` uniqueness uses source, entity, and the SHA-256 hash of canonical provider data. Repeat lookups therefore create distinct collection jobs while reusing matching entities, provider records, and observations.

`ImportBatch` records each submitted bundle independently, including repeated submissions of the same bundle hash. This preserves who submitted it, when it ran, the active parsing contract, the canonical filter definition, and its aggregate outcomes. `ImportObjectOutcome` is unique by batch and object index. Accepted outcomes reference their canonical entity and observation; rejected, skipped, or filtered outcomes retain the raw bounded object for review. Deleting an entity or observation clears the optional link without deleting the historical outcome.

An analyst promotion creates an `Evidence` row without modifying the source observation. `Evidence.promoted_by` distinguishes analyst-reviewed promotions from engine-created evidence, while `analyst_reviewed_at`, polarity, claim, and uncertainty preserve the decision context. The originating `ImportObjectOutcome` links to the evidence, and its batch stores the promoted count for operational filtering.

Relationships may cite evidence and always carry provenance plus uncertainty notes. Findings and assessments use join models so evidence polarity and rationale are retained. Each assessment stores an evidence-reconciliation snapshot that groups exact normalized upstream references, reports provider repetition separately from independent provenance, and preserves conflicts. Analyst decisions supersede prior decisions instead of updating them in place. Approvals retain requester, resolver, rationale, and timestamps.

`FeedSubscription` binds a catalog source to an explicit cadence and record budget. `FeedRun` records connector and aggregate outcomes, while ordered `FeedRunItem` rows retain the disposition, hash, source record, entity, observation, and rejected raw record needed to inspect or reproduce collection. Feed ingestion reuses `SourceRecord` and `Observation` uniqueness and never promotes evidence automatically.

Migration `20261024_0003` adds the Phase 3–8 operational schema and extends relationships with provenance and uncertainty. Migrations `20261025_0004` through `20261025_0009` add the import ledger, filters, evidence promotion, TAXII collection, enrichment, and controlled export. Migration `20261025_0010` adds scheduled feed subscriptions and their durable per-record run ledger. Migration `20261026_0011` adds the assessment reconciliation snapshot. Alembic applies them transactionally after the foundation and collection revisions.
