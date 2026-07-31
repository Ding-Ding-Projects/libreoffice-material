#!/usr/bin/env python3
"""Fail-closed ownership contract for pending native Material surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPOSITORY = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("qa/windows-ui-contract/pending-native-surface-ownership.json")
LEDGER_PATH = Path("qa/windows-ui-contract/material-rewrite-ledger.json")
DESIGN_PATH = Path("docs/design/blocked-surface-material-proposal.md")

EXPECTED = {
    "native:updater-lifecycle-ui": ("native-shell", "extensions", "WIN-SYS-012"),
    "native:writer-document-canvas": ("native-shell", "sw", "WIN-WR-002"),
}


class ValidationError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def violations(repo: Path = REPOSITORY) -> list[str]:
    errors: list[str] = []
    contract = _json(repo / CONTRACT_PATH)
    ledger = _json(repo / LEDGER_PATH)

    if contract.get("contract") != "material-pending-native-surface-ownership":
        errors.append("contract marker drift")
    if contract.get("status") != "design-specified-not-wired":
        errors.append("status must remain design-specified-not-wired")
    if contract.get("runtime_verified") is not False:
        errors.append("runtime_verified must remain false")

    entries = contract.get("governed_surfaces")
    if not isinstance(entries, list):
        return errors + ["governed_surfaces must be a list"]
    by_surface = {entry.get("surface"): entry for entry in entries if isinstance(entry, dict)}
    if set(by_surface) != set(EXPECTED):
        errors.append(f"governed surface set drift: {sorted(by_surface)}")

    design = (repo / DESIGN_PATH).read_text(encoding="utf-8")
    ledger_rows = {row.get("surface"): row for row in ledger.get("surfaces", [])}
    for surface, (family, owner, inventory_id) in EXPECTED.items():
        entry = by_surface.get(surface)
        if not isinstance(entry, dict):
            continue
        for key, expected in (("family", family), ("owner", owner), ("inventory_id", inventory_id)):
            if entry.get(key) != expected:
                errors.append(f"{surface}: {key} drift")
        if surface not in design:
            errors.append(f"{surface}: missing from design proposal")

        sources = [entry]
        runtime_sources = entry.get("runtime_sources", [])
        if isinstance(runtime_sources, list):
            sources.extend(item for item in runtime_sources if isinstance(item, dict))
        for source_entry in sources:
            relative = source_entry.get("source")
            markers = source_entry.get("required_markers")
            if not isinstance(relative, str) or not isinstance(markers, list):
                errors.append(f"{surface}: malformed source marker entry")
                continue
            path = repo / relative
            if not path.is_file():
                errors.append(f"{surface}: missing owner source {relative}")
                continue
            text = path.read_text(encoding="utf-8")
            for marker in markers:
                if not isinstance(marker, str) or marker not in text:
                    errors.append(f"{surface}: missing marker {marker!r} in {relative}")

        related = entry.get("related_contract")
        if related is not None and not (isinstance(related, str) and (repo / related).is_file()):
            errors.append(f"{surface}: missing related contract")

        row = ledger_rows.get(surface)
        if not isinstance(row, dict):
            errors.append(f"{surface}: missing ledger row")
            continue
        if row.get("family") != family or row.get("owner") != owner:
            errors.append(f"{surface}: ledger owner/family drift")
        if row.get("rewrite_status") != "pending":
            errors.append(f"{surface}: must remain pending until implementation contract exists")
        evidence = row.get("rewrite_evidence")
        if not isinstance(evidence, dict) or any(evidence.get(key) for key in ("commit", "contract", "capture")):
            errors.append(f"{surface}: pending implementation evidence must remain empty")
    return errors


def validate(repo: Path = REPOSITORY) -> None:
    errors = violations(repo)
    if errors:
        raise ValidationError("\n".join(errors))


def main() -> int:
    try:
        validate()
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Pending native-surface ownership contract failed:\n{error}")
        return 1
    print("Pending native-surface ownership contract passed: 2 native shells are owner-pinned, design-specified, runtime-unverified, and ledger-pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
