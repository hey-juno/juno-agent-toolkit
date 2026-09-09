"""One HTTP boundary; redirects are never followed, including signed downloads."""

from __future__ import annotations

import ipaddress
import json
import math
import re
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class JunoError(Exception):
    """Base class for client failures. Requests are never automatically retried."""


class ProtocolError(JunoError):
    """The response cannot carry the documented operation's result."""


class APIError(JunoError):
    """HTTP failure with redacted detail and optional server correlation headers."""

    def __init__(self, status, detail, *, request_id=None, retry_after=None):
        self.status = status
        self.detail = detail
        self.request_id = request_id
        self.retry_after = retry_after
        suffix = f" (request {request_id})" if request_id else ""
        super().__init__(f"Juno HTTP {status}: {detail}{suffix}")


class TransportError(JunoError):
    """Network or timeout failure; a write may have been accepted by the server."""


@dataclass(frozen=True)
class Download:
    """CSV bytes or a signed URL. Both are deliberately excluded from repr."""

    body: bytes = field(repr=False)
    content_type: str
    location: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes = field(repr=False)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def positive_number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return float(value)


def header_value(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError(f"{name} must contain non-whitespace ASCII characters")
    return value


def checked_url(url: str, *, allow_insecure_localhost: bool = False, signed: bool = False) -> str:
    if not isinstance(url, str) or any(ord(c) <= 32 for c in url) or "\\" in url:
        raise ValueError("URL must be an absolute HTTPS URL")
    parts = urlsplit(url)
    host = parts.hostname
    try:
        parts.port
    except ValueError:
        raise ValueError("URL has an invalid port") from None
    if not host or parts.username is not None or parts.password is not None or parts.fragment:
        raise ValueError("URL must have a host and no credentials or fragment")
    local = host in {"localhost", "127.0.0.1", "::1"}
    if parts.scheme != "https" and not (allow_insecure_localhost and local and parts.scheme == "http"):
        raise ValueError("HTTPS is required; HTTP is only allowed for explicit localhost tests")
    if signed:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if local or host.endswith((".localhost", ".local")) or (address is not None and not address.is_global):
            if not (allow_insecure_localhost and local):
                raise ValueError("Signed download URL must name a public HTTPS host")
    elif parts.query:
        raise ValueError("API base URL cannot contain a query")
    return url


def parse_json(response: Response):
    try:
        return json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ProtocolError("Expected a JSON response; response body is not included in this error") from None


class Transport:
    def __init__(self, api_key: str, timeout: float, max_response_bytes: int):
        self._api_key = header_value(api_key, "API key")
        self.timeout = positive_number(timeout, "request_timeout")
        if isinstance(max_response_bytes, bool) or not isinstance(max_response_bytes, int) or max_response_bytes < 1:
            raise ValueError("max_response_bytes must be a positive integer")
        self.max_response_bytes = max_response_bytes
        # No cookie jar, cached auth, or global opener is installed.
        self._opener = build_opener(_NoRedirect())

    def _redact(self, value: str) -> str:
        value = str(value).replace(self._api_key, "[redacted]")
        value = re.sub(r"jsk_(?:live|test)_[A-Za-z0-9_-]+", "[redacted]", value)
        value = re.sub(r"(?i)Bearer\s+\S+", "Bearer [redacted]", value)
        value = re.sub(r"https?://\S+", "[URL omitted]", value)
        return " ".join(value.split())[:500]

    def _http_error(self, response: Response) -> APIError:
        detail = "Request failed; see the public API contract and key scopes"
        try:
            payload = json.loads(response.body)
        except (ValueError, UnicodeDecodeError):
            payload = None
        if isinstance(payload, dict):
            candidate = payload.get("detail", payload.get("message"))
            if isinstance(candidate, str):
                detail = self._redact(candidate)
            elif isinstance(candidate, list):
                # Validation input and context can echo user data; only show locations and messages.
                details = []
                for entry in candidate:
                    if isinstance(entry, dict) and isinstance(entry.get("msg"), str):
                        loc = ".".join(str(x) for x in entry.get("loc", []))
                        details.append(f"{loc}: {entry['msg']}")
                if details:
                    detail = self._redact("; ".join(details))
        if 300 <= response.status < 400:
            detail = "Redirect refused; verify the API base URL (credentials were not forwarded)"
        request_id = response.headers.get("x-request-id")
        retry_after = response.headers.get("retry-after")
        return APIError(response.status, detail,
                        request_id=self._redact(request_id) if request_id else None,
                        retry_after=self._redact(retry_after) if retry_after else None)

    def send(self, method: str, url: str, *, payload=None, authenticate=True,
             idempotency_key=None, timeout=None, accept="application/json", allow_download_redirect=False) -> Response:
        headers = {"Accept": accept, "User-Agent": "juno-agent-toolkit/0.1.0a1"}
        if authenticate:
            headers["Authorization"] = f"Bearer {self._api_key}"
        data = None
        if payload is not None:
            data = json.dumps(payload, allow_nan=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = header_value(idempotency_key, "Idempotency key")
        request = Request(url, data=data, headers=headers, method=method)
        effective_timeout = self.timeout if timeout is None else min(self.timeout, positive_number(timeout, "timeout"))
        try:
            try:
                stream = self._opener.open(request, timeout=effective_timeout)
            except HTTPError as exc:
                stream = exc
            with stream:
                body = stream.read(self.max_response_bytes + 1)
                response = Response(stream.code, {k.lower(): v for k, v in stream.headers.items()}, body)
        except (URLError, TimeoutError, OSError):
            raise TransportError("Network request failed or timed out. A write may have completed; inspect its state before retrying.") from None
        if len(body) > self.max_response_bytes:
            raise ProtocolError("Response exceeds max_response_bytes; increase that explicit client limit if needed")
        if allow_download_redirect and response.status in {301, 302, 303, 307, 308}:
            return response
        if not 200 <= response.status < 300:
            raise self._http_error(response)
        return response
