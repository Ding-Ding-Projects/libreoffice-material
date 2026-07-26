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
    if (
        "gh release edit $tag --draft=false --prerelease=false --latest --repo"
        not in windows
    ):
        errors.append("windows-release:verified MSI promotion must claim Latest")
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
        "own Latest, public links stay canonical, and tag creation cannot duplicate the "
        "branch contract run."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
