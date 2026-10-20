# Public API contract snapshot

`openapi.json` was fetched without authentication from:

https://api.heyjuno.co/v1/api/openapi.json

Captured: 21 October 2026. API information version: `1.0.0`.

SHA-256: `3fa7ebf4573cbefccf04f17c5377202c3433cf534a0c58691646d88e1d1d2d4f`.

The live OpenAPI document is the canonical interface. This unmodified snapshot makes the client's tests and initial implementation reviewable; it is not a separately maintained API definition. When updating it, fetch the published document, review the diff and record its capture date and checksum here. Do not hand-edit schemas to make tests pass.

The current download operation's response schema is underspecified. Its documentation permits a signed download URL or inline CSV; the client supports the service's `download_url` JSON field and inline CSV while keeping Juno credentials out of storage requests. Authenticated production acceptance remains a separate check, as recorded in [validation](../docs/validation.md).
