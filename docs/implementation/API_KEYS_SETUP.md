# API key setup

Copy `.env.example` to `.env` and enter values locally when provider testing begins. `.env` is ignored by Git. Do not place secrets in frontend files, browser storage, source metadata, logs, tests, or documentation.

The registry records environment variable names only. Missing keys must produce `NOT_CONFIGURED`, leave other connectors operational, and remain visible in Source Health. A configured key does not by itself establish that an integration is implemented, permitted for the intended use, or successfully tested.

The Source Registry exposes an administrator-only, typed connection test for implemented connectors. It performs one explicit provider request, records only the outcome and source health, and does not persist returned intelligence. Use it after adding a key, beginning with a documentation-only or otherwise approved indicator. Live tests remain quota-bounded and must respect the provider's commercial-use and submission terms.

ThreatFox, URLhaus, and MalwareBazaar use the shared `ABUSECH_AUTH_KEY`. MalwareBazaar is metadata-only; ThreatLens never downloads or executes samples. VirusTotal and urlscan submission endpoints are not implemented. Google Safe Browsing is marked terms-restricted because its documented API is for non-commercial use; selecting a permitted commercial service remains an owner decision.

OpenPhish, Feodo Tracker, CISA KEV, MITRE ATT&CK, CVE.org, NVD, OSV, crt.sh, and RDAP do not require application credentials for the implemented read-only path, but provider policy, network access, and rate limits still apply. Their routine tests use local fixtures.

