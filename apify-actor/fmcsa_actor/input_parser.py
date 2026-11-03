"""Validate Actor input. The WebKey is the caller's own FMCSA credential."""

from __future__ import annotations

import re

_DOCKET_PREFIX = re.compile(r"^(?:MC|FF|MX)[\s-]*", re.IGNORECASE)
_MAX_RESULTS_DEFAULT = 10
_MAX_RESULTS_LIMIT = 50

class SearchRequest:
    """One Actor run: a WebKey plus at least one carrier query."""

    def __init__(
        self,
        web_key: str,
        dot_number: str | None,
        docket_number: str | None,
        docket_query: str | None,
        carrier_name: str | None,
        max_results: int,
    ) -> None:
        self.web_key = web_key
        self.dot_number = dot_number
        self.docket_number = docket_number
        self.docket_query = docket_query
        self.carrier_name = carrier_name
        self.max_results = max_results

    def __repr__(self) -> str:
        return (
            "SearchRequest(web_key='***', "
            f"dot_number={self.dot_number!r}, "
            f"docket_number={self.docket_number!r}, "
            f"docket_query={self.docket_query!r}, "
            f"carrier_name={self.carrier_name!r}, "
            f"max_results={self.max_results!r})"
        )


def parse_input(raw: dict | None) -> SearchRequest:
    """Parse and normalize Actor input.

    Raises ValueError with a message safe to show as the run status.
    """
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object.")

    web_key = _required_secret(raw.get("webKey"))
    dot_number = _normalize_dot(_optional_text(raw.get("dotNumber"), "dotNumber"))
    docket_number, docket_query = _normalize_docket(
        _optional_text(raw.get("docketNumber"), "docketNumber")
    )
    carrier_name = _normalize_name(_optional_text(raw.get("carrierName"), "carrierName"))
    max_results = _parse_max_results(raw.get("maxResults", _MAX_RESULTS_DEFAULT))

    if not any((dot_number, docket_number, carrier_name)):
        raise ValueError(
            "Provide a dotNumber, a docketNumber (MC/FF/MX), or a carrierName."
        )

    return SearchRequest(
        web_key=web_key,
        dot_number=dot_number,
        docket_number=docket_number,
        docket_query=docket_query,
        carrier_name=carrier_name,
        max_results=max_results,
    )


def _required_secret(value: object) -> str:
    text = _optional_text(value, "webKey")
    if not text:
        raise ValueError(
            "webKey is required. Use your own free FMCSA WebKey from "
            "https://mobile.fmcsa.dot.gov/QCDevsite/docs/getStarted."
        )
    return text


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, (list, dict)):
        raise ValueError(f"{field} must be a string.")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{field} must be a string.")
        return str(int(value))
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string.")
    text = value.strip()
    return text or None


def _normalize_dot(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    digits = digits.lstrip("0")
    if not digits or len(digits) > 12:
        raise ValueError(f"dotNumber {value!r} is not a USDOT number.")
    return digits


def _normalize_docket(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    prefix_match = _DOCKET_PREFIX.match(value)
    prefix = prefix_match.group(0) if prefix_match else ""
    prefix_code = re.sub(r"[^A-Za-z]", "", prefix).upper() or None
    remainder = value[prefix_match.end():] if prefix_match else value
    digits = re.sub(r"\D", "", remainder)
    digits = digits.lstrip("0")
    if not digits or len(digits) > 12:
        raise ValueError(
            f"docketNumber {value!r} is not an MC, FF, or MX docket number."
        )
    query = f"{prefix_code}-{digits}" if prefix_code else digits
    return digits, query


def _normalize_name(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = re.sub(r"\s+", " ", value).strip()
    if len(collapsed) < 2:
        raise ValueError("carrierName must be at least 2 characters.")
    if len(collapsed) > 120:
        raise ValueError("carrierName must be 120 characters or fewer.")
    return collapsed


def _parse_max_results(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("maxResults must be an integer from 1 to 50.")
    if isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise ValueError("maxResults must be an integer from 1 to 50.")
        number = int(text)
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError("maxResults must be an integer from 1 to 50.")
        number = int(value)
    elif isinstance(value, int):
        number = value
    else:
        raise ValueError("maxResults must be an integer from 1 to 50.")
    if not 1 <= number <= _MAX_RESULTS_LIMIT:
        raise ValueError("maxResults must be an integer from 1 to 50.")
    return number
