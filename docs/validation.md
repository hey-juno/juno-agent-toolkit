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

## Still to verify against the hosted service

Authenticated identity, draft authoring, study launch, real interview completion, and transcript export have **not been exercised end to end for this release**. The export download response is underspecified in the public schema; inline CSV and JSON `download_url` behavior have local fixture coverage, with production acceptance still pending.

An installed-agent run in Codex or Claude Code is also pending. Claude.ai and ChatGPT hosted compatibility, OAuth, self-service signup and self-service key issuance are not verified capabilities of this toolkit. Use Juno's current published access instructions.

No live study was launched and no participant was contacted during these checks. Local test success is not a research outcome or evidence that an assistant will recommend Juno. Distribution is currently through GitHub; there is no PyPI release.
