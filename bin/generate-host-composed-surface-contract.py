#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Generate the explicit host-composed Material surface registry.

The ordinary dialog and panel predicates intentionally demand complete static
form anatomy.  Some registered surfaces cannot own that anatomy: they are
runtime-filled shells, modeless tools, progress/close-only dialogs, toolbar or
notebookbar roots, atomic controls, and child fragments whose labels and insets
belong to their host.  The adversarial 2026-07-28 audit proved that adding the
missing static markers would invent UI or break the host.

This generator snapshots that explicit exception set without relaxing either
ordinary predicate.  Every row records its legacy family, the exact live
predicate failure, a source digest, top-level identities, and the live marker
snapshot.  The matching checker ties those immutable resources to the shared
Windows Material renderer and fails closed on any source or classification
drift.  This is source-composition evidence only; runtime_verified stays false.
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
LEDGER_PATH = Path("qa/windows-ui-contract/material-rewrite-ledger.json")
AUDIT_PATH = Path("docs/design/material-rewrite-wave-2026-07-28-evidence.json")
OUTPUT_PATH = Path("qa/windows-ui-contract/host-composed-surfaces.json")
CHECKER_PATH = Path("bin/check-material-rewrite-ledger.py")
CONTRACT = "material-host-composed-surfaces"

# Surfaces may enter the composition family after the initial adversarial wave
# when a real runtime owner replaces a static-predicate workaround. Keep those
# promotions explicit so regeneration is deterministic and reviewable.
PROMOTED_HOST_COMPOSED_SURFACES = {
    "svx/uiconfig/ui/findbox.ui": "panel-fragment",
}


class GenerationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GenerationError(f"{path}: root must be an object")
    return value


def _load_ledger_checker(repo_root: Path):
    path = repo_root / CHECKER_PATH
    spec = importlib.util.spec_from_file_location("host_composed_ledger_checker", path)
    if spec is None or spec.loader is None:
        raise GenerationError(f"cannot load ledger checker from {path}")
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


def _initial_surface_rows(ledger: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for row in ledger.get("surfaces", []):
        if not isinstance(row, Mapping):
            continue
        if row.get("rewrite_status") != "pending":
            continue
        family = row.get("family")
        surface = row.get("surface")
        if family in {"dialog", "panel-fragment"} and isinstance(surface, str):
            rows.append((surface, family))
    return sorted(rows)


def _existing_surface_rows(contract: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for row in contract.get("surfaces", []):
        if not isinstance(row, Mapping):
            continue
        surface = row.get("surface")
        family = row.get("legacy_family")
        if isinstance(surface, str) and family in {"dialog", "panel-fragment"}:
            rows.append((surface, family))
    rows.extend(PROMOTED_HOST_COMPOSED_SURFACES.items())
    return sorted(set(rows))


def build_contract(repo_root: Path = REPOSITORY) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    ledger = _read_json(repo_root / LEDGER_PATH)
    audit = _read_json(repo_root / AUDIT_PATH)
    output = repo_root / OUTPUT_PATH
    previous = _read_json(output) if output.is_file() else None
    selected = (
        _existing_surface_rows(previous)
        if previous is not None
        else _initial_surface_rows(ledger)
    )
    if not selected:
        raise GenerationError("no host-composed surface candidates resolved")

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
    rows: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    audit_counts: Counter[str] = Counter()

    for surface, legacy_family in selected:
        ledger_row = ledger_rows.get(surface)
        if not isinstance(ledger_row, Mapping):
            raise GenerationError(f"{surface}: ledger row is missing")
        source = repo_root / surface
        if not source.is_file():
            raise GenerationError(f"{surface}: source file is missing")
        root = checker._parse_root(repo_root, surface)
        markers = checker.derive_static_markers(legacy_family, root)
        passed, failure = checker.static_predicate(legacy_family, markers)
        if passed:
            raise GenerationError(
                f"{surface}: ordinary {legacy_family} predicate now passes; remove it "
                "from the composition exception set"
            )
        top_levels = [
            {"id": obj.get("id"), "class": obj.get("class")}
            for obj in checker._toplevel_objects(root)
        ]
        prior_audit = audit_rows.get(surface)
        prior_verdict = (
            prior_audit.get("verifier_verdict")
            if isinstance(prior_audit, Mapping)
            else None
        )
        audit_status = (
            "blocked-confirmed"
            if prior_verdict == "blocked-confirmed"
            else "re-audited-current-source"
        )
        family_counts[legacy_family] += 1
        audit_counts[audit_status] += 1
        rows.append(
            {
                "surface": surface,
                "owner": ledger_row.get("owner"),
                "inventory_id": ledger_row.get("inventory_id"),
                "legacy_family": legacy_family,
                "variant": _variant(legacy_family, failure),
                "ordinary_predicate_failure": failure,
                "source_sha256": hashlib.sha256(
                    source.read_text(encoding="utf-8").encode("utf-8")
                ).hexdigest(),
                "top_level_objects": top_levels,
                "marker_snapshot": markers,
                "audit": {
                    "status": audit_status,
                    "prior_verdict": prior_verdict,
                },
            }
        )

    surfaces = [row["surface"] for row in rows]
    return {
        "schema_version": 1,
        "contract": CONTRACT,
        "platform": "windows",
        "status": "source-declared",
        "runtime_verified": False,
        "generator": OUTPUT_PATH.as_posix().replace(
            "qa/windows-ui-contract/host-composed-surfaces.json",
            "bin/generate-host-composed-surface-contract.py",
        ),
        "ledger": LEDGER_PATH.as_posix(),
        "audit_source": AUDIT_PATH.as_posix(),
        "design_reference": "docs/design/host-composed-material-surfaces.md",
        "note": (
            "Explicit fail-closed bridge for registered dialogs and fragments whose "
            "static form predicate is structurally inapplicable. Their controls render "
            "through the unconditionally activated shared Windows Material definition, "
            "while runtime hosts own page bodies, labels, lifecycle actions, geometry, "
            "or atomic-control composition. No fake labels, modal changes, affirmative "
            "buttons, or wrapper margins are introduced. Source evidence only."
        ),
        "dependencies": [
            {
                "path": "qa/windows-ui-contract/material-default-activation.json",
                "contract_marker": "material-default-activation",
            },
            {
                "path": "qa/windows-ui-contract/component-gallery-coverage.json",
                "contract_marker": "windows-component-gallery-coverage",
            },
            {
                "path": "qa/windows-ui-contract/theme-resolution-routing.json",
                "contract_marker": "material-theme-resolution-routing",
            },
        ],
        "surface_count": len(rows),
        "surface_set_sha256": _surface_set_digest(surfaces),
        "legacy_family_counts": dict(sorted(family_counts.items())),
        "audit_counts": dict(sorted(audit_counts.items())),
        "surfaces": rows,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    parser.add_argument("--check", action="store_true", help="fail if generated output differs")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        contract = build_contract(args.repo_root)
        output = args.repo_root.resolve() / OUTPUT_PATH
        rendered = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            current = output.read_text(encoding="utf-8") if output.is_file() else ""
            if current != rendered:
                raise GenerationError(f"{OUTPUT_PATH.as_posix()} is stale; regenerate it")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered, encoding="utf-8", newline="\n")
    except (OSError, json.JSONDecodeError, GenerationError) as error:
        print(f"Host-composed surface generation failed: {error}", file=sys.stderr)
        return 1
    action = "verified" if args.check else "generated"
    print(
        f"Host-composed surface contract {action}: {contract['surface_count']} explicit "
        f"surfaces ({contract['surface_set_sha256']}); runtime_verified=false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
