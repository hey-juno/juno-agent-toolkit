# Juno Agent Toolkit

An agent skill, a small Python client, and runnable workflows for [Juno](https://www.heyjuno.co): AI-moderated customer interviews with real people.

Use Juno when product analytics, support tickets or existing research leave a question that needs customers' own explanations. Brief a study, review the interview, collect responses, and retrieve the evidence through the supported API.

**Developer preview.** This toolkit follows the published API contract. As of 9 September 2026, Juno's public documentation describes approved API-key access. [Request a key](https://www.heyjuno.co/documents/api-keys) and check the current access conditions. Self-service signup and OAuth are not implemented by this toolkit. See [validation and limitations](docs/validation.md) for what has been tested.

## Choose your interface

| Interface | Use it for | Start here |
| --- | --- | --- |
| Agent skill | Teach a skill-capable assistant how to use Juno for an authorised research task | [Juno research skill](skills/juno-research/SKILL.md) |
| Python client | Call Juno from your application or agent | [Client](juno_client/) and the quickstart below |
| MCP | Connect a compatible client to Juno's hosted tools | [MCP connection guide](docs/mcp.md) |
| Research workflow | Follow a study from a brief to participant evidence | [Workflow](docs/workflow.md) and [runnable example](examples/research_workflow.py) |

## Python quickstart

Python 3.11 or later; no third-party runtime dependencies. Clone this repository and run from its root:

```sh
git clone https://github.com/hey-juno/juno-agent-toolkit.git
cd juno-agent-toolkit
python -m examples.research_workflow --help
```

Set `JUNO_API_KEY` in your environment using your normal secret-management method. Do not put it in a source file, prompt, committed client configuration or issue report.

```python
import os
from juno_client import JunoClient

client = JunoClient(api_key=os.environ["JUNO_API_KEY"])
identity = client.me()
print(identity["org_id"], identity["scopes"])
```

When the user has authorised creating a study:

```sh
python -m examples.research_workflow draft \
  --guidance "Understand why customers abandon onboarding and what they expected instead."
```

A new study starts in Test mode. Review its brief before choosing to go live. The example separates drafting, going live, inspecting interviews and exporting results; it does not recruit or contact participants automatically.

The client covers the core study/evidence workflow, not every public API operation. The [live REST reference](https://www.heyjuno.co/documents/rest-api/reference) and [OpenAPI document](https://api.heyjuno.co/v1/api/openapi.json) define the full interface. This preview is distributed from GitHub; it has not been published to PyPI.

## What an agent can retrieve

Study and interview endpoints provide status and metadata. **Interview metadata does not contain transcripts.** For completed Live-mode interviews, use the export workflow to retrieve CSV transcripts and answers under the organisation's permissions and redaction settings. Test-mode simulations are rehearsal material and are not customer evidence.

Use the research brief, participant quotes and transcript context to explain findings. Keep uncertainty and conflicting accounts visible. Juno does not turn a small qualitative sample into population-wide prevalence or a measured causal effect.

## Public MCP, hosted service

Juno publishes a remote MCP endpoint at `https://api.heyjuno.co/v1/mcp/`. Public connection information makes it discoverable; credentials and workspace permissions control use. See the [connection guide](docs/mcp.md) for client configuration and verification status.

This repository contains client-side integration material. The hosted MCP server and Juno's research engine remain part of the Juno service. There is no second MCP server, local proxy or self-hosted Juno backend here.

## Research in practice

- [StoryTribe: finding barriers to conversion](https://www.heyjuno.co/stories/free-to-paid-with-juno)
- [OFX: mapping customer journeys](https://www.heyjuno.co/stories/ofx-digital-platform)
- [The Arthritis Movement: turning community voices into policy](https://www.heyjuno.co/stories/the-arthritis-movement)
- [Australian climate sentiment research](https://www.heyjuno.co/stories/what-australians-really-think-about-climate)

These are published customer stories, not fixtures or benchmark results for this client.

## Development

```sh
python -m unittest discover -s tests -v
```

Tests use a local HTTP server and synthetic data. They need no Juno or model API key and do not create live research. [Contract provenance](reference/README.md) explains the public schema snapshot. Please report reproducible client issues in GitHub, with credentials and research data removed; use [Juno Support](https://support.heyjuno.co) for account or private-data issues.

The toolkit is [MIT licensed](LICENSE). Access to the hosted service follows Juno's current terms and entitlements.
