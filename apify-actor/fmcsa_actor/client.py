"""HTTP client for the official FMCSA QCMobile API.

Base URL: https://mobile.fmcsa.dot.gov/qc/services/
Every request sends the caller's WebKey as the webKey query parameter.
This client does not request the SAFER website.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .errors import FmcsaApiError, FmcsaAuthError
from .input_parser import SearchRequest
from .mapping import carrier_row, not_found

BASE_URL = "https://mobile.fmcsa.dot.gov/qc/services/carriers/"
USER_AGENT = "fmcsa-qcmobile-actor/1.0 (+https://mobile.fmcsa.dot.gov/qc/services/)"
_OFFICIAL_PATH = re.compile(
    r"^/qc/services/carriers/"
    r"(?:"
    r"\d{1,12}"
    r"|\d{1,12}/authority"
    r"|docket-number/\d{1,12}"
    r"|name/(?:%[0-9A-Fa-f]{2}|[A-Za-z0-9._~-])+"
    r")$"
)

UrlOpen = Callable[..., Any]


class FmcsaClient:
    """Look up carriers and attach authority records."""

    def __init__(self, web_key: str, *, urlopen: UrlOpen | None = None, timeout: float = 30.0) -> None:
        key = web_key.strip()
        if not key:
            raise ValueError("webKey is required.")
        self._web_key = key
        self._urlopen = urlopen or urllib.request.urlopen
        self._timeout = timeout

    def lookup(self, request: SearchRequest) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if request.dot_number:
            rows.extend(self.lookup_dot(request.dot_number))
        if request.docket_number and request.docket_query:
            rows.extend(self.lookup_docket(request.docket_number, request.docket_query))
        if request.carrier_name:
            rows.extend(self.lookup_name(request.carrier_name, request.max_results))
        return rows

    def lookup_dot(self, dot_number: str) -> list[dict[str, Any]]:
        payload = self._get(dot_number)
        carriers = _carriers(payload["content"])
        if not carriers:
            return [not_found("dot", dot_number, payload.get("message") or "No carrier found for that USDOT number.", payload.get("retrievalDate"))]
        return [self._with_authority("dot", dot_number, carrier, payload.get("retrievalDate")) for carrier in carriers]

    def lookup_docket(self, docket_number: str, query: str) -> list[dict[str, Any]]:
        payload = self._get(f"docket-number/{docket_number}")
        carriers = _carriers(payload["content"])
        if not carriers:
            return [not_found("docket", query, payload.get("message") or "No carrier found for that docket number.", payload.get("retrievalDate"))]
        return [
            self._with_authority("docket", query, carrier, payload.get("retrievalDate"))
            for carrier in carriers
        ]

    def lookup_name(self, name: str, max_results: int) -> list[dict[str, Any]]:
        quoted = urllib.parse.quote(name, safe="")
        payload = self._get(
            f"name/{quoted}",
            {"start": "0", "size": str(max_results)},
        )
        carriers = _carriers(payload["content"])[:max_results]
        if not carriers:
            return [not_found("name", name, payload.get("message") or "No carrier found for that name.", payload.get("retrievalDate"))]
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for carrier in carriers:
            dot = str(carrier.get("dotNumber") or "")
            if dot and dot in seen:
                continue
            if dot:
                seen.add(dot)
            rows.append(self._with_authority("name", name, carrier, payload.get("retrievalDate")))
        return rows

    def _with_authority(
        self,
        query_type: str,
        query: str,
        carrier: dict[str, Any],
        retrieval_date: str | None,
    ) -> dict[str, Any]:
        dot = str(carrier.get("dotNumber") or "").strip()
        records: list[dict[str, Any]] = []
        if dot:
            authority_payload = self._get(f"{dot}/authority")
            records = _authority_records(authority_payload["content"])
        return carrier_row(query_type, query, carrier, records, retrieval_date)

    def _get(self, path: str, extra_params: dict[str, str] | None = None) -> dict[str, Any]:
        params = {"webKey": self._web_key}
        if extra_params:
            params.update(extra_params)
        # path may already contain a percent-encoded name segment.
        url = BASE_URL + path.lstrip("/") + "?" + urllib.parse.urlencode(params)
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "mobile.fmcsa.dot.gov":
            raise FmcsaApiError("Refusing to call a host other than the official FMCSA QCMobile API.")
        if "safer" in url.lower() or not _OFFICIAL_PATH.match(parsed.path):
            raise FmcsaApiError("Refusing to call a path outside the official FMCSA QCMobile API.")

        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with self._urlopen(request, timeout=self._timeout) as response:
                status = getattr(response, "status", None) or response.getcode()
                body = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = exc.read()
        except urllib.error.URLError as exc:
            raise FmcsaApiError(f"Could not reach the FMCSA QCMobile API: {exc.reason}") from exc
        return _parse_body(status, body)


def _parse_body(status: int, body: bytes) -> dict[str, Any]:
    text = body.decode("utf-8", errors="replace").strip()
    if "FMCSA System Maintenance" in text or text.lower().startswith("<!doctype html") or text.lower().startswith("<html"):
        raise FmcsaApiError("FMCSA QCMobile API is unavailable (maintenance page).")
    if not text:
        if status == 404:
            return {"content": None, "message": "No carrier found.", "retrievalDate": None}
        raise FmcsaApiError(f"FMCSA QCMobile API returned an empty response (HTTP {status}).")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FmcsaApiError(f"FMCSA QCMobile API returned non-JSON (HTTP {status}).") from exc
    if not isinstance(payload, dict):
        raise FmcsaApiError(f"FMCSA QCMobile API returned an unexpected payload (HTTP {status}).")

    content = payload.get("content")
    retrieval = payload.get("retrievalDate")
    retrieval_text = retrieval if isinstance(retrieval, str) else None

    if isinstance(content, str):
        if _is_auth_message(content) or status in (401, 403):
            raise FmcsaAuthError(
                "FMCSA rejected the WebKey. Check the secret webKey input from your FMCSA developer account."
            )
        if status >= 500:
            raise FmcsaApiError(content or f"FMCSA QCMobile API returned HTTP {status}.")
        if status >= 400 and status != 404:
            raise FmcsaApiError(content or f"FMCSA QCMobile API returned HTTP {status}.")
        return {"content": None, "message": content, "retrievalDate": retrieval_text}

    if status in (401, 403) or _content_is_auth(content):
        raise FmcsaAuthError(
            "FMCSA rejected the WebKey. Check the secret webKey input from your FMCSA developer account."
        )
    if status == 404:
        return {"content": None, "message": "No carrier found.", "retrievalDate": retrieval_text}
    if status >= 400:
        raise FmcsaApiError(f"FMCSA QCMobile API returned HTTP {status}.")
    return {"content": content, "message": None, "retrievalDate": retrieval_text}


def _is_auth_message(content: str) -> bool:
    lowered = content.lower()
    return "webkey" in lowered or "web key" in lowered or "unauthorized" in lowered


def _content_is_auth(content: object) -> bool:
    return isinstance(content, str) and _is_auth_message(content)


def _carriers(content: object) -> list[dict[str, Any]]:
    if isinstance(content, dict):
        items = [content]
    elif isinstance(content, list):
        items = [item for item in content if isinstance(item, dict)]
    else:
        return []
    carriers: list[dict[str, Any]] = []
    for item in items:
        carrier = item.get("carrier", item)
        if isinstance(carrier, dict) and carrier.get("dotNumber") is not None:
            carriers.append(carrier)
    return carriers


def _authority_records(content: object) -> list[dict[str, Any]]:
    if not isinstance(content, list):
        return []
    records: list[dict[str, Any]] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        authority = item.get("carrierAuthority", item)
        if isinstance(authority, dict) and (
            "docketNumber" in authority or "commonAuthorityStatus" in authority
        ):
            records.append(authority)
    return records
