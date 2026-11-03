"""QCMobile client tests with mocked HTTP responses. No live FMCSA calls."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
import urllib.parse

from fmcsa_actor.client import FmcsaClient
from fmcsa_actor.errors import FmcsaApiError, FmcsaAuthError
from fmcsa_actor.input_parser import parse_input

WEB_KEY = "test-web-key-not-real"
OFFICIAL_PREFIX = "https://mobile.fmcsa.dot.gov/qc/services/"


class JsonResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "JsonResponse":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class ScriptedTransport:
    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.requests: list[object] = []

    def __call__(self, request: object, timeout: float | None = None) -> object:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError(f"unexpected request: {getattr(request, 'full_url', request)}")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def http_error(status: int, payload: object) -> urllib.error.HTTPError:
    body = json.dumps(payload).encode("utf-8")
    return urllib.error.HTTPError(
        OFFICIAL_PREFIX,
        status,
        "error",
        hdrs=None,
        fp=io.BytesIO(body),
    )


def carrier_payload() -> dict:
    return {
        "content": {
            "carrier": {
                "allowedToOperate": "Y",
                "bipdInsuranceOnFile": "750",
                "bipdInsuranceRequired": "Y",
                "bipdRequiredAmount": "750",
                "bondInsuranceOnFile": "0",
                "bondInsuranceRequired": "u",
                "brokerAuthorityStatus": "N",
                "cargoInsuranceOnFile": "0",
                "cargoInsuranceRequired": "N",
                "carrierOperation": {
                    "carrierOperationCode": "A",
                    "carrierOperationDesc": "Interstate",
                },
                "commonAuthorityStatus": "A",
                "contractAuthorityStatus": "N",
                "dotNumber": 1000001,
                "legalName": "EXAMPLE HAULING LLC",
                "phyCity": "DALLAS",
                "phyState": "TX",
                "safetyRating": "S",
                "safetyRatingDate": "2019-06-01",
                "statusCode": "A",
                "totalDrivers": 4,
                "totalPowerUnits": 3,
            }
        },
        "retrievalDate": "2026-03-01T00:00:00.000+0000",
    }


def authority_payload() -> dict:
    return {
        "content": [
            {
                "carrierAuthority": {
                    "prefix": "MC",
                    "docketNumber": 100001,
                    "dotNumber": 1000001,
                    "commonAuthorityStatus": "A",
                    "contractAuthorityStatus": "N",
                    "brokerAuthorityStatus": "N",
                    "authorizedForProperty": "Y",
                    "authorizedForPassenger": "N",
                    "authorizedForHouseholdGoods": "N",
                    "authorizedForBroker": "N",
                }
            }
        ],
        "retrievalDate": "2026-03-01T00:00:00.000+0000",
    }


def request_url(request: object) -> str:
    return str(getattr(request, "full_url"))


class ClientTests(unittest.TestCase):
    def test_dot_lookup_calls_official_carrier_and_authority_endpoints(self) -> None:
        transport = ScriptedTransport([JsonResponse(carrier_payload()), JsonResponse(authority_payload())])
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        rows = client.lookup_dot("1000001")

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["found"])
        self.assertEqual(row["queryType"], "dot")
        self.assertEqual(row["operatingStatus"], "Allowed to operate")
        self.assertEqual(row["commonAuthorityStatusLabel"], "Active")
        self.assertEqual(row["docketNumbers"], ["MC-100001"])
        self.assertEqual(row["bipdInsuranceOnFileUsd"], 750000)
        self.assertEqual(row["safetyRatingLabel"], "Satisfactory")
        self.assertEqual(row["source"], "FMCSA QCMobile API")
        self.assertNotIn(WEB_KEY, json.dumps(row))

        urls = [request_url(item) for item in transport.requests]
        self.assertEqual(
            urls[0].split("?", 1)[0],
            "https://mobile.fmcsa.dot.gov/qc/services/carriers/1000001",
        )
        self.assertEqual(
            urls[1].split("?", 1)[0],
            "https://mobile.fmcsa.dot.gov/qc/services/carriers/1000001/authority",
        )
        for url in urls:
            parsed = urllib.parse.urlsplit(url)
            self.assertEqual(parsed.netloc, "mobile.fmcsa.dot.gov")
            self.assertTrue(parsed.path.startswith("/qc/services/"))
            self.assertNotIn("safer", parsed.netloc)
            self.assertEqual(urllib.parse.parse_qs(parsed.query)["webKey"], [WEB_KEY])

    def test_docket_lookup_strips_prefix_before_the_api_call(self) -> None:
        docket_body = {
            "content": [carrier_payload()["content"]],
            "retrievalDate": carrier_payload()["retrievalDate"],
        }
        transport = ScriptedTransport([JsonResponse(docket_body), JsonResponse(authority_payload())])
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        request = parse_input({"webKey": WEB_KEY, "docketNumber": "MC-100001"})
        rows = client.lookup(request)

        self.assertEqual(rows[0]["query"], "MC-100001")
        self.assertEqual(rows[0]["queryType"], "docket")
        self.assertEqual(rows[0]["legalName"], "EXAMPLE HAULING LLC")
        path = urllib.parse.urlsplit(request_url(transport.requests[0])).path
        self.assertEqual(path, "/qc/services/carriers/docket-number/100001")

    def test_name_search_encodes_the_name_and_limits_results(self) -> None:
        second = json.loads(json.dumps(carrier_payload()["content"]))
        second["carrier"]["dotNumber"] = 1000002
        second["carrier"]["legalName"] = "OTHER EXAMPLE LLC"
        third = json.loads(json.dumps(carrier_payload()["content"]))
        third["carrier"]["dotNumber"] = 1000001
        name_body = {
            "content": [carrier_payload()["content"], second, third],
            "retrievalDate": "2026-03-01T00:00:00.000+0000",
        }
        transport = ScriptedTransport(
            [
                JsonResponse(name_body),
                JsonResponse(authority_payload()),
                JsonResponse(authority_payload()),
            ]
        )
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        rows = client.lookup_name("Example Hauling", 2)

        self.assertEqual([row["dotNumber"] for row in rows], ["1000001", "1000002"])
        parsed = urllib.parse.urlsplit(request_url(transport.requests[0]))
        self.assertEqual(parsed.path, "/qc/services/carriers/name/Example%20Hauling")
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["size"], ["2"])
        self.assertEqual(query["start"], ["0"])
        self.assertEqual(len(transport.requests), 3)

    def test_missing_carrier_does_not_request_authority(self) -> None:
        transport = ScriptedTransport(
            [JsonResponse({"content": None, "retrievalDate": "2026-03-01T00:00:00.000+0000"})]
        )
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        rows = client.lookup_dot("9999999")
        self.assertFalse(rows[0]["found"])
        self.assertEqual(rows[0]["message"], "No carrier found for that USDOT number.")
        self.assertEqual(len(transport.requests), 1)

    def test_not_found_http_404_is_an_empty_result(self) -> None:
        transport = ScriptedTransport([http_error(404, {"content": None})])
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        rows = client.lookup_dot("9999999")
        self.assertFalse(rows[0]["found"])

    def test_invalid_webkey_fails_without_echoing_the_key(self) -> None:
        transport = ScriptedTransport(
            [http_error(404, {"content": "Webkey not found", "retrievalDate": "2026-03-01T00:00:00.000+0000"})]
        )
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        with self.assertRaises(FmcsaAuthError) as caught:
            client.lookup_dot("1000001")
        self.assertNotIn(WEB_KEY, str(caught.exception))
        self.assertIn("WebKey", str(caught.exception))

    def test_authority_404_keeps_the_carrier_snapshot(self) -> None:
        transport = ScriptedTransport(
            [
                JsonResponse(carrier_payload()),
                http_error(404, {"content": None}),
            ]
        )
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        rows = client.lookup_dot("1000001")
        self.assertTrue(rows[0]["found"])
        self.assertEqual(rows[0]["commonAuthorityStatus"], "A")
        self.assertEqual(rows[0]["authorityRecords"], [])
        self.assertEqual(rows[0]["safetyRating"], "S")

    def test_maintenance_page_and_network_errors(self) -> None:
        class HtmlResponse(JsonResponse):
            def __init__(self) -> None:
                self.status = 200
                self._body = b"<html><title>FMCSA System Maintenance Page</title></html>"

        transport = ScriptedTransport([HtmlResponse()])
        client = FmcsaClient(WEB_KEY, urlopen=transport)
        with self.assertRaises(FmcsaApiError):
            client.lookup_dot("1000001")

        offline = ScriptedTransport([urllib.error.URLError("timed out")])
        client = FmcsaClient(WEB_KEY, urlopen=offline)
        with self.assertRaises(FmcsaApiError) as caught:
            client.lookup_dot("1000001")
        self.assertNotIn(WEB_KEY, str(caught.exception))

    def test_refuses_non_fmcsa_host_if_base_were_rewritten(self) -> None:
        # The host guard runs on the URL the client is about to send.
        client = FmcsaClient(WEB_KEY, urlopen=ScriptedTransport([]))
        with self.assertRaises(FmcsaApiError):
            client._get("https://safer.fmcsa.dot.gov/query.asp")


if __name__ == "__main__":
    unittest.main()
