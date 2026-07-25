#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed source contract for the Material notification overlay shell (WIN-SHL-003).

``qa/windows-ui-contract/notification-overlay-composition.json`` pins the
project-authored composition behind the ``native:notification-overlay-window``
rewrite-ledger row and cross-validates it against the real tree:

* ``host`` -- ``NotificationOverlayWindow`` must stay an ``InterimItemWindow`` child of
  the owning frame and must keep the bottom-right anchoring arithmetic and the
  raise-without-focus ``SetZOrder`` call. The ``absent_markers`` guard fails closed if
  the vehicle is ever turned back into a ``FloatingWindow``/``WorkWindow`` (either would
  auto-dismiss on focus loss or become an OS top-level, breaking the non-blocking
  corner-anchored contract).
* ``anchoring_defaults`` -- the Material anchoring numbers (420 width, 16/16 insets, 3
  visible cards) must remain the declared defaults on ``NotificationPreferences``.
* ``controller`` -- ``NotificationStackController`` must load the Material stack ``.ui``,
  pass the preference insets/width into ``RepositionBottomRight`` and keep the
  Tab-escapes-to-document focus behaviour.
* ``stack_ui`` -- the stack ``.ui`` must stay a non-dialog ``GtkBox`` top level with the
  Material 9px rhythm and must declare every widget id the controller welds.
* ``governed_surfaces`` -- every enumerated surface must exist in the rewrite ledger with
  the declared family, and any such row already credited ``rewritten-material`` must name
  this contract through ``rewrite_evidence.anatomy_markers.contract_marker``.

Source evidence only: ``runtime_verified`` is false -- no native build, overlay pixels or
runtime capture are claimed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/notification-overlay-composition.json"
CONTRACT_NAME = "material-notification-overlay-composition"
LEDGER_PATH = "qa/windows-ui-contract/material-rewrite-ledger.json"
REWRITTEN = "rewritten-material"


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _without_cpp_comments(source: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", source, flags=re.DOTALL)


def _declared_sources(registry: Mapping[str, Any]) -> set[str]:
    paths: set[str] = set()
    host = registry.get("host")
    if isinstance(host, Mapping):
        for key in ("header", "source"):
            if isinstance(host.get(key), str):
                paths.add(host[key])
    for section in ("anchoring_defaults", "controller"):
        block = registry.get(section)
        if isinstance(block, Mapping) and isinstance(block.get("source"), str):
            paths.add(block["source"])
    stack = registry.get("stack_ui")
    if isinstance(stack, Mapping) and isinstance(stack.get("ui_file"), str):
        paths.add(stack["ui_file"])
    return paths


def load_repository(repo_root: Path = REPOSITORY) -> tuple[dict[str, Any], dict[str, str]]:
    registry = _read_json(repo_root / REGISTRY_PATH)
    contents: dict[str, str] = {}
    for relative in _declared_sources(registry) | {LEDGER_PATH}:
        path = repo_root / relative
        if path.is_file():
            contents[relative] = path.read_text(encoding="utf-8")
    return registry, contents


# --------------------------------------------------------------------------------------------------
# Section validators
# --------------------------------------------------------------------------------------------------
def _validate_host(host: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]) -> None:
    for key, marker_key in (("header", "header_markers"), ("source", "source_markers")):
        relative = host.get(key)
        text = contents.get(relative) if isinstance(relative, str) else None
        if text is None:
            errors.append(f"host:{key} {relative} missing")
            continue
        code = _without_cpp_comments(text)
        for marker in host.get(marker_key, []) or []:
            if isinstance(marker, str) and marker not in code:
                errors.append(f"host:{key}:marker missing in code ({marker})")

    relative = host.get("source")
    text = contents.get(relative) if isinstance(relative, str) else None
    if text is None:
        return
    code = _without_cpp_comments(text)
    absent = host.get("absent_markers")
    if not isinstance(absent, list) or not absent:
        errors.append("host:absent_markers:non-empty array required")
        return
    for marker in absent:
        if isinstance(marker, str) and marker in code:
            errors.append(
                f"host:absent-guard:{relative} now contains {marker!r} in code -- the overlay "
                "must stay a frame-child InterimItemWindow (a floating/top-level vehicle "
                "auto-dismisses on focus loss and breaks the corner-anchored contract)"
            )


def _validate_anchoring_defaults(
    block: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    relative = block.get("source")
    text = contents.get(relative) if isinstance(relative, str) else None
    if text is None:
        errors.append(f"anchoring_defaults:source {relative} missing")
        return
    code = _without_cpp_comments(text)
    struct_marker = block.get("struct_marker")
    if isinstance(struct_marker, str) and struct_marker not in code:
        errors.append(f"anchoring_defaults:struct missing ({struct_marker})")
    fields = block.get("fields")
    if not isinstance(fields, list) or not fields:
        errors.append("anchoring_defaults:fields:non-empty array required")
        return
    for field in fields:
        if not isinstance(field, Mapping):
            errors.append("anchoring_defaults:fields:object required")
            continue
        declaration = field.get("declaration")
        if not isinstance(declaration, str) or declaration not in code:
            errors.append(
                f"anchoring_defaults:{field.get('name')} default drifted; expected the "
                f"declaration {declaration!r} in {relative}"
            )


def _validate_controller(
    block: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    relative = block.get("source")
    text = contents.get(relative) if isinstance(relative, str) else None
    if text is None:
        errors.append(f"controller:source {relative} missing")
        return
    code = _without_cpp_comments(text)
    for marker in block.get("markers", []) or []:
        if isinstance(marker, str) and marker not in code:
            errors.append(f"controller:marker missing in code ({marker})")
    # The focus-escape argument is written as a /*named*/ comment, so it is checked against
    # the raw text rather than the comment-stripped code.
    escape = block.get("focus_escape_marker")
    if not isinstance(escape, str) or escape not in text:
        errors.append(
            "controller:focus-escape marker missing -- the stack must let Tab escape back to "
            f"the document ({escape!r})"
        )


def _ui_objects(root: ET.Element) -> list[ET.Element]:
    return [node for node in root.iter() if node.tag == "object"]


def _direct_properties(obj: ET.Element) -> dict[str, str]:
    props: dict[str, str] = {}
    for child in obj:
        if child.tag == "property" and child.get("name"):
            props[child.get("name")] = (child.text or "").strip()
    return props


def _validate_stack_ui(
    block: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    relative = block.get("ui_file")
    text = contents.get(relative) if isinstance(relative, str) else None
    if text is None:
        errors.append(f"stack_ui:ui_file {relative} missing")
        return
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        errors.append(f"stack_ui:xml:{error}")
        return

    objects = _ui_objects(root)
    by_id = {obj.get("id"): obj for obj in objects if obj.get("id")}

    toplevel = by_id.get(block.get("toplevel_id"))
    if toplevel is None:
        errors.append(f"stack_ui:toplevel id {block.get('toplevel_id')!r} missing")
    else:
        if toplevel.get("class") != block.get("toplevel_class"):
            errors.append(
                f"stack_ui:toplevel class is {toplevel.get('class')!r}, expected "
                f"{block.get('toplevel_class')!r} (a dialog top level would make the "
                "non-blocking stack modal)"
            )
        spacing = _direct_properties(toplevel).get("spacing")
        if spacing != block.get("toplevel_spacing"):
            errors.append(
                f"stack_ui:toplevel spacing is {spacing!r}, expected "
                f"{block.get('toplevel_spacing')!r} (Material stack rhythm)"
            )

    card_box = by_id.get(block.get("card_box_id"))
    if card_box is None:
        errors.append(f"stack_ui:card box id {block.get('card_box_id')!r} missing")
    else:
        spacing = _direct_properties(card_box).get("spacing")
        if spacing != block.get("card_box_spacing"):
            errors.append(
                f"stack_ui:card-box spacing is {spacing!r}, expected "
                f"{block.get('card_box_spacing')!r} (Material stack rhythm)"
            )

    for widget_id in block.get("required_ids", []) or []:
        if isinstance(widget_id, str) and widget_id not in by_id:
            errors.append(f"stack_ui:required id {widget_id!r} missing from {relative}")
    for widget_id in block.get("welded_ids", []) or []:
        if isinstance(widget_id, str) and widget_id not in by_id:
            errors.append(
                f"stack_ui:welded id {widget_id!r} missing from {relative} -- the controller "
                "welds it and would fail at runtime"
            )


def _validate_governed_surfaces(
    registry: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    surfaces = registry.get("governed_surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("registry:governed_surfaces:non-empty array required")
        return
    raw = contents.get(LEDGER_PATH)
    if raw is None:
        errors.append(f"governed_surfaces:ledger {LEDGER_PATH} missing")
        return
    try:
        ledger = json.loads(raw)
    except json.JSONDecodeError as error:
        errors.append(f"governed_surfaces:ledger:{error}")
        return
    rows = {
        row.get("surface"): row
        for row in ledger.get("surfaces", [])
        if isinstance(row, Mapping)
    }
    seen: set[str] = set()
    for entry in surfaces:
        if not isinstance(entry, Mapping):
            errors.append("governed_surfaces:object required")
            continue
        surface = entry.get("surface")
        if not isinstance(surface, str) or not surface:
            errors.append("governed_surfaces:surface:non-empty string required")
            continue
        if surface in seen:
            errors.append(f"governed_surfaces:{surface} enumerated twice")
            continue
        seen.add(surface)
        row = rows.get(surface)
        if row is None:
            errors.append(f"governed_surfaces:{surface} is not a rewrite-ledger row")
            continue
        if row.get("family") != entry.get("family"):
            errors.append(
                f"governed_surfaces:{surface} family is {row.get('family')!r} in the ledger, "
                f"contract declares {entry.get('family')!r}"
            )
        if entry.get("inventory_id") and row.get("inventory_id") != entry.get("inventory_id"):
            errors.append(
                f"governed_surfaces:{surface} inventory_id is {row.get('inventory_id')!r} in "
                f"the ledger, contract declares {entry.get('inventory_id')!r}"
            )
        if row.get("rewrite_status") == REWRITTEN:
            evidence = row.get("rewrite_evidence")
            markers = evidence.get("anatomy_markers") if isinstance(evidence, Mapping) else None
            token = markers.get("contract_marker") if isinstance(markers, Mapping) else None
            if token != CONTRACT_NAME:
                errors.append(
                    f"governed_surfaces:{surface} is credited rewritten-material but its "
                    f"contract_marker is {token!r}, not {CONTRACT_NAME!r} -- the composition "
                    "cross-reference does not point back at this contract"
                )


# --------------------------------------------------------------------------------------------------
# Top-level
# --------------------------------------------------------------------------------------------------
def violations(registry: Mapping[str, Any], contents: Mapping[str, str]) -> list[str]:
    errors: list[str] = []

    if registry.get("schema_version") != 1:
        errors.append("registry:schema_version:must be 1")
    if registry.get("contract") != CONTRACT_NAME:
        errors.append("registry:contract:unexpected value")
    if registry.get("platform") != "windows":
        errors.append("registry:platform:must be windows")
    if registry.get("inventory_id") != "WIN-SHL-003":
        errors.append("registry:inventory_id:must be WIN-SHL-003")
    if registry.get("status") != "source-declared":
        errors.append("registry:status:must be source-declared")
    if not isinstance(registry.get("runtime_verified"), bool):
        errors.append("registry:runtime_verified:boolean required")
    elif registry["runtime_verified"]:
        errors.append("registry:runtime_verified:no runtime evidence exists; must be false")

    for section, validator in (
        ("host", _validate_host),
        ("anchoring_defaults", _validate_anchoring_defaults),
        ("controller", _validate_controller),
        ("stack_ui", _validate_stack_ui),
    ):
        block = registry.get(section)
        if not isinstance(block, Mapping):
            errors.append(f"registry:{section}:object required")
            continue
        validator(block, contents, errors)

    _validate_governed_surfaces(registry, contents, errors)

    ledger = registry.get("ledger")
    if not isinstance(ledger, Mapping):
        errors.append("registry:ledger:object required")
    else:
        if ledger.get("path") != LEDGER_PATH:
            errors.append("registry:ledger:path:unexpected value")
        if ledger.get("cross_reference_marker") != CONTRACT_NAME:
            errors.append("registry:ledger:cross_reference_marker:must equal the contract name")

    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    registry, contents = load_repository(repo_root)
    errors = violations(registry, contents)
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
        print(f"Material notification-overlay contract failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Material notification-overlay composition contract passed: the overlay stays a "
        "frame-child InterimItemWindow anchored bottom-right with the 420/16/16 Material "
        "defaults, the stack controller wires those preferences and the Tab-escape focus "
        "behaviour, the stack .ui keeps its non-dialog GtkBox top level and 9px rhythm, and "
        "every governed rewrite-ledger surface cross-references this contract."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
