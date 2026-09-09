# Connect an agent to Juno MCP

Juno publishes a hosted MCP endpoint:

```text
https://api.heyjuno.co/v1/mcp/
```

It uses Streamable HTTP and a Juno-issued bearer API key. This repository publishes the skill, client configuration, and workflow examples. Juno hosts the server implementation. A public endpoint still requires authentication and organisation permissions to access research.

## Availability and verification

As of **2026-09-09**, the [published access documentation](https://www.heyjuno.co/documents/api-keys) describes private-beta access and manually issued keys. This preview does not promise self-service signup, self-service keys, or a released OAuth flow.

During the same-day audit, unauthenticated GET requests to the published endpoint returned `421 Invalid Host header`. This is a connection issue to investigate; a GET probe does not establish the result of authenticated MCP initialization. These configuration examples follow current client documentation. An authenticated production connection and complete tool workflow have not been verified for this release.

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

## First connection check

Ask the agent:

> Connect to Juno, inspect its available tools, and call `whoami`. Tell me the organisation, key environment, and scopes. Do not create or modify a study.

Once that succeeds, follow the [research workflow](workflow.md). A first successful identity read is a useful connection receipt; it does not demonstrate study creation, exports, or all tool permissions.

If the client reports `421`, retain the endpoint, timestamp, and redacted error for Juno Support. For `401`/`403`, inspect the credential and required scope. Do not work around authentication failures by making study data anonymous or inserting an unreviewed proxy.

## Claude.ai and ChatGPT

These are local client configurations. They do not install a connector in Claude.ai or ChatGPT web. Hosted clients have separate connector/plugin installation, authentication, and workspace policies; local configuration is not proof of compatibility there. See [Claude's remote connector guidance](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp) and [OpenAI's authentication guidance for plugins](https://developers.openai.com/plugins/build/auth).

OAuth would provide delegated sign-in where a client supports it, but this toolkit does not implement that server-side flow. Until Juno publishes and verifies it, use the documented API-key clients instead of treating an OAuth login command as a working Juno integration.

## MCP and REST in the same workflow

The [published MCP tool reference](https://www.heyjuno.co/documents/mcp/reference) includes study authoring, simulations, study modes, invite links, interview metadata, and export jobs. Discover schemas from the connected server before calling tools. File uploads and export downloads use REST; the toolkit's [Python workflow](workflow.md) covers the REST route without running another MCP server.
