"""Input parsing for USDOT, docket, and name searches."""

from __future__ import annotations

import unittest

from fmcsa_actor.input_parser import parse_input


class ParseInputTests(unittest.TestCase):
    def test_requires_web_key(self) -> None:
        with self.assertRaises(ValueError) as caught:
            parse_input({"dotNumber": "44110"})
        self.assertIn("webKey", str(caught.exception))
        self.assertIn("mobile.fmcsa.dot.gov", str(caught.exception))

    def test_requires_a_query(self) -> None:
        with self.assertRaises(ValueError) as caught:
            parse_input({"webKey": "secret-key"})
        self.assertIn("dotNumber", str(caught.exception))

    def test_normalizes_dot_docket_and_name(self) -> None:
        request = parse_input(
            {
                "webKey": "  secret-key  ",
                "dotNumber": "USDOT 0044110",
                "docketNumber": "mc-001515",
                "carrierName": "  Grey   Hound  ",
                "maxResults": "5",
            }
        )
        self.assertEqual(request.web_key, "secret-key")
        self.assertEqual(request.dot_number, "44110")
        self.assertEqual(request.docket_number, "1515")
        self.assertEqual(request.docket_query, "MC-1515")
        self.assertEqual(request.carrier_name, "Grey Hound")
        self.assertEqual(request.max_results, 5)
        self.assertNotIn("secret-key", repr(request))

    def test_accepts_ff_and_mx_prefixes(self) -> None:
        freight = parse_input({"webKey": "k", "docketNumber": "FF 42"})
        mexico = parse_input({"webKey": "k", "docketNumber": "MX-7"})
        self.assertEqual(freight.docket_query, "FF-42")
        self.assertEqual(mexico.docket_number, "7")

    def test_accepts_numeric_dot_from_json(self) -> None:
        request = parse_input({"webKey": "k", "dotNumber": 44110})
        self.assertEqual(request.dot_number, "44110")

    def test_rejects_bad_docket_and_short_name(self) -> None:
        with self.assertRaises(ValueError):
            parse_input({"webKey": "k", "docketNumber": "MC-"})
        with self.assertRaises(ValueError):
            parse_input({"webKey": "k", "carrierName": "A"})

    def test_rejects_max_results_outside_api_page(self) -> None:
        with self.assertRaises(ValueError):
            parse_input({"webKey": "k", "dotNumber": "1", "maxResults": 51})
        request = parse_input({"webKey": "k", "carrierName": "acme"})
        self.assertEqual(request.max_results, 10)


if __name__ == "__main__":
    unittest.main()
