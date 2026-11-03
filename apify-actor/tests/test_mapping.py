"""Dataset rows built from mocked FMCSA carrier and authority payloads."""

from __future__ import annotations

import unittest

from fmcsa_actor.mapping import SOURCE, SOURCE_URL, carrier_row, not_found, thousands_to_usd


CARRIER = {
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
    "contractAuthorityStatus": "I",
    "dotNumber": 1000001,
    "dbaName": None,
    "legalName": "EXAMPLE HAULING LLC",
    "oosDate": None,
    "phyCity": "DALLAS",
    "phyCountry": "US",
    "phyState": "TX",
    "phyStreet": "1 EXAMPLE ST",
    "phyZipcode": "75201",
    "safetyRating": "S",
    "safetyRatingDate": "2019-06-01",
    "safetyReviewDate": "2019-06-01",
    "safetyReviewType": "C",
    "statusCode": "A",
    "totalDrivers": 4,
    "totalPowerUnits": 3,
}

AUTHORITY = [
    {
        "prefix": "MC",
        "docketNumber": 100001,
        "dotNumber": 1000001,
        "commonAuthorityStatus": "A",
        "contractAuthorityStatus": "I",
        "brokerAuthorityStatus": "N",
        "authorizedForProperty": "Y",
        "authorizedForPassenger": "N",
        "authorizedForHouseholdGoods": "N",
        "authorizedForBroker": "N",
    }
]


class MappingTests(unittest.TestCase):
    def test_carrier_row_covers_authority_operation_insurance_and_rating(self) -> None:
        row = carrier_row("dot", "1000001", CARRIER, AUTHORITY, "2026-03-01T00:00:00.000+0000")

        self.assertTrue(row["found"])
        self.assertEqual(row["source"], SOURCE)
        self.assertEqual(row["sourceUrl"], SOURCE_URL)
        self.assertEqual(row["legalName"], "EXAMPLE HAULING LLC")
        self.assertEqual(row["dotNumber"], "1000001")
        self.assertEqual(row["docketNumbers"], ["MC-100001"])
        self.assertEqual(row["allowedToOperate"], "Y")
        self.assertEqual(row["operatingStatus"], "Allowed to operate")
        self.assertEqual(row["statusCode"], "A")
        self.assertEqual(row["statusLabel"], "Active")
        self.assertEqual(row["commonAuthorityStatus"], "A")
        self.assertEqual(row["commonAuthorityStatusLabel"], "Active")
        self.assertEqual(row["contractAuthorityStatus"], "I")
        self.assertEqual(row["contractAuthorityStatusLabel"], "Inactive")
        self.assertEqual(row["brokerAuthorityStatus"], "N")
        self.assertEqual(row["brokerAuthorityStatusLabel"], "None")
        self.assertEqual(row["authorityRecords"][0]["authorizedForProperty"], "Y")
        self.assertEqual(row["bipdInsuranceOnFile"], "750")
        self.assertEqual(row["bipdInsuranceOnFileUsd"], 750000)
        self.assertEqual(row["bipdRequiredAmountUsd"], 750000)
        self.assertEqual(row["bipdInsuranceRequiredLabel"], "Yes")
        self.assertEqual(row["cargoInsuranceOnFileUsd"], 0)
        self.assertEqual(row["bondInsuranceRequired"], "u")
        self.assertEqual(row["bondInsuranceRequiredLabel"], "Unknown")
        self.assertEqual(row["bondInsuranceOnFile"], "0")
        self.assertEqual(row["bondInsuranceOnFileUsd"], 0)
        self.assertEqual(row["safetyRating"], "S")
        self.assertEqual(row["safetyRatingLabel"], "Satisfactory")
        self.assertEqual(row["safetyRatingDate"], "2019-06-01")
        self.assertEqual(row["carrierOperation"], "Interstate")

    def test_missing_safety_rating_is_not_rated(self) -> None:
        carrier = dict(CARRIER)
        carrier["safetyRating"] = None
        carrier["safetyRatingDate"] = None
        row = carrier_row("dot", "1000001", carrier, [], None)
        self.assertIsNone(row["safetyRating"])
        self.assertEqual(row["safetyRatingLabel"], "Not rated")
        self.assertEqual(row["docketNumbers"], [])

    def test_authority_records_fill_missing_snapshot_status(self) -> None:
        carrier = dict(CARRIER)
        carrier["commonAuthorityStatus"] = None
        carrier["allowedToOperate"] = "N"
        row = carrier_row("docket", "MC-100001", carrier, AUTHORITY, None)
        self.assertEqual(row["commonAuthorityStatus"], "A")
        self.assertEqual(row["operatingStatus"], "Not allowed to operate")

    def test_not_found_row_still_names_the_official_api(self) -> None:
        row = not_found("name", "missing carrier", "No carrier found for that name.", None)
        self.assertFalse(row["found"])
        self.assertEqual(row["source"], "FMCSA QCMobile API")
        self.assertEqual(row["queryType"], "name")
        self.assertIsNone(row["safetyRatingLabel"])

    def test_thousands_conversion(self) -> None:
        self.assertEqual(thousands_to_usd("750"), 750000)
        self.assertEqual(thousands_to_usd("0"), 0)
        self.assertIsNone(thousands_to_usd("u"))
        self.assertIsNone(thousands_to_usd(None))


if __name__ == "__main__":
    unittest.main()
