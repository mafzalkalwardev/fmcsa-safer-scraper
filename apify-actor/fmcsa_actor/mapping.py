"""Map official FMCSA QCMobile JSON into dataset items.

Insurance amounts on the carrier record are thousands of U.S. dollars.
Authority codes are A (active), I (inactive), and N (none).
Safety ratings are S (satisfactory), C (conditional), and U (unsatisfactory).
A missing safety rating means FMCSA has not rated the carrier.
"""

from __future__ import annotations

from typing import Any

SOURCE = "FMCSA QCMobile API"
SOURCE_URL = "https://mobile.fmcsa.dot.gov/qc/services/"

_AUTHORITY_LABELS = {
    "A": "Active",
    "I": "Inactive",
    "N": "None",
}
_SAFETY_LABELS = {
    "S": "Satisfactory",
    "C": "Conditional",
    "U": "Unsatisfactory",
}
_STATUS_LABELS = {
    "A": "Active",
    "I": "Inactive",
}
_YES_NO_LABELS = {
    "Y": "Yes",
    "N": "No",
    "U": "Unknown",
}


def not_found(query_type: str, query: str, message: str, retrieval_date: str | None) -> dict[str, Any]:
    row = _empty_row(query_type, query)
    row["found"] = False
    row["message"] = message
    row["retrievalDate"] = retrieval_date
    return row


def carrier_row(
    query_type: str,
    query: str,
    carrier: dict[str, Any],
    authority_records: list[dict[str, Any]],
    retrieval_date: str | None,
) -> dict[str, Any]:
    operation = carrier.get("carrierOperation")
    if not isinstance(operation, dict):
        operation = {}

    mapped_authority = [_authority_record(item) for item in authority_records]
    common = _prefer_code(carrier.get("commonAuthorityStatus"), mapped_authority, "commonAuthorityStatus")
    contract = _prefer_code(carrier.get("contractAuthorityStatus"), mapped_authority, "contractAuthorityStatus")
    broker = _prefer_code(carrier.get("brokerAuthorityStatus"), mapped_authority, "brokerAuthorityStatus")
    allowed = _code(carrier.get("allowedToOperate"))
    status_code = _code(carrier.get("statusCode"))
    safety = _code(carrier.get("safetyRating"))

    row = _empty_row(query_type, query)
    row.update(
        {
            "found": True,
            "message": None,
            "dotNumber": _stringify(carrier.get("dotNumber")),
            "legalName": _text(carrier.get("legalName")),
            "dbaName": _text(carrier.get("dbaName")),
            "docketNumbers": _docket_numbers(mapped_authority),
            "allowedToOperate": allowed,
            "operatingStatus": _operating_status(allowed),
            "statusCode": status_code,
            "statusLabel": _STATUS_LABELS.get(status_code or "", "Unknown" if status_code is None else status_code),
            "outOfServiceDate": _text(carrier.get("oosDate")),
            "carrierOperationCode": _text(operation.get("carrierOperationCode")),
            "carrierOperation": _text(operation.get("carrierOperationDesc")),
            "commonAuthorityStatus": common,
            "commonAuthorityStatusLabel": _authority_label(common),
            "contractAuthorityStatus": contract,
            "contractAuthorityStatusLabel": _authority_label(contract),
            "brokerAuthorityStatus": broker,
            "brokerAuthorityStatusLabel": _authority_label(broker),
            "authorityRecords": mapped_authority,
            "safetyRating": safety,
            "safetyRatingLabel": _SAFETY_LABELS.get(safety or "", "Not rated" if safety is None else safety),
            "safetyRatingDate": _text(carrier.get("safetyRatingDate")),
            "safetyReviewDate": _text(carrier.get("safetyReviewDate")),
            "safetyReviewType": _text(carrier.get("safetyReviewType")),
            "phyStreet": _text(carrier.get("phyStreet")),
            "phyCity": _text(carrier.get("phyCity")),
            "phyState": _text(carrier.get("phyState")),
            "phyZipcode": _text(carrier.get("phyZipcode")),
            "phyCountry": _text(carrier.get("phyCountry")),
            "totalPowerUnits": _as_int(carrier.get("totalPowerUnits")),
            "totalDrivers": _as_int(carrier.get("totalDrivers")),
            "retrievalDate": retrieval_date,
        }
    )
    row.update(_insurance_fields(carrier))
    return row


def _empty_row(query_type: str, query: str) -> dict[str, Any]:
    return {
        "found": False,
        "queryType": query_type,
        "query": query,
        "message": None,
        "dotNumber": None,
        "legalName": None,
        "dbaName": None,
        "docketNumbers": [],
        "allowedToOperate": None,
        "operatingStatus": None,
        "statusCode": None,
        "statusLabel": None,
        "outOfServiceDate": None,
        "carrierOperationCode": None,
        "carrierOperation": None,
        "commonAuthorityStatus": None,
        "commonAuthorityStatusLabel": None,
        "contractAuthorityStatus": None,
        "contractAuthorityStatusLabel": None,
        "brokerAuthorityStatus": None,
        "brokerAuthorityStatusLabel": None,
        "authorityRecords": [],
        "bipdInsuranceOnFile": None,
        "bipdInsuranceOnFileUsd": None,
        "bipdInsuranceRequired": None,
        "bipdInsuranceRequiredLabel": None,
        "bipdRequiredAmount": None,
        "bipdRequiredAmountUsd": None,
        "cargoInsuranceOnFile": None,
        "cargoInsuranceOnFileUsd": None,
        "cargoInsuranceRequired": None,
        "cargoInsuranceRequiredLabel": None,
        "bondInsuranceOnFile": None,
        "bondInsuranceOnFileUsd": None,
        "bondInsuranceRequired": None,
        "bondInsuranceRequiredLabel": None,
        "safetyRating": None,
        "safetyRatingLabel": None,
        "safetyRatingDate": None,
        "safetyReviewDate": None,
        "safetyReviewType": None,
        "phyStreet": None,
        "phyCity": None,
        "phyState": None,
        "phyZipcode": None,
        "phyCountry": None,
        "totalPowerUnits": None,
        "totalDrivers": None,
        "source": SOURCE,
        "sourceUrl": SOURCE_URL,
        "retrievalDate": None,
    }


def _insurance_fields(carrier: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    pairs = (
        ("bipdInsuranceOnFile", "bipdInsuranceOnFile", "bipdInsuranceOnFileUsd"),
        ("bipdRequiredAmount", "bipdRequiredAmount", "bipdRequiredAmountUsd"),
        ("cargoInsuranceOnFile", "cargoInsuranceOnFile", "cargoInsuranceOnFileUsd"),
        ("bondInsuranceOnFile", "bondInsuranceOnFile", "bondInsuranceOnFileUsd"),
    )
    for source_key, raw_key, usd_key in pairs:
        raw = _code(carrier.get(source_key))
        fields[raw_key] = raw
        fields[usd_key] = thousands_to_usd(raw)
    for source_key, raw_key, label_key in (
        ("bipdInsuranceRequired", "bipdInsuranceRequired", "bipdInsuranceRequiredLabel"),
        ("cargoInsuranceRequired", "cargoInsuranceRequired", "cargoInsuranceRequiredLabel"),
        ("bondInsuranceRequired", "bondInsuranceRequired", "bondInsuranceRequiredLabel"),
    ):
        raw = _code(carrier.get(source_key))
        fields[raw_key] = raw
        fields[label_key] = _requirement_label(raw)
    return fields


def _authority_record(raw: dict[str, Any]) -> dict[str, Any]:
    common = _code(raw.get("commonAuthorityStatus"))
    contract = _code(raw.get("contractAuthorityStatus"))
    broker = _code(raw.get("brokerAuthorityStatus"))
    return {
        "prefix": _text(raw.get("prefix")),
        "docketNumber": _stringify(raw.get("docketNumber")),
        "commonAuthorityStatus": common,
        "commonAuthorityStatusLabel": _authority_label(common),
        "contractAuthorityStatus": contract,
        "contractAuthorityStatusLabel": _authority_label(contract),
        "brokerAuthorityStatus": broker,
        "brokerAuthorityStatusLabel": _authority_label(broker),
        "authorizedForProperty": _code(raw.get("authorizedForProperty")),
        "authorizedForPassenger": _code(raw.get("authorizedForPassenger")),
        "authorizedForHouseholdGoods": _code(raw.get("authorizedForHouseholdGoods")),
        "authorizedForBroker": _code(raw.get("authorizedForBroker")),
    }


def _docket_numbers(records: list[dict[str, Any]]) -> list[str]:
    numbers: list[str] = []
    seen: set[str] = set()
    for record in records:
        docket = record.get("docketNumber")
        if not docket:
            continue
        prefix = record.get("prefix")
        label = f"{prefix}-{docket}" if prefix else str(docket)
        if label not in seen:
            seen.add(label)
            numbers.append(label)
    return numbers


def _prefer_code(snapshot: object, records: list[dict[str, Any]], field: str) -> str | None:
    code = _code(snapshot)
    if code:
        return code
    values = [item.get(field) for item in records if item.get(field)]
    if any(value == "A" for value in values):
        return "A"
    if any(value == "I" for value in values):
        return "I"
    if values:
        return str(values[0])
    return None


def _authority_label(code: str | None) -> str | None:
    if code is None:
        return None
    return _AUTHORITY_LABELS.get(code, code)


def _operating_status(allowed: str | None) -> str | None:
    if allowed == "Y":
        return "Allowed to operate"
    if allowed == "N":
        return "Not allowed to operate"
    if allowed is None:
        return None
    return allowed


def _requirement_label(code: str | None) -> str | None:
    if code is None:
        return None
    return _YES_NO_LABELS.get(code.upper(), code)


def thousands_to_usd(value: str | None) -> int | None:
    """Convert an FMCSA insurance amount from thousands of dollars to dollars."""
    if value is None:
        return None
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    if amount < 0:
        return None
    return int(amount * 1000)


def _code(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text or None


def _text(value: object) -> str | None:
    return _code(value)


def _stringify(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _as_int(value: object) -> int | None:
    if value is None or isinstance(value, bool) or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.lstrip("-").isdigit():
            return int(text)
    return None
