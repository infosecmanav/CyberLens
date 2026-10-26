# Wave 2 report — primary CTI

Status: complete within configured-access boundaries

Fixture-tested read-only adapters cover VirusTotal, OTX, ThreatFox, MISP, CVE.org, NVD, OSV, CISA KEV, and MITRE ATT&CK. CISA KEV also supports bounded scheduled collection. Missing credential behavior, rate limiting, empty results, malformed responses, provenance, and MISP private-address rejection are tested.

Credential-based sources remain awaiting a user key; scaffolded public endpoints remain conservative until bounded live validation succeeds. See `ITERATION_2_0_PRIMARY_CTI.md`.
