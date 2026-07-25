#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed inventory of the "frame topness" seams (tabbed-UI stage 1, analysis only).

LibreOffice assumes one document per top-level window: a document ``SfxViewFrame`` is
reached through a top-level ``WorkWindow`` / ``SystemWindow``. Document tabs (several view
frames hosted in one window) change which frames are "top", and the historical failure
mode of tdf#37134 was code that hard-assumes a document frame is a top-level ``WorkWindow``.

``qa/windows-ui-contract/frame-topness-seams.json`` is a static, build-free registry that
enumerates every call site of the topness-assuming APIs and classifies each one
(``host-owned`` / ``tab-owned`` / ``audited-safe``). This checker is the guardrail:

* it re-greps the tree with the *same* recorded patterns and paths and builds the current
  multiset of ``(file, snippet)`` call sites, then

* it FAILS CLOSED when that multiset differs from the registry in either direction -- a
  new topness-assuming call site that is absent from the registry (drift-in), or a
  registered call site that has disappeared from the tree (drift-out) -- and

* it FAILS CLOSED on any entry classified ``unaudited`` (or with an unknown
  classification), so new topness-assuming code cannot land without being registered *and*
  deliberately classified.

It also pins the exact per-family and grand totals so a silent count change fails.

This is source evidence only. ``runtime_verified`` is false: no native build, no tabs
runtime and no window-hosting behaviour are claimed -- only that the seams are inventoried.
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/frame-topness-seams.json"

VALID_CLASSIFICATIONS = frozenset({"host-owned", "tab-owned", "audited-safe"})
# 'unaudited' is intentionally excluded above: it is a legal vocabulary word in the
# registry but an illegal state for a passing entry -- the checker fails closed on it.


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _git_grep(repo_root: Path, pattern: str, paths: Sequence[str]) -> collections.Counter:
    """Return a Counter of (file, stripped-snippet) for ``git grep -nP pattern -- paths``."""
    result = subprocess.run(
        ["git", "grep", "-nP", pattern, "--", *paths],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    # git grep exits 1 with no output when there are no matches; that is a real drift
    # signal (a whole family vanished), not a tool error, so only a >1 code is fatal.
    if result.returncode not in (0, 1):
        raise ValidationError(
            f"git grep failed for pattern {pattern!r} (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )
    counter: collections.Counter = collections.Counter()
    for line in result.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        path, _lineno, code = parts
        counter[(path, code.strip())] += 1
    return counter


def load_registry(repo_root: Path = REPOSITORY) -> dict[str, Any]:
    return _read_json(repo_root / REGISTRY_PATH)


def _registry_counter(family: Mapping[str, Any], errors: list[str]) -> collections.Counter:
    counter: collections.Counter = collections.Counter()
    for entry in family.get("entries", []) or []:
        if not isinstance(entry, dict):
            errors.append(f"{family.get('api')}: entry must be an object")
            continue
        file = entry.get("file")
        snippet = entry.get("snippet")
        count = entry.get("count", 1)
        if not isinstance(file, str) or not isinstance(snippet, str):
            errors.append(f"{family.get('api')}: entry needs string file and snippet")
            continue
        if not isinstance(count, int) or count < 1:
            errors.append(f"{family.get('api')}:{file}: count must be a positive integer")
            continue
        classification = entry.get("classification")
        if classification == "unaudited":
            errors.append(
                f"{family.get('api')}:{file} :: {snippet!r} is classified 'unaudited' -- "
                "every topness seam must be reviewed and classified host-owned / tab-owned / "
                "audited-safe before it can pass (fail-closed on unaudited)"
            )
        elif classification not in VALID_CLASSIFICATIONS:
            errors.append(
                f"{family.get('api')}:{file} :: {snippet!r} has unknown classification "
                f"{classification!r} (expected one of {sorted(VALID_CLASSIFICATIONS)})"
            )
        counter[(file, snippet)] += count
    return counter


def violations(registry: Mapping[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []

    if registry.get("schema_version") != 1:
        errors.append("registry:schema_version:must be 1")
    if registry.get("contract") != "frame-topness-seams":
        errors.append("registry:contract:unexpected value")
    if registry.get("platform") != "windows":
        errors.append("registry:platform:must be windows")
    if registry.get("status") != "static-inventory":
        errors.append("registry:status:must be static-inventory")
    if not isinstance(registry.get("runtime_verified"), bool):
        errors.append("registry:runtime_verified:boolean required")
    elif registry["runtime_verified"]:
        errors.append(
            "registry:runtime_verified:this is a static source inventory; no runtime tabs "
            "capability exists, so runtime_verified must be false"
        )
    if not isinstance(registry.get("source_note"), str) or not registry["source_note"].strip():
        errors.append("registry:source_note:non-empty string required (state it is static)")

    families = registry.get("families")
    if not isinstance(families, list) or not families:
        errors.append("registry:families:non-empty array required")
        return errors

    grand_total_recorded = registry.get("grand_total_call_sites")
    grand_total_actual = 0

    for family in families:
        if not isinstance(family, dict):
            errors.append("registry:families:each family must be an object")
            continue
        api = family.get("api")
        pattern = family.get("pattern")
        paths = family.get("paths")
        recorded_total = family.get("total")
        if not isinstance(pattern, str) or not isinstance(paths, list) or not paths:
            errors.append(f"{api}: pattern (str) and paths (non-empty array) required")
            continue

        actual = _git_grep(repo_root, pattern, [str(p) for p in paths])
        registered = _registry_counter(family, errors)

        actual_total = sum(actual.values())
        grand_total_actual += actual_total
        if recorded_total != actual_total:
            errors.append(
                f"{api}: recorded total {recorded_total} != {actual_total} call sites found "
                f"in the tree for {pattern!r}"
            )

        # Drift-in: a call site in the tree with no (matching-count) registry entry.
        for key, n in actual.items():
            reg_n = registered.get(key, 0)
            if reg_n < n:
                file, snippet = key
                errors.append(
                    f"{api}: DRIFT (unregistered topness seam) {file} :: {snippet!r} appears "
                    f"{n}x in the tree but {reg_n}x in the registry -- a new topness-assuming "
                    "call site must be added to frame-topness-seams.json and classified"
                )
        # Drift-out: a registry entry that no longer matches the tree.
        for key, n in registered.items():
            act_n = actual.get(key, 0)
            if act_n < n:
                file, snippet = key
                errors.append(
                    f"{api}: STALE registry entry {file} :: {snippet!r} recorded {n}x but "
                    f"found {act_n}x in the tree -- remove or update the registry entry"
                )

    if grand_total_recorded != grand_total_actual:
        errors.append(
            f"registry:grand_total_call_sites {grand_total_recorded} != {grand_total_actual} "
            "call sites found across all families"
        )

    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    registry = load_registry(repo_root)
    errors = violations(registry, repo_root)
    if errors:
        raise ValidationError("\n".join(errors))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    try:
        validate_repository(repo_root)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Frame-topness seam inventory failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Frame-topness seam inventory passed: every GetSystemWindow / getTopSystemWindow / "
        "SetMenuBar / SetNotebookBar / createTask / static_cast<WorkWindow*> call site in the "
        "tree is registered in frame-topness-seams.json and classified (no 'unaudited'); the "
        "per-family and grand totals match. Static source inventory only -- no runtime tabs "
        "capability is claimed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
