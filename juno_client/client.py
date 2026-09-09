"""Small, synchronous client for the published Juno API. Runtime: Python stdlib."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from urllib.parse import quote, urlencode
from uuid import UUID

from ._transport import (
    Download, JunoError, ProtocolError, Transport, checked_url, parse_json, positive_number,
)


@dataclass(frozen=True)
class Page:
    """One page of public records; pass next_cursor unchanged to the next call."""

    items: list[dict] = field(repr=False)
    next_cursor: str | None = field(repr=False)


class JobFailed(JunoError):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__("Juno reported that the job failed; inspect the job before starting another")


class PollTimeout(JunoError):
    def __init__(self, job_id: str, last_status: str | None):
        self.job_id = job_id
        self.last_status = last_status
        super().__init__("Polling deadline reached; the server job continues. Resume with the existing job_id.")


def _uuid(value: str) -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("Expected a UUID identifier") from None


def _job(value: str) -> str:
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise ValueError("Job identifier must be a nonempty path segment")
    if any(ord(c) < 32 for c in value) or "/" in value or "\\" in value:
        raise ValueError("Job identifier cannot contain path separators or control characters")
    return quote(value, safe="")


def _object(response) -> dict:
    value = parse_json(response)
    if not isinstance(value, dict):
        raise ProtocolError("Expected a JSON object")
    return value


class JunoClient:
    """Use an explicit key or JUNO_API_KEY. No writes or downloads happen on construction.

    base_url includes /v1/api. request_timeout bounds each blocking socket operation;
    polling deadlines stop further requests. No automatic retries or redirect follows.
    max_response_bytes bounds each buffered response, including CSV downloads.
    """

    def __init__(self, api_key: str | None = None, *,
                 base_url: str = "https://api.heyjuno.co/v1/api", request_timeout: float = 30,
                 max_response_bytes: int = 64 * 1024 * 1024, allow_insecure_localhost: bool = False):
        key = api_key if api_key is not None else os.environ.get("JUNO_API_KEY")
        if not key:
            raise ValueError("Set JUNO_API_KEY or pass api_key explicitly")
        self.base_url = checked_url(base_url, allow_insecure_localhost=allow_insecure_localhost).rstrip("/")
        self._allow_insecure_localhost = allow_insecure_localhost
        self._transport = Transport(key, request_timeout, max_response_bytes)

    def _request(self, method, path, *, payload=None, query=None, idempotency_key=None, timeout=None):
        url = self.base_url + path
        if query:
            url += "?" + urlencode({k: v for k, v in query.items() if v is not None})
        return self._transport.send(method, url, payload=payload, idempotency_key=idempotency_key, timeout=timeout)

    def me(self) -> dict:
        return _object(self._request("GET", "/me"))

    def create_study(self, guidance: str, *, file_ids: list[str] | None = None,
                     idempotency_key: str | None = None) -> dict:
        """Create a Test-mode study and return its authoring job; never go live."""
        if not isinstance(guidance, str) or not guidance:
            raise ValueError("guidance must be a nonempty string")
        body = {"guidance": guidance}
        if file_ids is not None:
            if not isinstance(file_ids, list) or not all(isinstance(v, str) for v in file_ids):
                raise ValueError("file_ids must be a list of uploaded file ID strings")
            body["file_ids"] = file_ids
        return _object(self._request("POST", "/studies", payload=body, idempotency_key=idempotency_key))

    def get_authoring_job(self, job_id: str, *, timeout: float | None = None) -> dict:
        return _object(self._request("GET", "/studies/jobs/" + _job(job_id), timeout=timeout))

    def wait_for_authoring(self, job_id: str, *, timeout: float = 300, poll_interval: float = 2) -> dict:
        return self._poll(job_id, self.get_authoring_job, "ready", {"working"}, timeout, poll_interval)

    def get_study(self, study_id: str) -> dict:
        return _object(self._request("GET", "/studies/" + _uuid(study_id)))

    def get_interview_link(self, study_id: str) -> dict:
        """Get the durable link. This does not send it or change collection mode."""
        return _object(self._request("GET", f"/studies/{_uuid(study_id)}/interview-link"))

    def set_study_mode(self, study_id: str, mode: str) -> dict:
        """Explicit collection action; live permits real interviews and credit use."""
        if not isinstance(mode, str) or mode not in {"test", "live", "paused", "closed"}:
            raise ValueError("mode must be a value supported by the public API")
        return _object(self._request("PUT", f"/studies/{_uuid(study_id)}/mode", payload={"mode": mode}))

    def _page(self, path: str, query: dict) -> Page:
        limit = query["limit"]
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("limit must be an integer from 1 to 200")
        if query.get("cursor") is not None and not isinstance(query["cursor"], str):
            raise ValueError("cursor must be a string")
        response = self._request("GET", path, query=query)
        value = parse_json(response)
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ProtocolError("Expected a JSON array of records")
        return Page(value, response.headers.get("x-next-cursor"))

    def list_studies(self, *, limit: int = 50, cursor: str | None = None) -> Page:
        return self._page("/studies", {"limit": limit, "cursor": cursor})

    def list_interviews(self, *, study_id: str | None = None, status: str | None = None,
                        limit: int = 50, cursor: str | None = None) -> Page:
        """Metadata only, including is_test; use exports for participant transcripts."""
        if status is not None and (not isinstance(status, str) or status not in {"in_progress", "completed", "failed"}):
            raise ValueError("status must be in_progress, completed, or failed")
        return self._page("/interviews", {"study_id": _uuid(study_id) if study_id is not None else None,
                                         "status": status, "limit": limit, "cursor": cursor})

    def get_interview(self, interview_id: str) -> dict:
        """Get interview metadata and its Juno permalink, without transcript text."""
        return _object(self._request("GET", "/interviews/" + _uuid(interview_id)))

    def create_export(self, study_id: str) -> dict:
        """Start a CSV export of completed Live-mode interviews; never auto-retry."""
        return _object(self._request("POST", "/exports", payload={"study_id": _uuid(study_id), "format": "csv"}))

    def get_export(self, job_id: str, *, timeout: float | None = None) -> dict:
        return _object(self._request("GET", "/exports/" + _job(job_id), timeout=timeout))

    def wait_for_export(self, job_id: str, *, timeout: float = 300, poll_interval: float = 2) -> dict:
        return self._poll(job_id, self.get_export, "completed", {"queued", "running"}, timeout, poll_interval)

    def _poll(self, job_id, fetch, done_status, pending_statuses, timeout, poll_interval):
        _job(job_id)
        deadline = time.monotonic() + positive_number(timeout, "timeout")
        interval = positive_number(poll_interval, "poll_interval")
        last_status = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PollTimeout(job_id, last_status)
            result = fetch(job_id, timeout=remaining)
            last_status = result.get("status")
            if not isinstance(last_status, str):
                raise ProtocolError("Job response must include a string status")
            if last_status == "failed":
                raise JobFailed(job_id)
            if last_status == done_status:
                if done_status == "completed" and result.get("ready") is not True:
                    raise ProtocolError("Completed export response must declare ready=true")
                return result
            if last_status not in pending_statuses:
                raise ProtocolError("Unexpected job status; resume manually after checking the API contract")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PollTimeout(job_id, last_status)
            time.sleep(min(interval, remaining))

    def get_export_download(self, job_id: str) -> Download:
        """Inspect inline CSV or signed download location; do not fetch a signed URL."""
        response = self._transport.send("GET", self.base_url + f"/exports/{_job(job_id)}/download",
                                        accept="text/csv, application/json", allow_download_redirect=True)
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        location = response.headers.get("location") if 300 <= response.status < 400 else None
        if content_type == "application/json":
            payload = _object(response)
            location = payload.get("download_url")
            if not isinstance(location, str) or not location:
                raise ProtocolError("Expected download_url in export download JSON")
        if location:
            checked_url(location, allow_insecure_localhost=self._allow_insecure_localhost, signed=True)
            return Download(b"", content_type, location)
        if content_type not in {"text/csv", "application/octet-stream"}:
            raise ProtocolError("Expected inline CSV or a signed download URL")
        return Download(response.body, content_type)

    def download_export(self, job_id: str) -> Download:
        """Get CSV bytes, fetching signed URLs anonymously; never write a file.

        Signed requests carry no Juno Authorization header or cookies. No redirects
        are followed; URL query credentials remain excluded from client errors.
        """
        download = self.get_export_download(job_id)
        if download.location is None:
            return download
        response = self._transport.send("GET", download.location, authenticate=False, accept="text/csv")
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"text/csv", "application/octet-stream"}:
            raise ProtocolError("Signed download did not return CSV or an octet stream")
        return Download(response.body, content_type)
