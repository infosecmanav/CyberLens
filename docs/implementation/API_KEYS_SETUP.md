# API key setup

Copy `.env.example` to `.env` and enter values locally when provider testing begins. `.env` is ignored by Git. Do not place secrets in frontend files, browser storage, source metadata, logs, tests, or documentation.

The registry records environment variable names only. Missing keys must produce `NOT_CONFIGURED`, leave other connectors operational, and remain visible in Source Health. A configured key does not by itself establish that an integration is implemented, permitted for the intended use, or successfully tested.

The Source Registry exposes an administrator-only, typed connection test for implemented connectors. It performs one explicit provider request, records only the outcome and source health, and does not persist returned intelligence. Use it after adding a key, beginning with a documentation-only or otherwise approved indicator. Live tests remain quota-bounded and must respect the provider's commercial-use and submission terms.

