"""The Actor calls the official API and does not include an owner license check."""

from __future__ import annotations

import unittest
from pathlib import Path

ACTOR_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ACTOR_ROOT / "fmcsa_actor"


class OfficialApiOnlyTests(unittest.TestCase):
    def test_package_does_not_include_an_owner_license_check(self) -> None:
        source = "\n".join(path.read_text(encoding="utf-8") for path in PACKAGE.rglob("*.py"))
        lowered = source.lower()
        self.assertNotIn("indus_license", lowered)
        self.assertNotIn("require_license", lowered)
        self.assertNotIn("license_token", lowered)
        self.assertNotIn("safer.fmcsa.dot.gov", lowered)
        self.assertNotIn("selenium", lowered)
        self.assertIn("https://mobile.fmcsa.dot.gov/qc/services/", source)

    def test_actor_metadata_points_at_the_official_api(self) -> None:
        readme = (ACTOR_ROOT / "README.md").read_text(encoding="utf-8")
        actor = (ACTOR_ROOT / ".actor" / "actor.json").read_text(encoding="utf-8")
        schema = (ACTOR_ROOT / ".actor" / "input_schema.json").read_text(encoding="utf-8")
        self.assertIn("official FMCSA", readme)
        self.assertIn("https://mobile.fmcsa.dot.gov/qc/services/", readme)
        self.assertIn("QCMobile", actor)
        self.assertIn('"isSecret": true', schema)
        self.assertIn("webKey", schema)


if __name__ == "__main__":
    unittest.main()
