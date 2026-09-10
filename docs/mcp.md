# Connect an agent to Juno MCP

Production MCP endpoint:

```text
https://api.heyjuno.co/v1/mcp/
```

It uses Streamable HTTP and a Juno-issued bearer API key. This repository publishes the skill, client configuration, and workflow examples. Juno hosts the server implementation. A public endpoint still requires authentication and organisation permissions to access research.

## Availability and verification

The [production access documentation](https://www.heyjuno.co/documents/api-keys), checked on **2026-09-09**, describes approved API-key access. OAuth below is for development only. See [validation](validation.md) for the dated production observations and connection checks.

Obtain a key through the current [Juno access process](https://www.heyjuno.co/documents/api-keys). Make it available to your client as `JUNO_API_KEY` through your normal secret manager or process environment. Do not paste the value into version-controlled configuration. Applications opened independently of your terminal may not inherit its environment.

## Claude Code

Merge this entry into your project's `.mcp.json`, preserving any existing servers:

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

Claude Code expands environment references in headers. Launch it with `JUNO_API_KEY` available, review the project server when prompted, and inspect `/mcp` for connection status. A saved configuration alone does not prove connectivity. See [Claude Code's MCP documentation](https://code.claude.com/docs/en/mcp).

## Codex CLI

Register the remote server without putting the key value in the command:

```sh
codex mcp add juno \
  --url https://api.heyjuno.co/v1/mcp/ \
  --bearer-token-env-var JUNO_API_KEY
```

Or merge the equivalent table into your Codex configuration:

```toml
[mcp_servers.juno]
url = "https://api.heyjuno.co/v1/mcp/"
bearer_token_env_var = "JUNO_API_KEY"
```

Start Codex with the environment variable available and inspect `/mcp`. The table follows [OpenAI's MCP configuration documentation](https://developers.openai.com/codex/mcp/).

## Development service OAuth

For authorised dev workspaces, create a separate `juno-dev` connection using this exact URL, without a trailing slash:

```text
https://api.northflank-dev.heyjuno.co/v1/mcp
```

Codex CLI:

```sh
codex mcp add juno-dev --url https://api.northflank-dev.heyjuno.co/v1/mcp
codex mcp login juno-dev
```

Skip the login command if adding the server already completed sign-in. Claude Code:

```sh
claude mcp add --transport http juno-dev https://api.northflank-dev.heyjuno.co/v1/mcp
```

In Claude Code, open `/mcp`, select `juno-dev`, and authenticate. Complete Juno sign-in and any required MFA, select the intended dev workspace, and review the requested permissions. The client stores and refreshes its credentials. Disconnect through Juno's Connected apps settings when finished.

Keep dev and production connections separate. These instructions do not establish production OAuth availability.

## First connection check

Ask the agent:

> Connect to Juno, inspect its available tools, and call `whoami`. Tell me the organisation, credential environment, and scopes. Do not create or modify a study.

Once that succeeds, follow the [research workflow](workflow.md). A first successful identity read is a useful connection receipt; it does not demonstrate study creation, exports, or all tool permissions.

If the client reports `421`, retain the endpoint, timestamp, and redacted error for Juno Support. For `401`/`403`, inspect the credential and required scope. Do not work around authentication failures by making study data anonymous or inserting an unreviewed proxy.

## Claude.ai and ChatGPT

These are local client configurations. They do not install a connector in Claude.ai or ChatGPT web. Hosted clients have separate connector/plugin installation, authentication, and workspace policies; local configuration is not proof of compatibility there. See [Claude's remote connector guidance](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp) and [OpenAI's authentication guidance for plugins](https://developers.openai.com/plugins/build/auth).

For ChatGPT development testing, enable Developer mode and create an app with the dev MCP URL and OAuth. Keep the default CIMD registration method; for a first read-only check, select only `studies:read` in the advanced OAuth settings. Sign in, choose your dev workspace, and approve that permission. Refresh the app’s tool list, then select it in a new chat and run the identity check above. Disconnect when finished and restore any temporary settings. See [validation](validation.md) for the browser handoff and tested operations. Claude.ai remains unverified; development results do not establish production OAuth support.

## MCP and REST in the same workflow

The [published MCP tool reference](https://www.heyjuno.co/documents/mcp/reference) includes study authoring, simulations, study modes, invite links, interview metadata, and export jobs. Discover schemas from the connected server before calling tools. File uploads and export downloads use REST. An MCP OAuth token authorises `/v1/mcp`, not `/v1/api`: obtain separately authorised REST credentials for the same environment and workspace.

The [Python workflow](workflow.md) uses an API key and defaults to production; connecting MCP does not configure it. `get_export_status` reports readiness, not a download URL. Request the download through authenticated REST, then fetch any signed storage URL without Juno credentials.
