# From a research question to participant evidence

This walkthrough uses Juno to investigate **why customers abandon onboarding**. Adapt the brief to the decision your team needs to make and the people who can inform it. Use the [agent skill](../skills/juno-research/SKILL.md) with a configured MCP client, or use the Python example below.

This is a preview built against the [public OpenAPI snapshot](../reference/openapi.json). Its local tests do not establish a successful authenticated production study. Current key access is described in [Juno's access documentation](https://www.heyjuno.co/documents/api-keys); the publication checked on 2026-09-09 still specifies manually issued private-beta keys. See [MCP availability and setup](mcp.md) for connection limits.

## Install the optional agent skill

Copy this repository's complete `skills/juno-research` folder into one of the following locations. Choose project scope to make it available only in the project where you will run the research. Preserve other skills; if `juno-research` already exists, review its differences before replacing it.

| Client | Project destination | Personal destination |
| --- | --- | --- |
| Codex | `.agents/skills/juno-research/` | `~/.agents/skills/juno-research/` |
| Claude Code | `.claude/skills/juno-research/` | `~/.claude/skills/juno-research/` |

These paths follow [OpenAI's local skill guidance](https://developers.openai.com/codex/skills/) and [Claude Code's skill guidance](https://code.claude.com/docs/en/skills). Open a session in the target project and select the skill: `$juno-research` in Codex, or `/juno-research` in Claude Code. The skill can also be selected when a relevant request matches its description. It needs the [MCP connection](mcp.md) or authorised REST access to perform platform actions; installing it alone does not connect Juno or grant permission to launch a study.

## Connect

Follow the [repository setup](../README.md), then make `JUNO_API_KEY` available in the process environment. The Python helper reads it without a literal credential in your script:

```python
from juno_client import JunoClient

juno = JunoClient()
identity = juno.me()
print(identity)
```

Check the returned organisation, key environment, and scopes. The key environment is separate from a study's Test or Live mode. The workflow needs permission to create/read studies and read invite links; going live requires `studies:golive`, and exporting requires `export:read`.

## Create and review a Test-mode study

From the repository root:

```sh
python -m examples.research_workflow draft --guidance \
  "Understand why new customers leave onboarding before finishing setup. Interview people who recently attempted setup. Explore what they expected, what happened, where they got stuck, and what they did next. The team will use this research to decide which onboarding changes to investigate."
```

This creates a study and waits for its authoring job. Save the returned identifiers. If the wait ends before authoring does, resume by checking that job rather than submitting another create request:

```sh
python -m examples.research_workflow status --job-id JOB_ID
```

Replace `JOB_ID` with the returned handle. A `ready` job means Juno finished authoring the brief. Review the objectives and questions with the researcher; completion is not a judgment that the design meets their needs.

In MCP, the corresponding calls are `create_study`, `get_authoring_status`, and `get_study`. Use `refine_study` for requested edits. An optional Test-mode rehearsal uses `simulate_study` followed by `get_simulation_status`; it is a synthetic conversation, not customer evidence. The lightweight Python example does not wrap every MCP operation.

## Go live when authorised

After the researcher has reviewed the study and authorised real participant research:

```sh
python -m examples.research_workflow go-live --study-id STUDY_ID --confirm
```

Replace `STUDY_ID` with the created study's ID. Live interviews use credits and can generate research data for analysis and exports. The command's explicit confirmation keeps this distinct from the draft example. Existing user authorization to launch is sufficient; the agent need not ask for it twice.

The returned durable interview link is for the researcher to distribute. A Test-mode link is a preview; going live makes the same study link admit real participants. This example does not send invitations or recruit people. Any participant contact remains within the user's authorised channels and audience.

## Read collection progress and retrieve research

Inspect completed interview records:

```sh
python -m examples.research_workflow evidence --study-id STUDY_ID
```

Interview list/detail responses contain state, timing, invite-link context, and a permalink into Juno. **They do not contain transcripts.** `is_test` distinguishes rehearsals from real participant research; the example should not treat simulated material as customer feedback.

When exporting that study's research is authorised, request the CSV explicitly:

```sh
python -m examples.research_workflow export --study-id STUDY_ID --output /path/outside/repo/results.csv
```

The export job covers completed Live-mode interviews and applies the organisation's PII-redaction settings. Keep downloaded research and any signed download URLs private. Replace the output path with a private location outside this checkout. The service can return inline CSV or a signed HTTPS download URL. Fetching that URL is a separate request that must not carry the Juno bearer key; the example handles this separation. The public OpenAPI download schema is currently underspecified, so its schema alone cannot validate the file response.

For custom code, the corresponding client operations are:

| Task | Python helper | MCP tool |
| --- | --- | --- |
| Check identity | `me()` | `whoami` |
| Create study | `create_study(guidance)` | `create_study` |
| Check authoring | `get_authoring_job(job_id)` / `wait_for_authoring(job_id)` | `get_authoring_status` |
| Read study | `get_study(study_id)` | `get_study` |
| Launch real collection | `set_study_mode(study_id, "live")` | `set_study_mode` |
| Get participant invite | `get_interview_link(study_id)` | `get_interview_link` |
| List interview metadata | `list_interviews(study_id=study_id)` | `list_interviews` |
| Start CSV export | `create_export(study_id)` | `start_export` |
| Check export | `get_export(job_id)` / `wait_for_export(job_id)` | `get_export_status` |
| Inspect export download response | `get_export_download(job_id)` | REST download endpoint |
| Retrieve CSV bytes | `download_export(job_id)` | REST download endpoint; then signed URL when supplied |

List helpers return a `Page` with `items` and `next_cursor`. Continue with that cursor until there is no next page. Save job handles before waiting; the client does not automatically retry writes. A failed or uncertain request is a reason to inspect the job or existing study before starting another one.

## Bring the findings back to the decision

Use retrieved participant evidence to explain what happened during onboarding and what the team could investigate next. Preserve the distinction between quotes, observations, and your interpretation. Attribute evidence to its source records when available, include contradictory accounts, and explain material gaps. A number of completed interviews is context for the researcher's judgment, not an automatic verdict about sufficiency.

For response fields and endpoint changes, use the [live REST reference](https://www.heyjuno.co/documents/rest-api/reference) and [MCP reference](https://www.heyjuno.co/documents/mcp/reference).
