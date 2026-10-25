# Iteration 1.8 — controlled STIX/TAXII export

Date: 2026-10-25

## Outcome

ThreatLens can share selected, analyst-reviewed STIX 2.1 Indicators with one explicitly allowlisted TAXII 2.1 collection. Export begins disabled, freezes the payload before review, requires approval from a different administrator, and revalidates destination write access before delivery.

## Delivered behavior

- An administrator can create an export policy only for an enabled TAXII collection that advertises `can_write`. New policies are always disabled.
- Enabling a policy requires an explicit marking-definition allowlist or an explicit decision to allow unmarked objects, plus a maximum object count.
- Only evidence with a recorded analyst reviewer and a STIX 2.1 Indicator source record can be selected. Enriched observations and unreviewed imports cannot bypass that boundary.
- Every Indicator's `object_marking_refs` must fit the destination policy. Available STIX marking-definition objects are included with the exported Indicators.
- A request freezes an immutable STIX bundle, evidence list, object count, bundle ID, and SHA-256 hash before approval.
- A different administrator must approve or reject the request with a rationale. The original requester cannot self-approve.
- Delivery rechecks that the policy remains enabled, the server remains enabled, the collection still advertises write permission, and the independent approval remains valid.
- TAXII delivery uses the fixed discovered authority and collection endpoint. Credentials stay in backend environment variables; the ledger stores only bounded receipt fields.
- Failed deliveries retain the frozen bundle and approval for controlled retry. Delivered requests cannot be replayed through the API.
- The dark/light sharing console exposes policy state, reviewed evidence eligibility, immutable hashes, independent review, delivery, errors, and receipts.

## Verification

- Backend tests cover default-disabled policies, marking allowlists, marking-definition preservation, write authorization, pre-approval delivery denial, role enforcement, independent approval, delivery, replay denial, history, and audit events.
- TAXII transport tests verify the fixed collection endpoint, 2.1 media type, backend bearer credential, and bounded receipt fields.
- Frontend service tests cover policy creation, request, resolution, and delivery contracts.
- The complete backend regression suite, Ruff, strict mypy, Angular unit suite, production build, PostgreSQL migration parity, Docker health checks, production dependency audit, and live OpenAPI inspection are required before release.

## Security boundary

The export API is the only network write path. It does not expose token values, accept arbitrary destination URLs, infer sharing permission from read access, export raw enrichment results, or treat an approval as permanent authorization if the destination later revokes write access.
