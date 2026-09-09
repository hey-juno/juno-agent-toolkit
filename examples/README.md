# Research workflow

Run these commands from the repository root with Python 3.11+. The runtime uses only Python's standard library. A valid, authorised Juno key is required for live calls; this repository does not create accounts or issue keys.

Supply `JUNO_API_KEY` using your shell or secret manager. Do not put a key directly in a command line, source file, commit, or example output. The examples do not load `.env` files.

Create a study in Test mode from an actual user brief:

```sh
python -m examples.research_workflow draft \
  --guidance 'Understand why new customers stop during our onboarding. Interview customers who recently tried it about their experience and what blocked them.' \
  --idempotency-key onboarding-draft-001
```

This writes a draft study in your organisation. It prints the authoring job ID before polling so you can resume it. Keep the idempotency key for that same logical request; choose a new value for a different study. The client never retries a write automatically.

```sh
python -m examples.research_workflow status --job-id YOUR_AUTHORING_JOB_ID
```

Review the draft in Juno. Test-mode interviews are rehearsals: they are not real participant evidence and do not provide analysis or exports. The same durable link admits real interviews after Go live, so treat sharing it as a separate user decision.

Only after the user has reviewed the study and authorised real collection:

```sh
python -m examples.research_workflow go-live --study-id YOUR_STUDY_UUID --confirm
```

Going live requires the appropriate key scope and research entitlements. Real interviews can consume credits. None of these commands emails, messages, recruits, or invites anyone.

Later, read one page of an existing study's interview metadata:

```sh
python -m examples.research_workflow evidence --study-id YOUR_STUDY_UUID
```

The records include state, `is_test`, supplied invite attributes, and a link into Juno. They do **not** include transcript text. Pass a returned `next_cursor` as `--cursor` to request another page. An empty page supplies no research findings; the example never fabricates participants, quotations, or conclusions.

For an authorised export of completed real interviews, choose a new file outside this repository. Create its parent directory first:

```sh
python -m examples.research_workflow export \
  --study-id YOUR_STUDY_UUID --output /absolute/private-directory/interviews.csv
```

The export job ID is printed before polling. Resume a slow or interrupted export without creating a duplicate:

```sh
python -m examples.research_workflow export \
  --job-id YOUR_EXPORT_JOB_ID --output /absolute/private-directory/interviews.csv
```

The client accepts inline CSV or the current API's JSON `download_url` response, fetching that signed HTTPS URL with no Juno bearer token or cookies. It does not follow HTTP redirects. Signed URLs and CSV contents are excluded from logs. Files are created with owner-only permissions and never overwrite an existing path. Organisation PII-redaction settings apply on the server; exported data can still be sensitive.

`--timeout` before the subcommand changes the polling deadline. Reaching it stops local polling, not the server's job. Each network operation also has a socket timeout. Responses are buffered, with a default 64 MiB limit; use the SDK's `max_response_bytes` option for a larger authorised export.

This is an alpha example verified against a public contract snapshot and local HTTP fixtures. Authenticated end-to-end acceptance against the hosted API is still pending. See the root README for the current access and MCP status.
