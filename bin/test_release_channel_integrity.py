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

    def test_source_release_requires_preflight_and_postflight(self) -> None:
        contents = self.mutate(
            VALIDATOR.SOURCE_WORKFLOW,
            "          # Fail before creating a release when the shared stable channel is\n"
            "          # already broken. A failed validation must not leave a new release.\n"
            "          verify_stable_latest_msi\n",
            "",
        )
        errors = self.failures(contents)
        self.assertTrue(any("before and after publication" in e for e in errors), errors)

    def test_source_release_rejects_a_preexisting_bare_tag(self) -> None:
        contents = self.mutate(
            VALIDATOR.SOURCE_WORKFLOW,
            '          if [ "$tag_ref_count" != "0" ]; then\n',
            '          if false; then\n',
        )
        errors = self.failures(contents)
        self.assertTrue(any("exact-tag check" in e for e in errors), errors)

    def test_source_tag_lookup_must_fail_closed_on_api_error(self) -> None:
        contents = self.mutate(
            VALIDATOR.SOURCE_WORKFLOW,
            "          if ! tag_ref_count=\"$(gh api -H 'Cache-Control: no-cache' \\\n",
            "          if tag_ref_count=\"$(gh api -H 'Cache-Control: no-cache' \\\n",
        )
        errors = self.failures(contents)
        self.assertTrue(any("exact-tag check" in e for e in errors), errors)

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

    def test_windows_release_publishers_must_be_serialized(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "group: ${{ github.ref == 'refs/heads/main' && 'windows-msi-stable-publisher' || format('windows-msi-nonpublisher-{0}', github.run_id) }}",
            "group: windows-msi-${{ github.sha }}",
        )
        errors = self.failures(contents)
        self.assertTrue(any("concurrency" in e or "monotonic" in e for e in errors), errors)

    def test_nonpublisher_dispatch_cannot_occupy_stable_queue(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "group: ${{ github.ref == 'refs/heads/main' && 'windows-msi-stable-publisher' || format('windows-msi-nonpublisher-{0}', github.run_id) }}",
            "group: windows-msi-stable-publisher",
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_windows_release_requires_ancestry_comparison(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            '"repos/$repository/compare/$latestBeforeCommit...$($env:GITHUB_SHA)"',
            '"repos/$repository/commits/$($env:GITHUB_SHA)"',
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_large_windows_publish_run_avoids_inline_expression_limit(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "$short = $env:GITHUB_SHA.Substring(0, 10)",
            "$short = '${{ github.sha }}'.Substring(0, 10)",
        )
        errors = self.failures(contents)
        self.assertTrue(any("inline expressions" in e for e in errors), errors)

    def test_windows_release_rejects_backward_comparison_status(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "if ([string]$comparison.status -notin @('ahead', 'identical'))",
            "if ([string]$comparison.status -in @('ahead', 'identical'))",
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_windows_release_queue_must_not_cancel_running_publisher(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "  cancel-in-progress: false",
            "  cancel-in-progress: true",
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_windows_release_requires_conditional_latest_mode(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "$latestMode = if ($promoteToLatest) { '--latest' } else { '--latest=false' }",
            "$latestMode = '--latest'",
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_windows_release_edit_must_use_conditional_mode(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "gh release edit $tag --draft=false --prerelease=false $latestMode --repo",
            "gh release edit $tag --draft=false --prerelease=false --latest --repo",
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_historical_release_must_preserve_latest_identity(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "[long]$preservedLatest.id -eq [long]$latestBefore.id",
            "$true",
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_historical_release_must_validate_preserved_asset_shape(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "-and (Test-StableLatestReleaseShape $preservedLatest)",
            "-and $true",
        )
        errors = self.failures(contents)
        self.assertTrue(any("monotonic Latest marker" in e for e in errors), errors)

    def test_promotion_cannot_be_reenabled_after_a_failed_guard(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "          $latestMode = if ($promoteToLatest)",
            "          $promoteToLatest = $true\n          $latestMode = if ($promoteToLatest)",
        )
        errors = self.failures(contents)
        self.assertTrue(any("enabled only" in e for e in errors), errors)

    def test_historical_release_cannot_validate_itself_as_latest(self) -> None:
        contents = self.mutate(
            VALIDATOR.WINDOWS_WORKFLOW,
            "[string]$preservedLatest.tag_name -ne $tag",
            "$true",
        )
        errors = self.failures(contents)
        self.assertTrue(any("never validate itself" in e for e in errors), errors)

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
