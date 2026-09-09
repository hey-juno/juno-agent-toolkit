"""Exercise example side effects against the same local HTTP fixtures."""

import contextlib
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from examples.research_workflow import main, output_path
from test_client import STUDY_ID, client, server


class WorkflowTests(unittest.TestCase):
    def invoke(self, args, url):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("examples.research_workflow.JunoClient", side_effect=lambda **_kwargs: client(url)):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = main(args)
        return status, stdout.getvalue(), stderr.getvalue()

    def test_draft_returns_study_without_going_live_or_sending_invitations(self):
        with server([
            (202, {}, {"job_id": "job-one"}),
            (200, {}, {"status": "ready", "study_id": STUDY_ID}),
            (200, {}, {"id": STUDY_ID, "mode": "test"}),
            (200, {}, {"url": "https://example.test/invite", "mode": "test"}),
        ]) as (url, calls):
            status, stdout, stderr = self.invoke(["draft", "--guidance", "Research our onboarding"], url)
        self.assertEqual(status, 0, stderr)
        self.assertIn("job-one", stdout)
        self.assertEqual(sum(c[0] != "GET" for c in calls), 1)
        self.assertEqual(calls[0][:2], ("POST", "/v1/api/studies"))

    def test_export_resume_writes_owner_only_file_without_new_export(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "research.csv"
            with server([
                (200, {}, {"status": "completed", "ready": True}),
                (200, {"Content-Type": "text/csv"}, b"id,answer\nexample,fabricated\n"),
            ]) as (url, calls):
                status, stdout, stderr = self.invoke([
                    "export", "--job-id", "existing-export", "--output", str(destination),
                ], url)
            self.assertEqual(status, 0, stderr)
            self.assertTrue(destination.read_bytes().startswith(b"id,answer"))
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertTrue(all(c[0] == "GET" for c in calls))
            self.assertNotIn("fabricated", stdout)

    def test_export_will_not_overwrite_or_write_inside_checkout(self):
        checkout = Path(__file__).parents[1]
        with self.assertRaises(ValueError):
            output_path(str(checkout / "participant-data.csv"))
        with tempfile.NamedTemporaryFile() as existing:
            with server([]) as (url, calls):
                status, _stdout, stderr = self.invoke([
                    "export", "--study-id", STUDY_ID, "--output", existing.name,
                ], url)
            self.assertEqual(status, 1)
            self.assertIn("already exists", stderr)
            self.assertEqual(calls, [])

    def test_invalid_polling_deadline_does_not_create_draft(self):
        with server([]) as (url, calls):
            status, _stdout, stderr = self.invoke(["--timeout", "-1", "draft", "--guidance", "brief"], url)
        self.assertEqual(status, 1)
        self.assertIn("positive finite", stderr)
        self.assertEqual(calls, [])

    def test_go_live_requires_explicit_confirmation(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            main(["go-live", "--study-id", STUDY_ID])
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
