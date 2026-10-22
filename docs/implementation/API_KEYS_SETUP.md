# API key setup

Copy `.env.example` to `.env` and enter values locally when provider testing begins. `.env` is ignored by Git. Do not place secrets in frontend files, browser storage, source metadata, logs, tests, or documentation.

The registry records environment variable names only. Missing keys must produce `NOT_CONFIGURED`, leave other connectors operational, and remain visible in Source Health. A configured key does not by itself establish that an integration is implemented, permitted for the intended use, or successfully tested.

Phase 2 will verify each provider's current authentication scheme and replace provisional variable names where official documentation requires it. Live tests will be explicit and quota-bounded.

