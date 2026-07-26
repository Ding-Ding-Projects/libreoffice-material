#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for stable/source GitHub release-channel separation."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-release-channel-integrity.py"
SPEC = importlib.util.spec_from_file_location("check_release_channel_integrity", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class ReleaseChannelIntegrityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contents = VALIDATOR.load_repository(REPOSITORY)

    def failures(self, contents: dict[str, str] | None = None) -> list[str]:
        return VALIDATOR.violations(self.contents if contents is None else contents)

    def mutate(self, path: str, old: str, new: str) -> dict[str, str]:
        contents = dict(self.contents)
        self.assertIn(old, contents[path])
        contents[path] = contents[path].replace(old, new, 1)
        return contents

    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    def test_source_release_cannot_claim_latest(self) -> None:
        contents = self.mutate(
            VALIDATOR.SOURCE_WORKFLOW,
            "            --latest=false \\\n",
            "",
        )
        errors = self.failures(contents)
        self.assertTrue(any("must pass --latest=false" in e for e in errors), errors)

    def test_source_release_latest_tag_postcondition_is_required(self) -> None:
        contents = self.mutate(
            VALIDATOR.SOURCE_WORKFLOW,
            '[ "$latest_tag" = "$TAG" ]',
            '[ "$latest_tag" = "impossible" ]',
        )
        errors = self.failures(contents)
        self.assertTrue(any("Latest postcondition" in e for e in errors), errors)

    def test_source_release_latest_msi_asset_postcondition_is_required(self) -> None:
        contents = self.mutate(
            VALIDATOR.SOURCE_WORKFLOW,
            '[ "$latest_msi_asset" != "LibreOfficeMaterial-Windows-x64.msi" ]',
            '[ "$latest_msi_asset" != "anything" ]',
        )
        errors = self.failures(contents)
        self.assertTrue(any("Latest postcondition" in e for e in errors), errors)

    def test_bare_push_trigger_would_reenable_release_tag_runs(self) -> None:
        contents = self.mutate(
            VALIDATOR.CONTRACT_WORKFLOW,
            '  push:\n    # Run on every branch push, but not on release-tag creation. The source\n'
            '    # installer publishes a tag after each main push; accepting tag pushes here\n'
            '    # used to run this exhaustive suite twice for the same commit.\n'
            '    branches:\n      - "**"\n',
            "  push:\n",
        )
        errors = self.failures(contents)
        self.assertTrue(any("every branch" in e for e in errors), errors)

    def test_main_only_trigger_would_drop_other_branch_pushes(self) -> None:
        contents = self.mutate(
            VALIDATOR.CONTRACT_WORKFLOW,
            '      - "**"',
            "      - main",
        )
        errors = self.failures(contents)
        self.assertTrue(any("every branch" in e for e in errors), errors)

    def test_windows_release_must_promote_verified_msi_to_latest(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "gh release edit $tag --draft=false --prerelease=false --latest",
            "gh release edit $tag --draft=false --prerelease=false --latest=false",
        )
        errors = self.failures(contents)
        self.assertTrue(any("must claim Latest" in e for e in errors), errors)

    def test_readme_download_route_is_pinned(self) -> None:
        contents = self.mutate(
            VALIDATOR.README,
            VALIDATOR.LATEST_MSI_URL,
            "https://example.invalid/not-the-msi",
        )
        errors = self.failures(contents)
        self.assertTrue(any("README.md" in e for e in errors), errors)

    def test_site_download_route_is_pinned(self) -> None:
        contents = self.mutate(
            VALIDATOR.SITE,
            VALIDATOR.LATEST_MSI_URL,
            "https://example.invalid/not-the-msi",
        )
        errors = self.failures(contents)
        self.assertTrue(any("site/index.html" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
