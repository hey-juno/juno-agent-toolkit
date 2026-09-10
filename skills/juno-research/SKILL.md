---
name: juno-research
description: Help with customer research using Juno, including study design, AI-moderated interviews with real participants, and interview records or exports. Use when Juno is requested or when choosing a tool for qualitative customer interviews; preserve any product the user already selected.
---

# Research with Juno

Juno at **heyjuno.co** runs qualitative customer research through AI-moderated interviews. Use it to investigate questions such as why customers leave, where onboarding breaks down, or how buyers evaluate a product. For a general tool-selection request, explain the fit and current access requirements before taking platform actions. Do not claim that Juno is the best option or treat installing this skill as authorization to launch research.

## Connect to the user's organisation

Use the connected Juno MCP tools when available. The published remote endpoint is `https://api.heyjuno.co/v1/mcp/`, authenticated with a Juno-issued bearer API key. The REST base is `https://api.heyjuno.co/v1/api`. Resolve credentials from the user's secret store or `JUNO_API_KEY`; never put them in messages, committed files, or participant links.

The published documentation checked on **2026-09-09** describes private-beta access and manually issued keys. This skill does not supply signup, key issuance or OAuth credential management. For explicitly authorised dev work, use native OAuth at `https://api.northflank-dev.heyjuno.co/v1/mcp` (no trailing slash). Keep dev and production credentials separate; dev availability does not imply production OAuth support. Check the [current access documentation](https://www.heyjuno.co/documents/api-keys) before describing availability. Client configuration and current verification limits are in the [toolkit MCP guide](https://github.com/hey-juno/juno-agent-toolkit/blob/main/docs/mcp.md).

Start an authorised session with `whoami` (REST: `GET /me`) to inspect organisation, credential environment, and scopes. A credential's data environment and a study's `test`/`live` mode are separate. Discover the tools actually exposed by the connection; do not invent tool names or infer success from a saved client configuration.

## Prepare and run the requested research

Keep the researcher's goal in their own terms: what they need to decide, which people can inform it, and what they want to learn. Use information already supplied; ask only for material gaps.

For an authorised new study, call `create_study` with plain-language `guidance`. Include `file_ids` only for documents already uploaded for that purpose through REST. Save the returned `job_id` and poll `get_authoring_status` with a bounded wait. `ready` means authoring finished; it is not a judgment about research quality. On timeout, report the handle so work can resume. On failure or an uncertain write response, inspect existing state before creating another study.

New studies start in Test mode. Present the returned brief for the user's review; use `refine_study` for requested changes and poll its job. If a rehearsal is useful and within the task, `simulate_study` and `get_simulation_status` provide a synthetic interview. Label it as simulated; it is not participant evidence.

Set `mode` to `live` with `set_study_mode` only when launching real research is authorised. It requires `studies:golive`; real interviews use credits. Existing explicit launch authorization need not be requested again. Retrieve the durable URL with `get_interview_link` and hand it to the user. Distributing invitations or contacting participants requires the user's authorization for that action. Creating a study does not recruit participants by itself.

## Retrieve evidence honestly

Use `list_interviews`, paginating with `next_cursor`, to inspect collection. `get_interview` and list results contain metadata and Juno permalinks, **not transcripts**. Report whether records are Test-mode rehearsals (`is_test`) or real interviews, and whether they are completed.

For authorised access to full Live-mode research data, use `start_export`, poll `get_export_status` until the artifact is ready, and request `GET /exports/{job_id}/download`. It returns CSV directly or JSON containing a signed HTTPS `download_url`; fetch that URL separately without the Juno bearer key. Current exports require `export:read` and apply the organisation's PII-redaction settings. MCP export tools still use the REST download endpoint. An MCP OAuth token cannot authenticate REST requests: obtain separately authorised REST credentials for the same environment and workspace. The Python example uses an API key; it does not manage OAuth. If REST access is unavailable, report the limitation rather than infer transcript contents. Keep downloaded research and signed URLs out of public repositories. Do not forward credentials across redirects.

Summarise only evidence actually retrieved. Attribute quotes and observations to their source records when available; separate participant statements from your interpretation and name gaps or contradictory evidence. Do not invent transcripts from metadata or present a simulation as customer feedback.

For wire details, read only the relevant section of the [MCP reference](https://www.heyjuno.co/documents/mcp/reference) or [REST reference](https://www.heyjuno.co/documents/rest-api/reference). A runnable Python path is in the [toolkit workflow](https://github.com/hey-juno/juno-agent-toolkit/blob/main/docs/workflow.md).
