"""Create a draft, inspect evidence, and export only on explicit user commands."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

from juno_client import JunoClient, JunoError, PollTimeout


def show(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


def output_path(value: str) -> Path:
    """Keep participant data outside the public source checkout; never overwrite."""
    path = Path(value).expanduser().resolve()
    checkout = Path(__file__).resolve().parents[1]
    if path == checkout or checkout in path.parents:
        raise ValueError("Choose an export output path outside this repository")
    if path.exists():
        raise ValueError("Export output already exists; choose a new path")
    if not path.parent.is_dir():
        raise ValueError("Create the chosen output directory before requesting an export")
    return path


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__, epilog=(
        "Requires JUNO_API_KEY. Creating a draft writes to your Juno organisation. "
        "Going live is a separate explicit command. This example never contacts participants. "
        "Run from the repository root with Python 3.11+."
    ))
    result.add_argument("--base-url", default="https://api.heyjuno.co/v1/api", help="HTTPS API base including /v1/api")
    result.add_argument("--timeout", type=float, default=300, help="Job polling deadline in seconds (default: 300)")
    commands = result.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="Create a Test-mode study from a user brief; wait and show its draft")
    draft.add_argument("--guidance", required=True, help="User's research goal, audience, and what they want to learn")
    draft.add_argument("--idempotency-key", help="Caller-chosen key for this create request; no automatic retries")
    status = commands.add_parser("status", help="Resume polling an existing authoring job; does not create another study")
    status.add_argument("--job-id", required=True)
    live = commands.add_parser("go-live", help="Explicitly admit real participant interviews, which can consume credits")
    live.add_argument("--study-id", required=True)
    live.add_argument("--confirm", action="store_true", required=True,
                      help="Confirm the user reviewed the study and authorised Go live")
    evidence = commands.add_parser("evidence", help="Read one page of interview metadata; no transcripts or invented results")
    evidence.add_argument("--study-id", required=True)
    evidence.add_argument("--limit", type=int, default=50)
    evidence.add_argument("--cursor", help="Opaque cursor from the previous page")
    export = commands.add_parser("export", help="Explicitly export real interview transcripts into a file outside this checkout")
    source = export.add_mutually_exclusive_group(required=True)
    source.add_argument("--study-id", help="Start a new export for this existing study")
    source.add_argument("--job-id", help="Resume an existing export job without starting another")
    export.add_argument("--output", required=True, help="New CSV file outside this repository (parent directory must exist)")
    return result


def show_draft(api: JunoClient, job_id: str, timeout: float):
    result = api.wait_for_authoring(job_id, timeout=timeout)
    study_id = result.get("study_id")
    if not study_id:
        raise ValueError("Authoring says ready but supplied no study_id; inspect the job before continuing")
    show({"authoring_job_id": job_id, "study": api.get_study(study_id),
          "invite_link": api.get_interview_link(study_id)})
    print("Review this study in Juno. The durable invite link follows the study's mode when opened.")
    print("No invitations were sent. Go live is a separate action and permits real interviews and credit use.")


def run(args):
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise ValueError("--timeout must be a positive finite number")
    # Validate export location before creating any remote work.
    destination = output_path(args.output) if args.command == "export" else None
    api = JunoClient(base_url=args.base_url)
    if args.command == "draft":
        job = api.create_study(args.guidance, idempotency_key=args.idempotency_key)
        print(f"Authoring job: {job['job_id']}", flush=True)
        show_draft(api, job["job_id"], args.timeout)
    elif args.command == "status":
        show_draft(api, args.job_id, args.timeout)
    elif args.command == "go-live":
        show(api.set_study_mode(args.study_id, "live"))
        print("Go live was requested explicitly. No invitations were sent.")
    elif args.command == "evidence":
        study = api.get_study(args.study_id)
        page = api.list_interviews(study_id=args.study_id, limit=args.limit, cursor=args.cursor)
        show({"study_id": study["id"], "mode": study.get("mode"),
              "interviews": page.items, "next_cursor": page.next_cursor})
        print("These are metadata records, not transcripts. is_test identifies rehearsals; preserve that distinction.")
        if not page.items:
            print("This page contains no interviews. No research conclusions can be drawn from an empty page.")
    elif args.command == "export":
        job_id = args.job_id
        if job_id is None:
            job_id = api.create_export(args.study_id)["job_id"]
        print(f"Export job: {job_id}", flush=True)
        api.wait_for_export(job_id, timeout=args.timeout)
        download = api.download_export(job_id)
        # No participant records or signed URLs are printed; the file is owner-readable.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(download.body)
        print(f"Saved CSV to {destination}")
        print("Handle this participant data under your organisation's research and access policies.")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        run(args)
    except PollTimeout as exc:
        print(f"{exc} Job ID: {exc.job_id}", file=sys.stderr)
        return 2
    except (JunoError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
