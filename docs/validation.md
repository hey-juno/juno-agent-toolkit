# Developer preview validation

Checked on **9 September 2026** for toolkit version `0.1.0a1`.

## What passed

- All 21 tests passed on Python 3.11 and 3.12, using real local HTTP servers and fabricated records. No account, model API key or participant data was needed.
- Tests cover request paths and bodies, cursor pagination, authoring/export polling, failure and timeout handling, explicit launch, resumable exports, and private output files that cannot overwrite an existing file.
- Credential tests verify that storage requests receive no Juno bearer token or cookies, redirects are not followed automatically, and errors do not disclose credentials or signed URLs.
- The client operations were checked against the unmodified [public OpenAPI snapshot](../reference/README.md). This establishes agreement with the published contract, not every behavior of the deployed service.
- The skill's structure and the documentation's configuration snippets passed local validation. Client configuration follows the official documentation linked in the [MCP guide](mcp.md).
- Source and wheel builds passed. The installed wheel imported successfully in an isolated Python 3.13 environment with no runtime dependencies; the source archive includes the workflow, skill, documentation, public schema and tests.
- All 19 local Markdown links resolved. A credential scan and manual review found no real secrets; the scanner's single finding was a synthetic `user:pass` URL used to test rejection of embedded credentials.
- An independent review found no blocking issue in the client, skill, workflow or public contract snapshot.

Run the tests from the repository root:

```sh
python -m unittest discover -s tests -v
python -m examples.research_workflow --help
```

The repository's GitHub Actions workflow runs those checks on Python 3.11 and 3.13. Its recorded run is the source for CI status.

## What the public probes showed

These requests used no credentials:

| Endpoint | Observation |
| --- | --- |
| `https://api.heyjuno.co/v1/api/openapi.json` | HTTP 200; public contract retrieved |
| `https://api.heyjuno.co/v1/api/me` | HTTP 401; identity requires authentication |
| `https://api.heyjuno.co/v1/mcp/` | An unauthenticated GET returned HTTP 421, `Invalid Host header` |

The MCP result is a connection issue to investigate. It does not establish the result of an authenticated protocol initialization. Saving a client configuration does not prove a working connection.

## Development OAuth checks

Verified on **2026-09-10** at `https://api.northflank-dev.heyjuno.co`, revision `9e9e2ce3dcca36d9f34c2971857624dc386c911b`. These checks used only `studies:read` in an authorised dev workspace.

| Client or flow | Verified result |
| --- | --- |
| Codex CLI 0.149.1 | Native OAuth, 15 tools, `whoami` and `list_studies` through its model-free app-server interface; not a normal model turn. |
| Claude Code 2.1.266 | Native OAuth and a normal model turn calling `whoami` and `list_studies`. |
| ChatGPT hosted, DCR | OAuth, 15 tools and actual `whoami` and `list_studies` calls. |
| REST OAuth | Browser consent, PKCE exchange and refresh rotation; revocation rejected further access and renewal. |
| API-key compatibility | REST identity and MCP discovery/reads; revocation rejected both. |

The test connections were revoked after use. Discovery metadata, bearer challenges and browser-origin handling also passed. The dev workspace did not require MFA; this run does not verify deployed MFA enrollment or reauthentication.

Follow-up dev release: **2026-09-10**, revision `7494c252f0e16bb8bab0cec8c504fe111b83564e`.

- Default ChatGPT OAuth (CIMD): Consent, 15-tool discovery, and actual `whoami` plus `list_studies(limit=1)` calls passed with only `studies:read`. The identity response confirmed `https://chatgpt.com/oauth/client.json` as the client. After Juno disconnect, the exact grant was inactive with reason `user_disconnected`, and ChatGPT required reconnection before another call.
- Refreshed tool labels: ChatGPT shows eight tools as reads; the link helper remains a write. Those nine tools no longer carry destructive or open-world labels.

The automated browser’s popup handoff stalled before consent. The test continued by opening the exact authorization URL returned by ChatGPT in a new tab; Juno consent and the return to ChatGPT then completed normally. This verifies the OAuth and tool flow, not an uninterrupted popup experience in every browser.

The [OpenAPI snapshot](../reference/README.md) remains the production contract captured on 9 September; it has not been replaced with a dev schema.

## Remaining verification

Production OAuth, authenticated production client access, Claude.ai, and a complete research workflow remain unverified. Study authoring, launch, real interview completion and transcript export were not exercised end to end in these checks. The export response has local fixture coverage; authenticated production acceptance remains pending.

The toolkit does not implement self-service signup, key issuance or OAuth credential management. Follow Juno's published production access instructions.

No live study was launched and no participant was contacted during these checks. Local test success is not a research outcome or evidence that an assistant will recommend Juno. Distribution is currently through GitHub; there is no PyPI release.
