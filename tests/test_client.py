"""Wire-level tests use a real local HTTP server and fabricated records only."""

import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from juno_client import APIError, JunoClient, JobFailed, PollTimeout, ProtocolError


STUDY_ID = "11111111-1111-4111-8111-111111111111"
INTERVIEW_ID = "22222222-2222-4222-8222-222222222222"
KEY = "local-test-credential"


@contextmanager
def server(responses):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request()

        def do_PUT(self):
            self.handle_request()

        def handle_request(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.append((self.command, self.path, dict(self.headers), body))
            status, headers, payload = responses.pop(0)
            if not isinstance(payload, bytes):
                payload = json.dumps(payload).encode()
                headers = {"Content-Type": "application/json", **headers}
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{httpd.server_port}/v1/api"
    try:
        yield url, requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def client(url):
    return JunoClient(KEY, base_url=url, allow_insecure_localhost=True)


class ClientTests(unittest.TestCase):
    def test_draft_poll_and_link_wire_contract(self):
        responses = [
            (202, {}, {"job_id": "job:one", "thread_id": STUDY_ID}),
            (200, {}, {"status": "working"}),
            (200, {}, {"status": "ready", "study_id": STUDY_ID, "brief": {}}),
            (200, {}, {"id": STUDY_ID, "mode": "test"}),
            (200, {}, {"url": "https://example.test/invite", "mode": "test"}),
        ]
        with server(responses) as (url, calls):
            api = client(url)
            accepted = api.create_study("Learn why onboarding is difficult.", idempotency_key="draft-one")
            ready = api.wait_for_authoring(accepted["job_id"], timeout=1, poll_interval=0.001)
            self.assertEqual(ready["study_id"], STUDY_ID)
            api.get_study(STUDY_ID)
            api.get_interview_link(STUDY_ID)
        self.assertEqual([c[:2] for c in calls], [
            ("POST", "/v1/api/studies"),
            ("GET", "/v1/api/studies/jobs/job%3Aone"),
            ("GET", "/v1/api/studies/jobs/job%3Aone"),
            ("GET", f"/v1/api/studies/{STUDY_ID}"),
            ("GET", f"/v1/api/studies/{STUDY_ID}/interview-link"),
        ])
        self.assertEqual(json.loads(calls[0][3]), {"guidance": "Learn why onboarding is difficult."})
        self.assertEqual(calls[0][2]["Idempotency-Key"], "draft-one")
        self.assertTrue(all(c[2]["Authorization"] == f"Bearer {KEY}" for c in calls))

    def test_page_cursor_round_trip_and_metadata(self):
        with server([
            (200, {"X-Next-Cursor": "opaque+/="}, [{"id": INTERVIEW_ID, "is_test": False}]),
            (200, {}, []),
            (200, {}, {"id": INTERVIEW_ID, "permalink": "https://example.test/interview"}),
        ]) as (url, calls):
            api = client(url)
            page = api.list_interviews(study_id=STUDY_ID, status="completed", limit=2)
            self.assertEqual(page.items[0]["id"], INTERVIEW_ID)
            self.assertEqual(page.next_cursor, "opaque+/=")
            last = api.list_interviews(study_id=STUDY_ID, cursor=page.next_cursor, limit=2)
            self.assertIsNone(last.next_cursor)
            api.get_interview(INTERVIEW_ID)
        self.assertIn("cursor=opaque%2B%2F%3D", calls[1][1])
        self.assertEqual(calls[2][1], f"/v1/api/interviews/{INTERVIEW_ID}")

    def test_server_error_redacts_credentials_and_does_not_retry_writes(self):
        payload = {"detail": f"Rejected Bearer {KEY}; jsk_live_unrelatedsecret", "input": KEY}
        with server([(429, {"Retry-After": "30", "X-Request-ID": "req-one"}, payload)]) as (url, calls):
            with self.assertRaises(APIError) as caught:
                client(url).create_study("A brief")
        self.assertEqual(len(calls), 1)
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(caught.exception.request_id, "req-one")
        self.assertEqual(caught.exception.retry_after, "30")
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn("jsk_live_unrelatedsecret", str(caught.exception))

    def test_redirect_never_receives_bearer(self):
        with server([(200, {}, {"should": "not be called"})]) as (other_url, other_calls):
            with server([(302, {"Location": other_url + "/me"}, b"")]) as (url, calls):
                with self.assertRaises(APIError) as caught:
                    client(url).me()
            self.assertEqual(caught.exception.status, 302)
            self.assertEqual(len(calls), 1)
            self.assertEqual(other_calls, [])

    def test_download_redirect_is_returned_without_fetching(self):
        with server([(307, {"Location": "https://storage.example.test/file?signature=secret"}, b"")]) as (url, calls):
            download = client(url).get_export_download("export:one")
        self.assertEqual(download.location, "https://storage.example.test/file?signature=secret")
        self.assertEqual(download.body, b"")
        self.assertNotIn("signature", repr(download))
        self.assertEqual(calls[0][1], "/v1/api/exports/export%3Aone/download")

    def test_export_job_poll_and_inline_csv(self):
        with server([
            (202, {}, {"job_id": "export:one"}),
            (200, {}, {"status": "running", "ready": False}),
            (200, {}, {"status": "completed", "ready": True}),
            (200, {"Content-Type": "text/csv"}, b"interview_id,answer\nexample,fabricated\n"),
        ]) as (url, calls):
            api = client(url)
            job = api.create_export(STUDY_ID)
            api.wait_for_export(job["job_id"], timeout=1, poll_interval=0.001)
            download = api.get_export_download(job["job_id"])
        self.assertEqual(json.loads(calls[0][3]), {"study_id": STUDY_ID, "format": "csv"})
        self.assertEqual(download.content_type, "text/csv")
        self.assertTrue(download.body.startswith(b"interview_id,"))

    def test_signed_json_download_uses_no_bearer_or_cookies(self):
        csv = b"interview_id,answer\nexample,fabricated\n"
        with server([(200, {"Content-Type": "text/csv"}, csv)]) as (storage_url, storage_calls):
            with server([(200, {"Set-Cookie": "session=must-not-forward"},
                          {"download_url": storage_url + "/artifact?signature=private"})]) as (url, calls):
                download = client(url).download_export("export-job")
        self.assertEqual(download.body, csv)
        self.assertIn("Authorization", calls[0][2])
        self.assertNotIn("Authorization", storage_calls[0][2])
        self.assertNotIn("Cookie", storage_calls[0][2])
        self.assertNotIn("signature", repr(download))

    def test_signed_download_does_not_follow_redirect_or_expose_url_in_error(self):
        signed_url = "https://storage.example.test/file?signature=secret"
        with server([(302, {"Location": signed_url}, {"detail": signed_url})]) as (storage_url, storage_calls):
            with server([(200, {}, {"download_url": storage_url + "/artifact"})]) as (url, _calls):
                with self.assertRaises(APIError) as caught:
                    client(url).download_export("export-job")
        self.assertEqual(len(storage_calls), 1)
        self.assertNotIn("Authorization", storage_calls[0][2])
        self.assertNotIn("signature", str(caught.exception))

    def test_signed_download_rejects_unsafe_urls(self):
        for target in ["http://storage.example.test/file", "https://user:pass@example.test/file",
                       "https://169.254.169.254/file", "https://localhost/file", "https://192.168.1.4/file"]:
            with self.subTest(target=target):
                with server([(200, {}, {"download_url": target})]) as (url, calls):
                    api = client(url)
                    # Local fixture transport is allowed, but production download policy is retained.
                    api._allow_insecure_localhost = False
                    with self.assertRaises(ValueError):
                        api.download_export("export-job")
                self.assertEqual(len(calls), 1)

    def test_permission_error_preserves_status_and_validation_omits_input(self):
        with server([(403, {}, {"detail": "Missing required scope: export:read"}),
                     (422, {}, {"detail": [{"loc": ["body", "guidance"], "msg": "Field required",
                                          "input": "private participant information"}]})]) as (url, calls):
            api = client(url)
            with self.assertRaises(APIError) as denied:
                api.get_interview(INTERVIEW_ID)
            with self.assertRaises(APIError) as invalid:
                api.create_study("brief")
        self.assertEqual(denied.exception.status, 403)
        self.assertIn("export:read", str(denied.exception))
        self.assertIn("body.guidance", str(invalid.exception))
        self.assertNotIn("private participant", str(invalid.exception))
        self.assertEqual(len(calls), 2)

    def test_set_mode_is_an_explicit_wire_action(self):
        with server([(200, {}, {"mode": "live", "url": "https://example.test/invite"})]) as (url, calls):
            client(url).set_study_mode(STUDY_ID, "live")
        self.assertEqual(calls[0][:2], ("PUT", f"/v1/api/studies/{STUDY_ID}/mode"))
        self.assertEqual(json.loads(calls[0][3]), {"mode": "live"})

    def test_failed_and_unknown_job_statuses_stop_polling(self):
        for payload, expected in [({"status": "failed"}, JobFailed), ({"status": "surprise"}, ProtocolError)]:
            with self.subTest(payload=payload):
                with server([(200, {}, payload)]) as (url, calls):
                    with self.assertRaises(expected):
                        client(url).wait_for_authoring("job", timeout=1, poll_interval=0.001)
                self.assertEqual(len(calls), 1)

    def test_polling_deadline_does_not_start_another_request(self):
        with server([(200, {}, {"status": "working"})]) as (url, calls):
            with self.assertRaises(PollTimeout) as caught:
                client(url).wait_for_authoring("job", timeout=0.02, poll_interval=1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(caught.exception.job_id, "job")
        self.assertEqual(caught.exception.last_status, "working")

    def test_invalid_json_and_wrong_shape_are_explicit(self):
        for payload in [b"not-json", []]:
            with self.subTest(payload=payload):
                with server([(200, {}, payload)]) as (url, _calls):
                    with self.assertRaises(ProtocolError):
                        client(url).me()

    def test_invalid_identifiers_and_base_urls_never_send(self):
        for url in ["http://api.heyjuno.co/v1/api", "https://user:pass@example.test", "https://example.test?q=a"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                JunoClient(KEY, base_url=url)
        with server([]) as (url, calls):
            api = client(url)
            with self.assertRaises(ValueError):
                api.get_study("../me")
            with self.assertRaises(ValueError):
                api.get_authoring_job("../me")
            with self.assertRaises(ValueError):
                api.create_study("brief", idempotency_key="x\r\nAuthorization: unsafe")
        self.assertEqual(calls, [])

    def test_public_snapshot_has_every_implemented_operation(self):
        snapshot = json.loads((Path(__file__).parents[1] / "reference/openapi.json").read_text())
        operations = {
            "/me": "get", "/studies": "get post", "/studies/{study_id}": "get",
            "/studies/{study_id}/interview-link": "get", "/studies/jobs/{job_id}": "get",
            "/studies/{study_id}/mode": "put", "/interviews": "get",
            "/interviews/{interview_id}": "get", "/exports": "post",
            "/exports/{job_id}": "get", "/exports/{job_id}/download": "get",
        }
        for path, verbs in operations.items():
            for verb in verbs.split():
                self.assertIn(verb, snapshot["paths"]["/v1/api" + path])
        params = snapshot["paths"]["/v1/api/studies"]["post"]["parameters"]
        self.assertTrue(any(p["name"] == "Idempotency-Key" and p["in"] == "header" for p in params))


if __name__ == "__main__":
    unittest.main()
