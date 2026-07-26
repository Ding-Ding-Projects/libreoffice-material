#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail closed when a build-free repository validator is absent from CI.

The project's fast gate is intentionally discoverable from the tree: every
project-authored ``bin/check-*.py`` checker (apart from six inherited upstream
linters), every ``bin/check_*.py`` checker, every ``bin/test_*.py`` mutation
suite, and ``bin/validate-prototype.mjs``.  A locally green script that is not
invoked by any workflow is not a CI gate, so this checker cross-references the
discovered fleet against executable workflow command lines.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
UPSTREAM_CHECK_EXCLUSIONS = frozenset(
    {
        "check-autocorr.py",
        "check-icon-sizes.py",
        "check-implementer-notes.py",
        "check-missing-export-asserts.py",
        "check-missing-unittests.py",
        "check-sid-slots.py",
    }
)

PYTHON_COMMAND = re.compile(
    r"(?m)^(?!\s*#)\s*(?:run:\s*)?"
    r"(?:python3|python|py(?:\s+-3)?)\s+(?:-m\s+unittest\s+)?"
    r"(bin/[A-Za-z0-9_.-]+\.py)(?:\s|$)"
)
NODE_COMMAND = re.compile(
    r"(?m)^(?!\s*#)\s*(?:run:\s*)?node\s+"
    r"(bin/validate-prototype\.mjs)(?:\s|$)"
)


class ValidationError(RuntimeError):
    pass


def discover_eligible_scripts(repo_root: Path = REPOSITORY) -> set[str]:
    bin_dir = repo_root / "bin"
    eligible = {
        path.relative_to(repo_root).as_posix()
        for path in bin_dir.glob("check-*.py")
        if path.name not in UPSTREAM_CHECK_EXCLUSIONS
    }
    eligible.update(
        path.relative_to(repo_root).as_posix() for path in bin_dir.glob("check_*.py")
    )
    eligible.update(
        path.relative_to(repo_root).as_posix() for path in bin_dir.glob("test_*.py")
    )
    prototype = bin_dir / "validate-prototype.mjs"
    if prototype.is_file():
        eligible.add(prototype.relative_to(repo_root).as_posix())
    return eligible


def load_workflows(repo_root: Path = REPOSITORY) -> dict[str, str]:
    workflow_dir = repo_root / ".github" / "workflows"
    workflows: dict[str, str] = {}
    for pattern in ("*.yml", "*.yaml"):
        for path in workflow_dir.glob(pattern):
            workflows[path.relative_to(repo_root).as_posix()] = path.read_text(
                encoding="utf-8"
            )
    return workflows


def referenced_scripts(workflows: Mapping[str, str]) -> set[str]:
    referenced: set[str] = set()
    for source in workflows.values():
        referenced.update(PYTHON_COMMAND.findall(source))
        referenced.update(NODE_COMMAND.findall(source))
    return referenced


def violations(
    eligible: set[str], workflows: Mapping[str, str]
) -> list[str]:
    errors: list[str] = []
    if not workflows:
        return ["workflows:none found under .github/workflows"]
    referenced = referenced_scripts(workflows)
    for path in sorted(eligible - referenced):
        errors.append(f"workflow-coverage:{path}:eligible build-free gate is not invoked")
    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> tuple[int, int]:
    eligible = discover_eligible_scripts(repo_root)
    workflows = load_workflows(repo_root)
    errors = violations(eligible, workflows)
    if errors:
        raise ValidationError("\n".join(errors))
    return len(eligible), len(referenced_scripts(workflows) & eligible)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        eligible_count, referenced_count = validate_repository(args.repo_root.resolve())
    except (OSError, ValidationError) as error:
        print(f"Build-free workflow coverage failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Build-free workflow coverage passed: "
        f"all {eligible_count} eligible scripts are invoked by CI "
        f"({referenced_count}/{eligible_count})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
