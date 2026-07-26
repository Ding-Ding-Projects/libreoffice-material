#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed contract for the repository's two GitHub release channels.

The stable GitHub ``Latest`` pointer is an application API: the website, README,
and native updater all resolve the verified MSI and update manifest through it.
The fast source-installer channel must therefore publish normal releases without
claiming Latest.  Release-tag creation also must not rerun the exhaustive Windows
UI contract suite for a commit already tested by its branch push.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE_WORKFLOW = ".github/workflows/source-installer.yml"
WINDOWS_WORKFLOW = ".github/workflows/windows-installer.yml"
CONTRACT_WORKFLOW = ".github/workflows/windows-ui-contract.yml"
README = "README.md"
SITE = "site/index.html"
MSI_NAME = "LibreOfficeMaterial-Windows-x64.msi"
LATEST_MSI_URL = (
    "https://github.com/Ding-Ding-Projects/libreoffice-material/"
    f"releases/latest/download/{MSI_NAME}"
)
FILES = (SOURCE_WORKFLOW, WINDOWS_WORKFLOW, CONTRACT_WORKFLOW, README, SITE)


class ValidationError(RuntimeError):
    pass


def load_repository(repo_root: Path = REPOSITORY) -> dict[str, str]:
    return {
        relative: (repo_root / relative).read_text(encoding="utf-8")
        for relative in FILES
        if (repo_root / relative).is_file()
    }


def _source_release_create_block(source: str) -> str | None:
    start = source.find('gh release create "$TAG"')
    if start < 0:
        return None
    end = source.find('published_draft="$(gh release view', start)
    if end < 0:
        return None
    return source[start:end]


def _contract_push_block(source: str) -> str | None:
    start = source.find("  push:")
    if start < 0:
        return None
    end = source.find("  pull_request:", start)
    if end < 0:
        return None
    return source[start:end]


def _windows_publish_run_block(source: str) -> str | None:
    step = source.find("      - name: Publish Windows MSI release")
    if step < 0:
        return None
    start = source.find("        run: |", step)
    if start < 0:
        return None
    end = source.find("      - name: Clean up failed draft release", start)
    if end < 0:
        return None
    return source[start:end]


def violations(contents: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    for relative in FILES:
        if relative not in contents:
            errors.append(f"source:{relative}:missing")

    source = contents.get(SOURCE_WORKFLOW, "")
    create_block = _source_release_create_block(source)
    if create_block is None:
        errors.append("source-release:create block not found")
    elif "--latest=false" not in create_block:
        errors.append("source-release:create must pass --latest=false")

    postcondition_markers = (
        'latest_tag="$(gh api -H \'Cache-Control: no-cache\'',
        'latest_msi_asset="$(gh api -H \'Cache-Control: no-cache\'',
        '[ "$latest_tag" = "$TAG" ]',
        f'[ "$latest_msi_asset" != "{MSI_NAME}" ]',
    )
    for marker in postcondition_markers:
        if marker not in source:
            errors.append(f"source-release:Latest postcondition missing {marker!r}")
    if source.count("verify_stable_latest_msi") != 3:
        errors.append(
            "source-release:stable Latest verifier must be defined once and called before and after publication"
        )
    tag_ref_markers = (
        'if ! tag_ref_count="$(gh api -H \'Cache-Control: no-cache\' \\',
        '"repos/$REPOSITORY/git/matching-refs/tags/$TAG"',
        '--jq "[.[] | select(.ref == \\"refs/tags/$TAG\\")] | length")"; then',
        'if [ "$tag_ref_count" != "0" ]; then',
    )
    for marker in tag_ref_markers:
        if marker not in source:
            errors.append(
                f"source-release:fail-closed exact-tag check missing {marker!r}"
            )

    contract = contents.get(CONTRACT_WORKFLOW, "")
    push_block = _contract_push_block(contract)
    if push_block is None:
        errors.append("contract-workflow:push trigger block not found")
    else:
        if "branches:" not in push_block or not re.search(
            r'(?m)^\s+-\s+["\']\*\*["\']\s*$', push_block
        ):
            errors.append(
                "contract-workflow:push must cover every branch with quoted '**'"
            )
        if re.search(r"(?m)^\s+tags(?:-ignore)?:", push_block):
            errors.append("contract-workflow:release-tag pushes must stay excluded")

    windows = contents.get(WINDOWS_WORKFLOW, "")
    publish_run = _windows_publish_run_block(windows)
    if publish_run is None:
        errors.append("windows-release:publish run block not found")
    else:
        if "${{" in publish_run:
            errors.append(
                "windows-release:large publish run must use GITHUB_* environment variables, not inline expressions"
            )
        for variable in (
            "GITHUB_SHA",
            "GITHUB_REPOSITORY",
            "GITHUB_RUN_ID",
            "GITHUB_RUN_NUMBER",
            "GITHUB_RUN_ATTEMPT",
        ):
            if f"$env:{variable}" not in publish_run:
                errors.append(
                    f"windows-release:publish run missing default environment variable {variable}"
                )
    monotonic_markers = (
        "group: ${{ github.ref == 'refs/heads/main' && 'windows-msi-stable-publisher' || format('windows-msi-nonpublisher-{0}', github.run_id) }}",
        "cancel-in-progress: false",
        "$promoteToLatest = $true",
        '"repos/$repository/compare/$latestBeforeCommit...$($env:GITHUB_SHA)"',
        "if ([string]$comparison.status -notin @('ahead', 'identical'))",
        "$latestMode = if ($promoteToLatest) { '--latest' } else { '--latest=false' }",
        "gh release edit $tag --draft=false --prerelease=false $latestMode --repo",
        "if (-not $promoteToLatest)",
        "function Test-StableLatestReleaseShape($releaseObject)",
        "-and (Test-StableLatestReleaseShape $preservedLatest)",
        "[long]$preservedLatest.id -eq [long]$latestBefore.id",
    )
    for marker in monotonic_markers:
        if marker not in windows:
            errors.append(f"windows-release:monotonic Latest marker missing {marker!r}")
    if "group: windows-msi-${{ github.sha }}" in windows:
        errors.append("windows-release:per-SHA concurrency permits out-of-order Latest writes")
    if windows.count("[string]$preservedLatest.tag_name -ne $tag") != 2:
        errors.append(
            "windows-release:historical release must never validate itself as Latest"
        )
    if windows.count("$promoteToLatest = $true") != 1:
        errors.append(
            "windows-release:promotion may be enabled only by its initial fail-safe default"
        )
    if windows.count("$promoteToLatest = $false") != 4:
        errors.append(
            "windows-release:all four API, target, compare, and ancestry failures must withhold promotion"
        )
    if "releases/latest/download/${encodedAssetName}" not in windows:
        errors.append("windows-release:public Latest asset-byte verification missing")

    for relative in (README, SITE):
        if LATEST_MSI_URL not in contents.get(relative, ""):
            errors.append(f"download-surface:{relative}:canonical Latest MSI URL drifted")

    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    errors = violations(load_repository(repo_root))
    if errors:
        raise ValidationError("\n".join(errors))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        validate_repository(args.repo_root.resolve())
    except (OSError, ValidationError) as error:
        print(f"Release-channel integrity failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Release-channel integrity passed: source packages are explicitly non-Latest, "
        "their publish step proves the stable MSI route survived, verified MSI releases "
        "own Latest, the large publisher avoids inline-expression limits, public links "
        "stay canonical, and tag creation cannot duplicate the branch contract run."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
