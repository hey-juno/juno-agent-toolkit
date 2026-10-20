# Connect an agent to Juno MCP

Production MCP endpoint:

```text
https://api.heyjuno.co/v1/mcp/
```

Official MCP Registry name: `io.github.hey-juno/juno` ([`server.json`](../server.json)).

It uses Streamable HTTP and accepts either **OAuth 2.1** (RFC 8414 discovery, RFC 9728 protected resource metadata, dynamic client registration, and PKCE S256) or a Juno-issued bearer **API key** (`jsk_live_…` / `jsk_test_…`). This repository publishes the skill, client configuration, and workflow examples. Juno hosts the server implementation. A public endpoint still requires authentication and organisation permissions to access research.

## Availability and credentials

Production serves both self-service [API keys](https://www.heyjuno.co/documents/api-keys) (created in the Juno app or over the programmatic account access API at `https://api.heyjuno.co/v1/access/openapi.json`) and [OAuth 2.1](https://www.heyjuno.co/documents/oauth) (`https://api.heyjuno.co/.well-known/oauth-authorization-server`). See [validation](validation.md) for the dated observations and connection checks.

When using an API key, make it available to your client as `JUNO_API_KEY` through your normal secret manager or process environment. Do not paste the value into version-controlled configuration. Applications opened independently of your terminal may not inherit its environment.

## Claude Code

Connect with OAuth 2.1 (Claude Code reads the 401 challenge, registers dynamically, and opens Juno's consent screen):

```sh
claude mcp add --transport http juno https://api.heyjuno.co/v1/mcp/
```

Or merge a bearer-key entry into your project's `.mcp.json`, preserving any existing servers:

```json
{
  "mcpServers": {
    "juno": {
      "type": "http",
      "url": "https://api.heyjuno.co/v1/mcp/",
      "headers": {
        "Authorization": "Bearer ${JUNO_API_KEY}"
      }
    }
  }
}
```

Claude Code expands environment references in headers. Launch it with `JUNO_API_KEY` available (or complete OAuth sign-in via `/mcp`), review the project server when prompted, and inspect `/mcp` for connection status. A saved configuration alone does not prove connectivity. See [Claude Code's MCP documentation](https://code.claude.com/docs/en/mcp).

## Codex CLI

Register the remote server with an API key from your environment:

```sh
codex mcp add juno \
  --url https://api.heyjuno.co/v1/mcp/ \
  --bearer-token-env-var JUNO_API_KEY
```

Or merge the equivalent table into `~/.codex/config.toml`:

```toml
[mcp_servers.juno]
url = "https://api.heyjuno.co/v1/mcp/"
bearer_token_env_var = "JUNO_API_KEY"
```

Or connect Codex with OAuth 2.1:

```sh
codex mcp add juno --url https://api.heyjuno.co/v1/mcp/
codex mcp login juno
```

Start Codex and inspect `/mcp`. The table follows [OpenAI's MCP configuration documentation](https://developers.openai.com/codex/mcp/).

## Development service OAuth

For authorised dev workspaces, create a separate `juno-dev` connection using:

```text
https://api.northflank-dev.heyjuno.co/v1/mcp
```

Codex CLI:

```sh
codex mcp add juno-dev --url https://api.northflank-dev.heyjuno.co/v1/mcp
codex mcp login juno-dev
```

Claude Code:

```sh
claude mcp add --transport http juno-dev https://api.northflank-dev.heyjuno.co/v1/mcp
```

Keep dev and production connections separate. Disconnect through Juno's Connected apps settings when finished.

## First connection check

Ask the agent:

> Connect to Juno, inspect its available tools, and call `whoami`. Tell me the organisation, credential environment, and scopes. Do not create or modify a study.

Once that succeeds, follow the [research workflow](workflow.md). A first successful identity read is a useful connection receipt; it does not demonstrate study creation, exports, or all tool permissions.

For `401`/`403`, inspect the credential and required scope. Do not work around authentication failures by making study data anonymous or inserting an unreviewed proxy.

## Hosted MCP tools (15 tools)

| Tool | Required scope | Purpose |
| --- | --- | --- |
| `whoami` | Any valid credential | Verify the presented API key or OAuth token, organisation, environment, and scopes |
| `create_study` | `studies:write` | Brief Juno in plain language to draft a new study in Test mode |
| `refine_study` | `studies:write` | Update an existing study with further instructions |
| `get_authoring_status` | `studies:read` | Poll a `create_study` or `refine_study` job until `status == "ready"` |
| `simulate_study` | `studies:write` | Run a synthetic Test-mode interview rehearsal |
| `get_simulation_status` | `studies:read` | Poll a simulation job and read its sample transcript turn by turn |
| `set_study_mode` | `studies:write` (`studies:golive` for `live`) | Set study mode (`test`, `live`, `paused`, `closed`) |
| `get_interview_link` | `links:read` | Retrieve the study's durable participant invite URL |
| `create_participant_link` | `links:write` | Mint a group or per-person invite link carrying CRM context and interviewer notes |
| `list_studies` | `studies:read` | List studies in the organisation with cursor pagination |
| `get_study` | `studies:read` | Fetch one study and its authored brief |
| `list_interviews` | `export:read` | List participant interviews by `study_id` and `status` with cursor pagination |
| `get_interview` | `export:read` | Fetch metadata and permalink for one interview |
| `start_export` | `export:read` | Start a PII-redacted CSV transcript export for completed Live-mode interviews |
| `get_export_status` | `export:read` | Poll an export job until `ready == true` (download via REST `GET /v1/api/exports/{job_id}/download`) |

## Claude.ai and ChatGPT

Local CLI configurations do not automatically install a connector in Claude.ai or ChatGPT web. Hosted clients have separate connector/app installation, OAuth authentication, and workspace policies. See [Claude's remote connector guidance](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp) and [OpenAI's MCP guidance](https://developers.openai.com/codex/mcp/).

## MCP and REST in the same workflow

The [published MCP tool reference](https://www.heyjuno.co/documents/mcp/reference) includes study authoring, simulations, study modes, invite links, participant links with context, interview metadata, and export jobs. Discover schemas from the connected server before calling tools. File uploads (`POST /v1/api/files`) and export downloads (`GET /v1/api/exports/{job_id}/download`) use REST. An MCP OAuth token is bound to `/v1/mcp`, not `/v1/api`: obtain a REST-scoped token or API key for the same environment and workspace when calling REST endpoints.
