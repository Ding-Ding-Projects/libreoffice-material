#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed coverage instrument for the non-.ui command-surface XML layer.

``qa/windows-ui-contract/config-layer-coverage.json`` enumerates every
toolbar / popupmenu / menubar / statusbar command list under ``*/uiconfig/**``
and maps each to the composition mechanism that renders it Material. This layer
is invisible to the WIN-SYS-016 surface closure (``ui-registry.json`` = 1260
``.ui`` + 10 native), so this registry is where "no command surface unaccounted
for" is proven. It edits no officecfg and no command XML -- it only records and
pins coverage.

The checker re-derives everything from the live tree and fails closed on:

* **file-set drift** -- a fresh ``git ls-files`` enumeration of the command-XML
  layer must match the registered file set exactly. A new command XML that is
  not registered (or a registered file that vanished) fails closed, listing the
  delta per family;
* **named contract disappearance** -- every contract/checker a *satisfied* entry
  or mechanism names must still exist on disk. A satisfied toolbar whose pinning
  contract (or its checker) was deleted, or a blanket mechanism whose contract /
  checker was removed, fails closed;
* **count mismatch** -- the ``counts`` block (total, per-family, satisfied /
  pending) must equal a fresh recompute from the registered entries;
* **satisfied-claim grounding** -- the *satisfied* toolbar set must equal the set
  of toolbar files actually pinned (as a ``"file"`` value) by the named toolbar
  Button-part chrome contracts (calc-chrome / writer-chrome / chart-editor /
  writer-review-composition). A registry that claims a toolbar is satisfied
  without the contract really pinning it -- or that mis-attributes the pin --
  fails closed. The blanket menu / statusbar families are satisfied at the chrome
  level (part-states in vcl code + definition.xml), so they carry no per-file
  pin and their whole live family set must be listed.

Enumeration mirrors ``bin/check-windows-ui-registry-closure.py``: a single
``git ls-files -z --cached --others --exclude-standard`` over the four command
directories, filtered to paths under a ``uiconfig/`` segment (dotdir / nested
worktree paths are skipped). Source evidence only: ``runtime_verified`` is false
throughout -- no build, command-surface pixels, or runtime interaction claimed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/config-layer-coverage.json"

FAMILIES = ("toolbar", "popupmenu", "menubar", "statusbar")

# A command XML is any toolbar/popupmenu/menubar/statusbar *.xml sitting under a
# ``uiconfig/`` path segment, at any depth (chart2 is a single-app module whose
# command dirs live directly under chart2/uiconfig/, not chart2/uiconfig/<app>/).
CLASSIFIER = re.compile(
    r"(?:^|/)uiconfig/(?:[^/]+/)*(toolbar|popupmenu|menubar|statusbar)/[^/]+\.xml$"
)
TOOLBAR_FILE = re.compile(r"(?:^|/)uiconfig/(?:[^/]+/)*toolbar/[^/]+\.xml$")

GIT_PATHSPECS = (
    "*/toolbar/*.xml",
    "*/popupmenu/*.xml",
    "*/menubar/*.xml",
    "*/statusbar/*.xml",
)

# The toolbar Button-part chrome-composition contracts named by the config
# partition, plus writer-review-composition which also pins a Writer toolbar
# (changes.xml) against the same shared native toolbar Button/Entire part. Order
# is the satisfied-attribution precedence (first contract to pin a file wins).
TOOLBAR_CONTRACTS: tuple[tuple[str, str, str], ...] = (
    ("calc-chrome",
     "qa/windows-ui-contract/calc-chrome.json",
     "bin/check-calc-chrome-contract.py"),
    ("writer-chrome",
     "qa/windows-ui-contract/writer-chrome.json",
     "bin/check-writer-chrome-contract.py"),
    ("chart-editor",
     "qa/windows-ui-contract/chart-editor.json",
     "bin/check-chart-editor-contract.py"),
    ("writer-review-composition",
     "qa/windows-ui-contract/writer-review-composition.json",
     "bin/check-windows-writer-review-composition.py"),
)

BLANKET_MECHANISMS = {
    "popupmenu": "menu-composition",
    "menubar": "menu-composition",
    "statusbar": "statusbar-composition",
}


class ValidationError(RuntimeError):
    pass


# --------------------------------------------------------------------------------------------------
# Live-tree derivation (git enumeration + contract grounding)
# --------------------------------------------------------------------------------------------------
def _git_command_xml(repo_root: Path) -> list[str]:
    command = [
        "git", "-C", str(repo_root), "ls-files", "-z",
        "--cached", "--others", "--exclude-standard", "--", *GIT_PATHSPECS,
    ]
    try:
        completed = subprocess.run(
            command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as error:
        raise ValidationError(f"cannot run git to discover command XML: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValidationError(f"git command-XML discovery failed: {detail}")
    seen: set[str] = set()
    paths: list[str] = []
    for raw in completed.stdout.decode("utf-8", errors="surrogateescape").split("\0"):
        if not raw:
            continue
        posix = PurePosixPath(raw).as_posix()
        # Skip dotdirs (e.g. a nested .claude/worktrees checkout): never a shipping
        # command surface, and git may surface them in some worktree layouts.
        if posix.startswith(".") or "/." in posix:
            continue
        if not (repo_root / posix).is_file():
            continue
        if posix not in seen:
            seen.add(posix)
            paths.append(posix)
    return paths


def enumerate_live(repo_root: Path) -> dict[str, list[str]]:
    """Return {family: sorted list of command XML paths} from the live tree."""
    families: dict[str, set[str]] = {family: set() for family in FAMILIES}
    for posix in _git_command_xml(repo_root):
        match = CLASSIFIER.search(posix)
        if match:
            families[match.group(1)].add(posix)
    return {family: sorted(members) for family, members in families.items()}


def _collect_file_values(obj: Any) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "file" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_collect_file_values(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_file_values(item))
    return found


def derive_toolbar_pins(repo_root: Path) -> dict[str, tuple[str, str, str]]:
    """file -> (contract_name, contract_json, checker_py) from the real contracts.

    Only contracts that still exist are read; a missing contract simply pins
    nothing (its disappearance is caught separately by the named-contract check).
    """
    pins: dict[str, tuple[str, str, str]] = {}
    for name, contract_rel, checker_rel in TOOLBAR_CONTRACTS:
        contract_path = repo_root / contract_rel
        if not contract_path.is_file():
            continue
        try:
            data = json.loads(contract_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValidationError(f"{contract_rel}: cannot read/parse: {error}") from error
        for value in _collect_file_values(data):
            if TOOLBAR_FILE.search(value):
                pins.setdefault(value, (name, contract_rel, checker_rel))
    return pins


# --------------------------------------------------------------------------------------------------
# Validation (pure: takes injected live state / pins / existence oracle)
# --------------------------------------------------------------------------------------------------
def _format_delta(added: Sequence[str], removed: Sequence[str], family: str) -> list[str]:
    errors: list[str] = []
    for path in added:
        errors.append(
            f"drift:{family}:live command XML not registered: {path} "
            "(regenerate config-layer-coverage.json)"
        )
    for path in removed:
        errors.append(
            f"drift:{family}:registered command XML no longer in tree: {path} "
            "(regenerate config-layer-coverage.json)"
        )
    return errors


def violations(
    registry: Mapping[str, Any],
    live: Mapping[str, Sequence[str]],
    toolbar_pins: Mapping[str, tuple[str, str, str]],
    exists: Callable[[str], bool],
) -> list[str]:
    errors: list[str] = []

    # ---- header ------------------------------------------------------------
    if registry.get("schema_version") != 1:
        errors.append("registry:schema_version:must be 1")
    if registry.get("contract") != "windows-config-layer-coverage":
        errors.append("registry:contract:unexpected value")
    if registry.get("platform") != "windows":
        errors.append("registry:platform:must be windows")
    if registry.get("status") != "source-declared":
        errors.append("registry:status:must be source-declared")
    if not isinstance(registry.get("runtime_verified"), bool):
        errors.append("registry:runtime_verified:boolean required")
    elif registry["runtime_verified"]:
        errors.append("registry:runtime_verified:no runtime evidence exists; must be false")

    glob = registry.get("glob")
    if not isinstance(glob, dict):
        errors.append("registry:glob:object required")
    else:
        if glob.get("classifier") != CLASSIFIER.pattern:
            errors.append(
                "registry:glob:classifier drifted from the checker's canonical pattern"
            )
        if list(glob.get("families") or []) != list(FAMILIES):
            errors.append("registry:glob:families must list toolbar,popupmenu,menubar,statusbar")

    families = registry.get("families")
    if not isinstance(families, dict):
        errors.append("registry:families:object required")
        return errors  # nothing more can be checked coherently

    # ---- per-family declared sets + drift ----------------------------------
    declared: dict[str, set[str]] = {}
    fam_satisfied: dict[str, int] = {}
    fam_pending: dict[str, int] = {}
    for family in FAMILIES:
        block = families.get(family)
        if not isinstance(block, dict):
            errors.append(f"families:{family}:object required")
            declared[family] = set()
            fam_satisfied[family] = 0
            fam_pending[family] = 0
            continue
        if family == "toolbar":
            files, sat, pend = _validate_toolbar_block(block, toolbar_pins, errors)
        else:
            files, sat, pend = _validate_blanket_block(family, block, errors)
        declared[family] = files
        fam_satisfied[family] = sat
        fam_pending[family] = pend

        live_set = set(live.get(family, ()))
        # every declared file must classify into THIS family
        for path in sorted(files):
            match = CLASSIFIER.search(path)
            if match is None:
                errors.append(f"families:{family}:{path} is not a command XML under uiconfig/")
            elif match.group(1) != family:
                errors.append(
                    f"families:{family}:{path} is a {match.group(1)} file, mis-filed"
                )
        added = sorted(live_set - files)
        removed = sorted(files - live_set)
        errors.extend(_format_delta(added, removed, family))

    # ---- no file appears in two families -----------------------------------
    seen_global: dict[str, str] = {}
    for family in FAMILIES:
        for path in declared[family]:
            other = seen_global.get(path)
            if other is not None:
                errors.append(f"duplicate:{path} listed in both {other} and {family}")
            else:
                seen_global[path] = family

    # ---- counts ------------------------------------------------------------
    counts = registry.get("counts")
    if not isinstance(counts, dict):
        errors.append("registry:counts:object required")
    else:
        by_family = counts.get("by_family")
        expected_by_family = {family: len(declared[family]) for family in FAMILIES}
        if by_family != expected_by_family:
            errors.append(
                f"counts:by_family {by_family} != recompute {expected_by_family}"
            )
        expected_total = sum(expected_by_family.values())
        if counts.get("total") != expected_total:
            errors.append(f"counts:total {counts.get('total')} != recompute {expected_total}")
        by_status = counts.get("by_status")
        expected_status = {
            "satisfied": sum(fam_satisfied.values()),
            "pending": sum(fam_pending.values()),
        }
        if by_status != expected_status:
            errors.append(f"counts:by_status {by_status} != recompute {expected_status}")

    # ---- mechanisms block + named-contract existence -----------------------
    _validate_mechanisms(registry, errors)
    for contract_rel, checker_rel, why in _referenced_contracts(registry):
        if not exists(contract_rel):
            errors.append(f"named-contract:{why}:contract missing on disk: {contract_rel}")
        if not exists(checker_rel):
            errors.append(f"named-contract:{why}:checker missing on disk: {checker_rel}")

    return errors


def _validate_blanket_block(
    family: str, block: Mapping[str, Any], errors: list[str]
) -> tuple[set[str], int, int]:
    if block.get("status") != "satisfied":
        errors.append(f"families:{family}:blanket family must be status=satisfied")
    expected_mech = BLANKET_MECHANISMS[family]
    if block.get("mechanism") != expected_mech:
        errors.append(f"families:{family}:mechanism must be {expected_mech}")
    if not isinstance(block.get("contract"), str) or not isinstance(block.get("checker"), str):
        errors.append(f"families:{family}:contract and checker strings required")
    files = block.get("files")
    if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
        errors.append(f"families:{family}:files must be a list of strings")
        return set(), 0, 0
    file_set = set(files)
    if len(file_set) != len(files):
        errors.append(f"families:{family}:files contains duplicates")
    if block.get("count") != len(file_set):
        errors.append(f"families:{family}:count {block.get('count')} != {len(file_set)}")
    # blanket => every file satisfied, none pending
    return file_set, len(file_set), 0


def _validate_toolbar_block(
    block: Mapping[str, Any],
    toolbar_pins: Mapping[str, tuple[str, str, str]],
    errors: list[str],
) -> tuple[set[str], int, int]:
    if block.get("mechanism") != "toolbar-button-part":
        errors.append("families:toolbar:mechanism must be toolbar-button-part")

    satisfied = block.get("satisfied")
    pending = block.get("pending")
    if not isinstance(satisfied, list):
        errors.append("families:toolbar:satisfied must be a list")
        satisfied = []
    if not isinstance(pending, list) or not all(isinstance(f, str) for f in pending):
        errors.append("families:toolbar:pending must be a list of strings")
        pending = []

    satisfied_files: dict[str, tuple[str, str, str]] = {}
    for entry in satisfied:
        if not isinstance(entry, dict):
            errors.append("families:toolbar:satisfied entry must be an object")
            continue
        path = entry.get("file")
        if not isinstance(path, str):
            errors.append("families:toolbar:satisfied entry missing file")
            continue
        pinned_by = entry.get("pinned_by")
        contract = entry.get("contract")
        checker = entry.get("checker")
        if not (isinstance(pinned_by, str) and isinstance(contract, str) and isinstance(checker, str)):
            errors.append(f"families:toolbar:{path} missing pinned_by/contract/checker")
            continue
        satisfied_files[path] = (pinned_by, contract, checker)

    pending_set = set(pending)
    if len(pending_set) != len(pending):
        errors.append("families:toolbar:pending contains duplicates")

    overlap = satisfied_files.keys() & pending_set
    for path in sorted(overlap):
        errors.append(f"families:toolbar:{path} listed as both satisfied and pending")

    # ---- grounding: satisfied set must equal the real contract pins --------
    claimed = set(satisfied_files)
    grounded = set(toolbar_pins)
    for path in sorted(claimed - grounded):
        errors.append(
            f"grounding:toolbar:{path} claimed satisfied but no named contract pins it"
        )
    for path in sorted(grounded - claimed):
        name = toolbar_pins[path][0]
        errors.append(
            f"grounding:toolbar:{path} is pinned by {name} but not listed satisfied "
            "(regenerate config-layer-coverage.json)"
        )
    for path in sorted(claimed & grounded):
        want = toolbar_pins[path]
        got = satisfied_files[path]
        if got != want:
            errors.append(
                f"grounding:toolbar:{path} attribution {got} != real pin {want}"
            )

    # ---- count fields ------------------------------------------------------
    files = set(satisfied_files) | pending_set
    if block.get("count") != len(files):
        errors.append(f"families:toolbar:count {block.get('count')} != {len(files)}")
    if block.get("satisfied_count") != len(satisfied_files):
        errors.append(
            f"families:toolbar:satisfied_count {block.get('satisfied_count')} "
            f"!= {len(satisfied_files)}"
        )
    if block.get("pending_count") != len(pending_set):
        errors.append(
            f"families:toolbar:pending_count {block.get('pending_count')} != {len(pending_set)}"
        )
    return files, len(satisfied_files), len(pending_set)


def _validate_mechanisms(registry: Mapping[str, Any], errors: list[str]) -> None:
    mechanisms = registry.get("mechanisms")
    if not isinstance(mechanisms, dict):
        errors.append("registry:mechanisms:object required")
        return
    for name in ("menu-composition", "statusbar-composition", "toolbar-button-part"):
        if name not in mechanisms:
            errors.append(f"mechanisms:{name}:missing")
    # applies_to coherence for the blanket families
    for family, mech_name in BLANKET_MECHANISMS.items():
        mech = mechanisms.get(mech_name)
        if isinstance(mech, dict) and family not in (mech.get("applies_to") or []):
            errors.append(f"mechanisms:{mech_name}:applies_to must include {family}")
    toolbar_mech = mechanisms.get("toolbar-button-part")
    if isinstance(toolbar_mech, dict) and "toolbar" not in (toolbar_mech.get("applies_to") or []):
        errors.append("mechanisms:toolbar-button-part:applies_to must include toolbar")


def _referenced_contracts(registry: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    """Every (contract_rel, checker_rel, why) a satisfied/mechanism entry names."""
    refs: list[tuple[str, str, str]] = []
    mechanisms = registry.get("mechanisms")
    if isinstance(mechanisms, dict):
        for mech_name, mech in mechanisms.items():
            if not isinstance(mech, dict):
                continue
            if isinstance(mech.get("contract"), str) and isinstance(mech.get("checker"), str):
                refs.append((mech["contract"], mech["checker"], f"mechanism:{mech_name}"))
            for sub in mech.get("contracts", []) or []:
                if isinstance(sub, dict) and isinstance(sub.get("contract"), str) \
                        and isinstance(sub.get("checker"), str):
                    refs.append((sub["contract"], sub["checker"],
                                 f"mechanism:{mech_name}:{sub.get('name')}"))
    families = registry.get("families")
    if isinstance(families, dict):
        for family in ("popupmenu", "menubar", "statusbar"):
            block = families.get(family)
            if isinstance(block, dict) and isinstance(block.get("contract"), str) \
                    and isinstance(block.get("checker"), str):
                refs.append((block["contract"], block["checker"], f"family:{family}"))
        toolbar = families.get("toolbar")
        if isinstance(toolbar, dict):
            for entry in toolbar.get("satisfied", []) or []:
                if isinstance(entry, dict) and isinstance(entry.get("contract"), str) \
                        and isinstance(entry.get("checker"), str):
                    refs.append((entry["contract"], entry["checker"],
                                 f"toolbar:{entry.get('file')}"))
    return refs


# --------------------------------------------------------------------------------------------------
# Top-level wiring
# --------------------------------------------------------------------------------------------------
def load_registry(repo_root: Path) -> dict[str, Any]:
    path = repo_root / REGISTRY_PATH
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{REGISTRY_PATH}: root must be an object")
    return value


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    registry = load_registry(repo_root)
    live = enumerate_live(repo_root)
    toolbar_pins = derive_toolbar_pins(repo_root)
    exists = lambda rel: (repo_root / rel).is_file()
    errors = violations(registry, live, toolbar_pins, exists)
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
        print(f"Config-layer coverage contract failed:\n{error}", file=sys.stderr)
        return 1
    registry = load_registry(repo_root)
    counts = registry.get("counts", {})
    by_status = counts.get("by_status", {})
    print(
        "Config-layer coverage contract passed: "
        f"{counts.get('total')} command XML under */uiconfig/** "
        f"({by_status.get('satisfied')} satisfied, {by_status.get('pending')} pending); "
        "file-set, counts, named contracts, and toolbar pins all consistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
