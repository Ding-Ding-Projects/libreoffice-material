#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Validate the explicit host-composed Material surface family fail closed.

These surfaces are deliberate exceptions to the ordinary static dialog/form
predicates, not exceptions to Material rendering.  Their visible controls ride
the unconditionally activated shared Windows Material definition while runtime
hosts own content, geometry, labels, or lifecycle semantics.  The contract
locks the exact exception set, every source byte digest, the still-failing
ordinary predicate, ledger classification/evidence, and the renderer contracts
that make composition evidence meaningful.

This is source-composition evidence only. ``runtime_verified`` remains false.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/host-composed-surfaces.json"
LEDGER_PATH = "qa/windows-ui-contract/material-rewrite-ledger.json"
AUDIT_PATH = "docs/design/material-rewrite-wave-2026-07-28-evidence.json"
LEDGER_CHECKER_PATH = "bin/check-material-rewrite-ledger.py"
MATERIAL_DEFINITION = "vcl/uiconfig/theme_definitions/material/definition.xml"
CONTRACT = "material-host-composed-surfaces"
EXPECTED_SURFACE_COUNT = 194
EXPECTED_SURFACE_SET_SHA256 = "7a6bd9a38fe7e4777b014e08c52599ea8840855cbde6f14c5e205dd674d7a68c"
EXPECTED_LEGACY_COUNTS = {"dialog": 64, "panel-fragment": 130}
EXPECTED_AUDIT_COUNTS = {
    "blocked-confirmed": 184,
    "re-audited-current-source": 10,
}
EXPECTED_DEPENDENCIES = {
    "qa/windows-ui-contract/material-default-activation.json":
        "material-default-activation",
    "qa/windows-ui-contract/component-gallery-coverage.json":
        "windows-component-gallery-coverage",
    "qa/windows-ui-contract/theme-resolution-routing.json":
        "material-theme-resolution-routing",
}
FAMILY = "host-composed-surface"
REWRITE_CLASS = "host-composition"
EVIDENCE_KIND = "composition-code"


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _load_ledger_checker(repo_root: Path):
    path = repo_root / LEDGER_CHECKER_PATH
    spec = importlib.util.spec_from_file_location("host_composed_ledger_checker", path)
    if spec is None or spec.loader is None:
        raise ValidationError(f"cannot load ledger checker from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _surface_set_digest(surfaces: Sequence[str]) -> str:
    payload = "\n".join(sorted(surfaces)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _variant(legacy_family: str, failure: str) -> str:
    if legacy_family == "panel-fragment":
        return "host-composed-fragment"
    if failure == "not modal":
        return "modeless-dialog"
    if failure == "no action-widgets footer":
        return "host-lifecycle-dialog"
    if failure.startswith("primary response") or failure.startswith("secondary response"):
        return "progress-close-or-choice-dialog"
    return "runtime-content-dialog"


def load_repository(
    repo_root: Path = REPOSITORY,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    registry = _read_json(repo_root / REGISTRY_PATH)
    ledger = _read_json(repo_root / LEDGER_PATH)
    audit = _read_json(repo_root / AUDIT_PATH)
    paths = {MATERIAL_DEFINITION, *EXPECTED_DEPENDENCIES}
    for row in registry.get("surfaces", []):
        if isinstance(row, Mapping) and isinstance(row.get("surface"), str):
            paths.add(row["surface"])
    contents = {
        path: (repo_root / path).read_text(encoding="utf-8")
        for path in paths
        if (repo_root / path).is_file()
    }
    return registry, ledger, audit, contents


def violations(
    registry: Mapping[str, Any],
    ledger: Mapping[str, Any],
    audit: Mapping[str, Any],
    contents: Mapping[str, str],
    *,
    repo_root: Path = REPOSITORY,
) -> list[str]:
    errors: list[str] = []
    checks = {
        "schema_version": 1,
        "contract": CONTRACT,
        "platform": "windows",
        "status": "source-declared",
        "runtime_verified": False,
        "generator": "bin/generate-host-composed-surface-contract.py",
        "ledger": LEDGER_PATH,
        "audit_source": AUDIT_PATH,
        "surface_count": EXPECTED_SURFACE_COUNT,
        "surface_set_sha256": EXPECTED_SURFACE_SET_SHA256,
    }
    for key, expected in checks.items():
        if registry.get(key) != expected:
            errors.append(
                f"registry: {key} is {registry.get(key)!r}, expected {expected!r}"
            )

    dependency_rows = registry.get("dependencies")
    dependency_map = {
        row.get("path"): row.get("contract_marker")
        for row in dependency_rows
        if isinstance(dependency_rows, list) and isinstance(row, Mapping)
    } if isinstance(dependency_rows, list) else {}
    if dependency_map != EXPECTED_DEPENDENCIES:
        errors.append("registry: renderer dependency set drifted")
    for path, marker in EXPECTED_DEPENDENCIES.items():
        payload = contents.get(path)
        if payload is None:
            errors.append(f"dependency: {path} is missing")
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as error:
            errors.append(f"dependency: {path} is invalid JSON: {error}")
            continue
        if not isinstance(data, Mapping) or data.get("contract") != marker:
            errors.append(f"dependency: {path} lost contract marker {marker!r}")
        if isinstance(data, Mapping) and data.get("runtime_verified") is True:
            errors.append(f"dependency: {path} cannot claim runtime verification here")
    if MATERIAL_DEFINITION not in contents:
        errors.append(f"dependency: {MATERIAL_DEFINITION} is missing")

    rows = registry.get("surfaces")
    if not isinstance(rows, list):
        errors.append("registry: surfaces must be a list")
        return errors
    surfaces = [row.get("surface") for row in rows if isinstance(row, Mapping)]
    if len(surfaces) != EXPECTED_SURFACE_COUNT:
        errors.append(
            f"registry: surface row count is {len(surfaces)}, expected {EXPECTED_SURFACE_COUNT}"
        )
    if len(surfaces) != len(set(surfaces)):
        errors.append("registry: surface paths must be unique")
    live_set_digest = _surface_set_digest(
        [surface for surface in surfaces if isinstance(surface, str)]
    )
    if live_set_digest != EXPECTED_SURFACE_SET_SHA256:
        errors.append(
            f"registry: surface set digest drifted: {live_set_digest} != "
            f"{EXPECTED_SURFACE_SET_SHA256}"
        )

    ledger_rows = {
        row.get("surface"): row
        for row in ledger.get("surfaces", [])
        if isinstance(row, Mapping) and isinstance(row.get("surface"), str)
    }
    audit_rows = {
        row.get("surface"): row
        for row in audit.get("surfaces", [])
        if isinstance(row, Mapping) and isinstance(row.get("surface"), str)
    }
    checker = _load_ledger_checker(repo_root)
    legacy_counts: Counter[str] = Counter()
    audit_counts: Counter[str] = Counter()

    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("registry: every surface row must be an object")
            continue
        surface = row.get("surface")
        if not isinstance(surface, str):
            errors.append("registry: every surface path must be a string")
            continue
        context = surface
        legacy_family = row.get("legacy_family")
        if legacy_family not in EXPECTED_LEGACY_COUNTS:
            errors.append(f"{context}: invalid legacy_family {legacy_family!r}")
            continue
        legacy_counts[legacy_family] += 1
        payload = contents.get(surface)
        if payload is None:
            errors.append(f"{context}: source file is missing")
            continue
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if row.get("source_sha256") != digest:
            errors.append(f"{context}: source_sha256 drifted")
        try:
            root = checker._parse_root(repo_root, surface)
            top_levels = [
                {"id": obj.get("id"), "class": obj.get("class")}
                for obj in checker._toplevel_objects(root)
            ]
            markers = checker.derive_static_markers(legacy_family, root)
            passed, failure = checker.static_predicate(legacy_family, markers)
        except Exception as error:  # checker surfaces a precise per-file diagnostic
            errors.append(f"{context}: cannot derive live structure: {error}")
            continue
        if passed:
            errors.append(
                f"{context}: ordinary {legacy_family} predicate now passes; migrate it "
                "out of the composition family"
            )
        if row.get("ordinary_predicate_failure") != failure:
            errors.append(
                f"{context}: predicate failure drifted: {failure!r} != "
                f"{row.get('ordinary_predicate_failure')!r}"
            )
        if row.get("marker_snapshot") != markers:
            errors.append(f"{context}: marker snapshot drifted")
        if row.get("top_level_objects") != top_levels:
            errors.append(f"{context}: top-level object identity drifted")
        if row.get("variant") != _variant(legacy_family, failure):
            errors.append(f"{context}: composition variant drifted")

        ledger_row = ledger_rows.get(surface)
        if not isinstance(ledger_row, Mapping):
            errors.append(f"{context}: ledger row is missing")
            continue
        expected_ledger = {
            "owner": row.get("owner"),
            "inventory_id": row.get("inventory_id"),
            "family": FAMILY,
            "rewrite_class": REWRITE_CLASS,
        }
        for key, expected in expected_ledger.items():
            if ledger_row.get(key) != expected:
                errors.append(
                    f"{context}: ledger {key} is {ledger_row.get(key)!r}, "
                    f"expected {expected!r}"
                )
        status = ledger_row.get("rewrite_status")
        if status == "rewritten-material":
            evidence = ledger_row.get("rewrite_evidence")
            markers_evidence = (
                evidence.get("anatomy_markers") if isinstance(evidence, Mapping) else None
            )
            if not isinstance(evidence, Mapping) or evidence.get("contract") != REGISTRY_PATH:
                errors.append(f"{context}: rewritten row must cite {REGISTRY_PATH}")
            if not isinstance(markers_evidence, Mapping) or markers_evidence.get(
                "contract_marker"
            ) != CONTRACT:
                errors.append(f"{context}: rewritten row lost the contract marker")
            if not isinstance(markers_evidence, Mapping) or markers_evidence.get(
                "evidence_kind"
            ) != EVIDENCE_KIND:
                errors.append(f"{context}: rewritten row must use composition-code evidence")
            if not isinstance(markers_evidence, Mapping) or markers_evidence.get(
                "source_sha256"
            ) != digest:
                errors.append(f"{context}: rewritten row source digest drifted")
            if not isinstance(markers_evidence, Mapping) or markers_evidence.get(
                "legacy_family"
            ) != legacy_family:
                errors.append(f"{context}: rewritten row legacy family drifted")
        elif status != "pending":
            errors.append(f"{context}: ledger status must be pending or rewritten-material")

        audit_info = row.get("audit")
        audit_status = audit_info.get("status") if isinstance(audit_info, Mapping) else None
        if audit_status not in EXPECTED_AUDIT_COUNTS:
            errors.append(f"{context}: invalid audit status {audit_status!r}")
        else:
            audit_counts[audit_status] += 1
        if audit_status == "blocked-confirmed":
            prior = audit_rows.get(surface)
            if not isinstance(prior, Mapping) or prior.get("verifier_verdict") != "blocked-confirmed":
                errors.append(f"{context}: blocked-confirmed audit provenance vanished")

    if dict(sorted(legacy_counts.items())) != EXPECTED_LEGACY_COUNTS:
        errors.append(
            f"registry: legacy family counts drifted: {dict(legacy_counts)!r} != "
            f"{EXPECTED_LEGACY_COUNTS!r}"
        )
    if registry.get("legacy_family_counts") != EXPECTED_LEGACY_COUNTS:
        errors.append("registry: declared legacy family counts drifted")
    if dict(sorted(audit_counts.items())) != EXPECTED_AUDIT_COUNTS:
        errors.append(
            f"registry: audit counts drifted: {dict(audit_counts)!r} != "
            f"{EXPECTED_AUDIT_COUNTS!r}"
        )
    if registry.get("audit_counts") != EXPECTED_AUDIT_COUNTS:
        errors.append("registry: declared audit counts drifted")
    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    registry, ledger, audit, contents = load_repository(repo_root)
    errors = violations(
        registry, ledger, audit, contents, repo_root=repo_root.resolve()
    )
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
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Host-composed surface contract failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Host-composed surface contract passed: 194 explicit audited resources "
        "retain source hashes, inapplicable ordinary predicates, shared Material "
        "renderer dependencies, and composition ledger ownership; "
        "runtime_verified=false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
