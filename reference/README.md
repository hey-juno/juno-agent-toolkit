# Public API contract snapshot

`openapi.json` was fetched without authentication from:

https://api.heyjuno.co/v1/api/openapi.json

Captured: 9 September 2026. API information version: `1.0.0`.

SHA-256: `e2cebcc0b43b977dc13a6c81e8e7039e62a1f3ee39ce4481d2e426f023a14610`.

The live OpenAPI document is the canonical interface. This unmodified snapshot makes the client's tests and initial implementation reviewable; it is not a separately maintained API definition. When updating it, fetch the published document, review the diff and record its capture date and checksum here. Do not hand-edit schemas to make tests pass.

The current download operation's response schema is underspecified. Its documentation permits a signed download URL or inline CSV; the client supports the service's `download_url` JSON field and inline CSV while keeping Juno credentials out of storage requests. Authenticated production acceptance remains a separate check, as recorded in [validation](../docs/validation.md).
