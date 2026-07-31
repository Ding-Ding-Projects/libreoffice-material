#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Validate runtime-composed Material dialog shells fail closed.

The governed ``GtkDialog`` files intentionally contain empty notebooks: their
page labels and page bodies are created by C++ controllers.  Crediting those
shells through the ordinary static-dialog predicate would require fake labels;
crediting them without checking the host would accept an empty dialog.  This
contract therefore requires both halves at once:

* the static shell preserves its declared modality and title source, Material
  inset grid, empty left-tab notebook, safe footer/default action, and no
  legacy border width;
* the named C++ host binds that notebook and creates every declared page via
  ordered markers or an exact conditional occurrence map; and
* the burn-down ledger classifies only the explicit allow-list as
  ``runtime-dialog-shell`` and, once credited, cites this exact contract.

This is source-composition evidence only. ``runtime_verified`` remains false.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/runtime-dialog-shell-composition.json"
LEDGER_PATH = "qa/windows-ui-contract/material-rewrite-ledger.json"
CONTRACT = "material-runtime-dialog-shell-composition"
EXPECTED_SURFACES = {
    "chart2/uiconfig/ui/3dviewdialog.ui": ("chart2", "WIN-CH-001"),
    "chart2/uiconfig/ui/attributedialog.ui": ("chart2", "WIN-CH-001"),
    "chart2/uiconfig/ui/chardialog.ui": ("chart2", "WIN-CH-001"),
    "chart2/uiconfig/ui/paradialog.ui": ("chart2", "WIN-CH-001"),
    "cui/uiconfig/ui/areadialog.ui": ("cui", "unassigned"),
    "cui/uiconfig/ui/borderareatransparencydialog.ui": ("cui", "unassigned"),
    "cui/uiconfig/ui/borderbackgrounddialog.ui": ("cui", "unassigned"),
    "cui/uiconfig/ui/calloutdialog.ui": ("cui", "unassigned"),
    "cui/uiconfig/ui/customizedialog.ui": ("cui", "unassigned"),
    "cui/uiconfig/ui/formatcellsdialog.ui": ("cui", "unassigned"),
    "cui/uiconfig/ui/hyperlinkdlg.ui": ("cui", "WIN-SYS-015"),
    "filter/uiconfig/ui/pdfoptionsdialog.ui": ("filter", "WIN-SYS-002"),
    "sfx2/uiconfig/ui/documentpropertiesdialog.ui": ("sfx2", "WIN-SYS-003"),
    "sw/uiconfig/swriter/ui/characterproperties.ui": ("sw", "WIN-WR-001"),
    "sw/uiconfig/swriter/ui/envdialog.ui": ("sw", "WIN-WR-001"),
    "sw/uiconfig/swriter/ui/footendnotedialog.ui": ("sw", "WIN-WR-001"),
    "sw/uiconfig/swriter/ui/formatsectiondialog.ui": ("sw", "WIN-WR-001"),
    "sw/uiconfig/swriter/ui/fielddialog.ui": ("sw", "WIN-WR-001"),
    "sw/uiconfig/swriter/ui/paradialog.ui": ("sw", "WIN-WR-001"),
    "sw/uiconfig/swriter/ui/picturedialog.ui": ("sw", "WIN-WR-001"),
    "sw/uiconfig/swriter/ui/tableproperties.ui": ("sw", "WIN-WR-001"),
}


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _strip_comments(text: str) -> str:
    """Remove C/C++ comments while preserving quoted strings."""

    out: list[str] = []
    i = 0
    state = "code"
    quote = ""
    while i < len(text):
        char = text[i]
        following = text[i + 1] if i + 1 < len(text) else ""
        if state == "code":
            if char == "/" and following == "/":
                state = "line"
                i += 2
                continue
            if char == "/" and following == "*":
                state = "block"
                i += 2
                continue
            if char in ('"', "'"):
                state = "quote"
                quote = char
            out.append(char)
            i += 1
            continue
        if state == "line":
            if char == "\n":
                state = "code"
                out.append(char)
            i += 1
            continue
        if state == "block":
            if char == "*" and following == "/":
                state = "code"
                i += 2
                continue
            if char == "\n":
                out.append(char)
            i += 1
            continue
        out.append(char)
        if char == "\\" and i + 1 < len(text):
            out.append(text[i + 1])
            i += 2
            continue
        if char == quote:
            state = "code"
        i += 1
    return "".join(out)


def _normalise_source(text: str) -> str:
    return " ".join(_strip_comments(text).split())


def _tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _direct_properties(obj: ET.Element) -> dict[str, str]:
    return {
        child.get("name", ""): (child.text or "").strip()
        for child in obj
        if _tag(child.tag) == "property" and child.get("name")
    }


def _bool(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes"}


def _integer(raw: str | None) -> int | None:
    try:
        return int((raw or "").strip())
    except ValueError:
        return None


def _objects(root: ET.Element) -> dict[str, ET.Element]:
    result: dict[str, ET.Element] = {}
    for node in root.iter():
        if _tag(node.tag) != "object" or not node.get("id"):
            continue
        result[node.get("id", "")] = node
    return result


def _parse_xml(text: str | None, surface: str, errors: list[str]) -> ET.Element | None:
    if text is None:
        errors.append(f"{surface}: source file is missing")
        return None
    try:
        return ET.fromstring(text)
    except ET.ParseError as error:
        errors.append(f"{surface}: XML is not parseable: {error}")
        return None


def load_repository(
    repo_root: Path = REPOSITORY,
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    registry = _read_json(repo_root / REGISTRY_PATH)
    ledger = _read_json(repo_root / LEDGER_PATH)
    paths: set[str] = set()
    for shell in registry.get("shells", []):
        if not isinstance(shell, Mapping):
            continue
        surface = shell.get("surface")
        host = shell.get("host")
        if isinstance(surface, str):
            paths.add(surface)
        if isinstance(host, Mapping) and isinstance(host.get("source"), str):
            paths.add(host["source"])
        dependency = shell.get("dependency_contract")
        if isinstance(dependency, Mapping) and isinstance(dependency.get("path"), str):
            paths.add(dependency["path"])
    contents = {
        path: (repo_root / path).read_text(encoding="utf-8")
        for path in paths
        if (repo_root / path).is_file()
    }
    return registry, contents, ledger


def _find_action_widgets(dialog: ET.Element) -> list[tuple[str, int | None]]:
    for node in dialog.iter():
        if _tag(node.tag) != "action-widgets":
            continue
        return [
            ((item.text or "").strip(), _integer(item.get("response")))
            for item in node
            if _tag(item.tag) == "action-widget"
        ]
    return []


def _button_is_secondary(dialog: ET.Element, button_id: str) -> bool:
    for child in dialog.iter():
        if _tag(child.tag) != "child":
            continue
        direct_object = next(
            (
                node
                for node in child
                if _tag(node.tag) == "object" and node.get("id") == button_id
            ),
            None,
        )
        if direct_object is None:
            continue
        for packing in child:
            if _tag(packing.tag) != "packing":
                continue
            props = {
                node.get("name", ""): (node.text or "").strip()
                for node in packing
                if _tag(node.tag) == "property"
            }
            return _bool(props.get("secondary"))
    return False


def _validate_shell(
    shell: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    surface = shell.get("surface")
    if not isinstance(surface, str):
        errors.append("shell: surface must be a string")
        return
    context = surface
    root = _parse_xml(contents.get(surface), surface, errors)
    if root is None:
        return
    objects = _objects(root)
    parent = {child: node for node in root.iter() for child in node}

    dialog_spec = shell.get("dialog")
    if not isinstance(dialog_spec, Mapping):
        errors.append(f"{context}: dialog contract must be an object")
        return
    dialog_id = dialog_spec.get("id")
    dialog = objects.get(dialog_id) if isinstance(dialog_id, str) else None
    if dialog is None or dialog.get("class") != "GtkDialog":
        errors.append(f"{context}: GtkDialog {dialog_id!r} is missing")
        return
    dialog_props = _direct_properties(dialog)
    expected_modal = dialog_spec.get("modal")
    if not isinstance(expected_modal, bool):
        errors.append(f"{context}: dialog modal contract must be a boolean")
    elif _bool(dialog_props.get("modal")) != expected_modal:
        errors.append(f"{context}: dialog must remain modal={expected_modal}")

    title_source = dialog_spec.get("title_source", "static")
    if dialog_spec.get("title_required") is not True:
        errors.append(f"{context}: dialog title_required must remain True")
    elif title_source == "static":
        if not dialog_props.get("title", "").strip():
            errors.append(f"{context}: dialog must retain a non-empty static title")
    elif title_source == "runtime":
        runtime_title_marker = dialog_spec.get("runtime_title_marker")
        if not isinstance(runtime_title_marker, str) or not runtime_title_marker.strip():
            errors.append(f"{context}: runtime title source requires a non-empty marker")
    else:
        errors.append(f"{context}: dialog title_source must be 'static' or 'runtime'")

    grid_spec = shell.get("content_grid")
    if not isinstance(grid_spec, Mapping):
        errors.append(f"{context}: content_grid contract must be an object")
        return
    grid_id = grid_spec.get("id")
    grid = objects.get(grid_id) if isinstance(grid_id, str) else None
    if grid is None or grid.get("class") != grid_spec.get("class"):
        errors.append(f"{context}: Material content grid {grid_id!r} is missing")
        return
    grid_props = _direct_properties(grid)
    expected_grid = {
        "row-spacing": grid_spec.get("row_spacing"),
        "column-spacing": grid_spec.get("column_spacing"),
        "margin-start": grid_spec.get("margins"),
        "margin-end": grid_spec.get("margins"),
        "margin-top": grid_spec.get("margins"),
        "margin-bottom": grid_spec.get("margins"),
    }
    for name, expected in expected_grid.items():
        if not isinstance(expected, int) or _integer(grid_props.get(name)) != expected:
            errors.append(
                f"{context}: content grid {name} is {_integer(grid_props.get(name))!r}, "
                f"expected {expected!r}"
            )
    for name in ("hexpand", "vexpand"):
        expected = grid_spec.get(name)
        if expected is not True or not _bool(grid_props.get(name)):
            errors.append(f"{context}: content grid {name} must remain True")

    notebook_spec = shell.get("notebook")
    if not isinstance(notebook_spec, Mapping):
        errors.append(f"{context}: notebook contract must be an object")
        return
    notebook_id = notebook_spec.get("id")
    notebook = objects.get(notebook_id) if isinstance(notebook_id, str) else None
    if notebook is None or notebook.get("class") != notebook_spec.get("class"):
        errors.append(f"{context}: runtime notebook {notebook_id!r} is missing")
        return
    if parent.get(parent.get(notebook)) is not grid:
        errors.append(f"{context}: notebook is no longer directly hosted by the Material grid")
    notebook_props = _direct_properties(notebook)
    if notebook_props.get("tab-pos") != notebook_spec.get("tab_pos"):
        errors.append(f"{context}: notebook tab-pos must remain {notebook_spec.get('tab_pos')!r}")
    if notebook_spec.get("scrollable") is not True or not _bool(notebook_props.get("scrollable")):
        errors.append(f"{context}: notebook must remain scrollable=True")
    static_pages = sum(
        1
        for child in notebook
        if _tag(child.tag) == "child" and child.get("type") != "tab"
    )
    if notebook_spec.get("static_pages") != 0 or static_pages != 0:
        errors.append(
            f"{context}: notebook must remain an empty runtime host; found {static_pages} static pages"
        )

    footer = shell.get("footer")
    if not isinstance(footer, Mapping):
        errors.append(f"{context}: footer contract must be an object")
        return
    expected_actions = [
        (item.get("id"), item.get("response"))
        for item in footer.get("action_widgets", [])
        if isinstance(item, Mapping)
    ]
    actual_actions = _find_action_widgets(dialog)
    if actual_actions != expected_actions:
        errors.append(
            f"{context}: footer action-widget order/response drift: "
            f"{actual_actions!r} != {expected_actions!r}"
        )
    primary = footer.get("primary")
    if not isinstance(primary, Mapping):
        errors.append(f"{context}: footer primary contract must be an object")
    else:
        primary_id = primary.get("id")
        primary_button = objects.get(primary_id) if isinstance(primary_id, str) else None
        if primary_button is None or primary_button.get("class") != "GtkButton":
            errors.append(f"{context}: primary button {primary_id!r} is missing")
        else:
            primary_props = _direct_properties(primary_button)
            for name, key in (("can-default", "can_default"), ("has-default", "has_default")):
                if primary.get(key) is not True or not _bool(primary_props.get(name)):
                    errors.append(f"{context}: primary {primary_id} must retain {name}=True")
        if (primary_id, primary.get("response")) not in actual_actions:
            errors.append(f"{context}: primary action is not bound to its declared response")

    action_ids = {item[0] for item in actual_actions}
    for button_id in footer.get("secondary", []):
        if not isinstance(button_id, str) or not _button_is_secondary(dialog, button_id):
            errors.append(f"{context}: footer button {button_id!r} must remain secondary")
    for button_id in footer.get("auxiliary_buttons", []):
        if not isinstance(button_id, str) or button_id not in objects:
            errors.append(f"{context}: auxiliary footer button {button_id!r} is missing")
        elif button_id in action_ids:
            errors.append(f"{context}: auxiliary footer button {button_id!r} became an action-widget")

    footer_boxes = [
        node
        for node in dialog.iter()
        if _tag(node.tag) == "object" and node.get("class") == "GtkButtonBox"
    ]
    if not footer_boxes:
        errors.append(f"{context}: footer GtkButtonBox is missing")
    else:
        footer_props = _direct_properties(footer_boxes[0])
        if (_integer(footer_props.get("spacing")) or 0) < 10:
            errors.append(f"{context}: footer spacing must remain at least 10")
        if footer_props.get("layout-style") != "end":
            errors.append(f"{context}: footer layout-style must remain 'end'")

    for node in dialog.iter():
        if _tag(node.tag) != "property" or node.get("name") != "border-width":
            continue
        if (_integer(node.text) or 0) > 0:
            errors.append(f"{context}: legacy positive border-width returned")

    dependency = shell.get("dependency_contract")
    if dependency is not None:
        if not isinstance(dependency, Mapping):
            errors.append(f"{context}: dependency_contract must be an object")
        else:
            dependency_path = dependency.get("path")
            dependency_marker = dependency.get("contract_marker")
            if not isinstance(dependency_path, str) or dependency_path not in contents:
                errors.append(f"{context}: dependency contract {dependency_path!r} is missing")
            elif not isinstance(dependency_marker, str) or not dependency_marker:
                errors.append(f"{context}: dependency contract marker is missing")
            else:
                try:
                    dependency_data = json.loads(contents[dependency_path])
                except json.JSONDecodeError as error:
                    errors.append(f"{context}: dependency contract is invalid JSON: {error}")
                else:
                    if not (
                        isinstance(dependency_data, Mapping)
                        and dependency_data.get("contract") == dependency_marker
                    ):
                        errors.append(
                            f"{context}: dependency contract marker {dependency_marker!r} vanished"
                        )
                    if isinstance(dependency_data, Mapping) and dependency_data.get(
                        "runtime_verified"
                    ) is not False:
                        errors.append(
                            f"{context}: dependency contract runtime_verified must remain false"
                        )

    host = shell.get("host")
    if not isinstance(host, Mapping):
        errors.append(f"{context}: host contract must be an object")
        return
    source = host.get("source")
    if not isinstance(source, str) or source not in contents:
        errors.append(f"{context}: host source {source!r} is missing")
        return
    normalised = _normalise_source(contents[source])
    region_start = host.get("region_start")
    region_end = host.get("region_end")
    if region_start is not None or region_end is not None:
        if not (
            isinstance(region_start, str)
            and region_start.strip()
            and isinstance(region_end, str)
            and region_end.strip()
        ):
            errors.append(f"{context}: host region_start and region_end must both be non-empty")
            return
        region_start = " ".join(region_start.split())
        region_end = " ".join(region_end.split())
        start_count = normalised.count(region_start)
        end_count = normalised.count(region_end)
        if start_count != 1 or end_count != 1:
            errors.append(
                f"{context}: host region bounds occur {start_count}/{end_count} times in {source}"
            )
            return
        start_index = normalised.index(region_start)
        end_index = normalised.index(region_end)
        if end_index <= start_index:
            errors.append(f"{context}: host region bounds are reversed")
            return
        normalised = normalised[start_index:end_index]

    if title_source == "runtime":
        runtime_title_marker = " ".join(
            str(dialog_spec.get("runtime_title_marker", "")).split()
        )
        marker_count = normalised.count(runtime_title_marker)
        if marker_count != 1:
            errors.append(
                f"{context}: runtime title marker occurs {marker_count} times in {source}: "
                f"{runtime_title_marker}"
            )
    positions: list[int] = []
    for marker in host.get("ordered_markers", []):
        if not isinstance(marker, str) or not marker.strip():
            errors.append(f"{context}: every host marker must be a non-empty string")
            continue
        marker = " ".join(marker.split())
        count = normalised.count(marker)
        if count != 1:
            errors.append(f"{context}: host marker occurs {count} times in {source}: {marker}")
            continue
        positions.append(normalised.index(marker))
    if positions != sorted(positions):
        errors.append(f"{context}: runtime page host markers are out of declared order")
    marker_blob = " ".join(
        marker for marker in host.get("ordered_markers", []) if isinstance(marker, str)
    )
    page_ids = host.get("page_ids")
    if not isinstance(page_ids, list) or not page_ids:
        errors.append(f"{context}: host page_ids must be a non-empty list")
    else:
        page_occurrences = host.get("page_occurrences")
        if page_occurrences is not None:
            if not isinstance(page_occurrences, Mapping) or not page_occurrences:
                errors.append(f"{context}: host page_occurrences must be a non-empty object")
            else:
                expected_occurrences: dict[str, int] = {}
                for page_id, count in page_occurrences.items():
                    if not isinstance(page_id, str) or not page_id:
                        errors.append(f"{context}: every page_occurrences key must be non-empty")
                    elif not isinstance(count, int) or isinstance(count, bool) or count < 1:
                        errors.append(
                            f"{context}: page occurrence count for {page_id!r} must be positive"
                        )
                    else:
                        expected_occurrences[page_id] = count
                actual_occurrences = Counter(
                    re.findall(r'AddTabPage\s*\(\s*u"([^"]+)"_ustr', normalised)
                )
                if actual_occurrences != Counter(expected_occurrences):
                    errors.append(
                        f"{context}: runtime page occurrences drifted: "
                        f"{dict(sorted(actual_occurrences.items()))!r} != "
                        f"{dict(sorted(expected_occurrences.items()))!r}"
                    )
                if set(page_ids) != set(expected_occurrences):
                    errors.append(
                        f"{context}: page_ids must exactly match page_occurrences keys"
                    )
        else:
            for page_id in page_ids:
                encoded_tokens = (f'u"{page_id}"_ustr', f'"{page_id}"')
                if not isinstance(page_id, str) or not any(
                    token in marker_blob for token in encoded_tokens
                ):
                    errors.append(
                        f"{context}: runtime page {page_id!r} has no ordered host marker"
                    )


def violations(
    registry: Mapping[str, Any],
    contents: Mapping[str, str],
    ledger: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if registry.get("schema_version") != 1:
        errors.append("registry: schema_version must be 1")
    if registry.get("contract") != CONTRACT:
        errors.append(f"registry: contract must be {CONTRACT!r}")
    if registry.get("platform") != "windows":
        errors.append("registry: platform must be 'windows'")
    if registry.get("status") != "source-declared":
        errors.append("registry: status must be 'source-declared'")
    if registry.get("runtime_verified") is not False:
        errors.append("registry: runtime_verified must remain false without runtime evidence")
    if registry.get("ledger") != LEDGER_PATH:
        errors.append(f"registry: ledger must be {LEDGER_PATH!r}")

    shells = registry.get("shells")
    if not isinstance(shells, list):
        errors.append("registry: shells must be a list")
        return errors
    surfaces = [shell.get("surface") for shell in shells if isinstance(shell, Mapping)]
    if len(surfaces) != len(set(surfaces)):
        errors.append("registry: shell surfaces must be unique")
    if set(surfaces) != set(EXPECTED_SURFACES):
        errors.append(
            "registry: shell surface set drifted: "
            f"{sorted(str(item) for item in surfaces)!r} != {sorted(EXPECTED_SURFACES)!r}"
        )

    ledger_rows = {
        row.get("surface"): row
        for row in ledger.get("surfaces", [])
        if isinstance(row, Mapping) and isinstance(row.get("surface"), str)
    }
    runtime_rows = {
        surface
        for surface, row in ledger_rows.items()
        if row.get("family") == "runtime-dialog-shell"
    }
    if runtime_rows != set(EXPECTED_SURFACES):
        errors.append(
            "ledger: runtime-dialog-shell surface set drifted: "
            f"{sorted(runtime_rows)!r} != {sorted(EXPECTED_SURFACES)!r}"
        )
    for shell in shells:
        if not isinstance(shell, Mapping):
            errors.append("registry: every shell must be an object")
            continue
        surface = shell.get("surface")
        if not isinstance(surface, str) or surface not in EXPECTED_SURFACES:
            continue
        expected_owner, expected_inventory = EXPECTED_SURFACES[surface]
        if shell.get("owner") != expected_owner:
            errors.append(f"{surface}: contract owner must be {expected_owner!r}")
        if shell.get("inventory_id") != expected_inventory:
            errors.append(f"{surface}: contract inventory_id must be {expected_inventory!r}")
        _validate_shell(shell, contents, errors)

        row = ledger_rows.get(surface)
        if not isinstance(row, Mapping):
            errors.append(f"{surface}: ledger row is missing")
            continue
        expected = {
            "owner": expected_owner,
            "inventory_id": expected_inventory,
            "family": "runtime-dialog-shell",
            "rewrite_class": "dialog-composition",
        }
        for key, value in expected.items():
            if row.get(key) != value:
                errors.append(f"{surface}: ledger {key} is {row.get(key)!r}, expected {value!r}")
        if row.get("rewrite_status") == "rewritten-material":
            evidence = row.get("rewrite_evidence")
            markers = evidence.get("anatomy_markers") if isinstance(evidence, Mapping) else None
            if not isinstance(evidence, Mapping) or evidence.get("contract") != REGISTRY_PATH:
                errors.append(f"{surface}: rewritten ledger row must cite {REGISTRY_PATH}")
            if not isinstance(markers, Mapping) or markers.get("contract_marker") != CONTRACT:
                errors.append(f"{surface}: rewritten ledger row lost the composition marker")
            if not isinstance(markers, Mapping) or markers.get("evidence_kind") != "composition-code":
                errors.append(f"{surface}: rewritten ledger row must declare composition-code evidence")
        elif row.get("rewrite_status") != "pending":
            errors.append(f"{surface}: ledger status must be pending or rewritten-material")
    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    registry, contents, ledger = load_repository(repo_root)
    errors = violations(registry, contents, ledger)
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
        print(f"Runtime dialog shell composition failed:\n{error}", file=sys.stderr)
        return 1
    print(
        f"Runtime dialog shell composition passed: {len(EXPECTED_SURFACES)} explicit "
        "empty-notebook shells retain Material inset grids, safe footers, and declared "
        "C++ page hosts; runtime_verified=false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
