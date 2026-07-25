#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed source contract for the Material UI-scale appearance control.

This pins the whole-UI scaling control restored on Tools > Options > Appearance
(community demand tdf#101646), modelled one-for-one on the proven MaterialDensity
control. The control is STORED-VALUE-ONLY in this stage: the value is persisted and
round-tripped, but no metric rescales the UI yet, so it is honest-inert exactly like
MaterialDensity. The contract cross-validates, source-only, that the three surfaces
cannot silently drift:

* **Schema** -- the officecfg ``Appearance`` group declares ``MaterialUiScale`` as
  ``xs:short`` with ``<value>100</value>`` and a ``minInclusive`` 50 / ``maxInclusive``
  400 constraint.
* **Widget** -- ``cui/uiconfig/ui/appearance.ui`` carries, inside the ``materialtheme``
  frame, a ``GtkSpinButton`` bound to a ``GtkAdjustment`` whose lower/upper match the
  schema bounds, plus a mnemonic ``GtkLabel`` that labels it.
* **Controller** -- ``cui/source/options/appearance.cxx`` welds the spin and both READS
  the stored value (accessor ``::get()`` -> ``set_value``) and WRITES it back (accessor
  ``::set(`` from ``get_value()``). A one-directional binding is a broken round-trip.

The value is stored-only and honest-inert this stage; ``runtime_verified`` is false and
``stored_only`` is true. Promoting either flag has no runtime evidence and must fail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/material-ui-scale.json"
CONTRACT = "material-ui-scale"


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _referenced_sources(registry: Mapping[str, Any]) -> set[str]:
    paths: set[str] = set()
    for key in ("schema_source", "ui_source", "controller_source", "controller_header"):
        value = registry.get(key)
        if isinstance(value, str):
            paths.add(value)
    return paths


def load_repository(repo_root: Path = REPOSITORY) -> tuple[dict[str, Any], dict[str, str]]:
    registry = _read_json(repo_root / REGISTRY_PATH)
    contents: dict[str, str] = {}
    for relative in _referenced_sources(registry):
        path = repo_root / relative
        if path.is_file():
            contents[relative] = path.read_text(encoding="utf-8")
    return registry, contents


# --------------------------------------------------------------------------------------------------
# integrity
# --------------------------------------------------------------------------------------------------
def _validate_integrity(registry: Mapping[str, Any], errors: list[str]) -> None:
    if registry.get("schema_version") != 1:
        errors.append("registry:schema_version:must be 1")
    if registry.get("contract") != CONTRACT:
        errors.append(f"registry:contract:must be {CONTRACT}")
    if registry.get("platform") != "windows":
        errors.append("registry:platform:must be windows")
    if registry.get("status") != "source-declared":
        errors.append("registry:status:must be source-declared")
    if not isinstance(registry.get("runtime_verified"), bool):
        errors.append("registry:runtime_verified:boolean required")
    elif registry["runtime_verified"]:
        errors.append("registry:runtime_verified:no runtime evidence exists; must be false")
    if not isinstance(registry.get("stored_only"), bool):
        errors.append("registry:stored_only:boolean required")
    elif not registry["stored_only"]:
        errors.append(
            "registry:stored_only:the UI-scale factor is not consumed by any metric this "
            "stage; the control is stored-value-only, so stored_only must be true"
        )
    if registry.get("apply_stage") != "restart":
        errors.append(
            "registry:apply_stage:must be 'restart' (the value is committed through the "
            "existing restart path; live rescale is a later stage)"
        )


def _prop_block(source: str, name: str) -> str | None:
    match = re.search(
        r'<prop\s+oor:name="' + re.escape(name) + r'"(?:.*?)</prop>', source, flags=re.DOTALL
    )
    return match.group(0) if match else None


# --------------------------------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------------------------------
def _validate_schema(
    registry: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    schema = contents.get(registry.get("schema_source", ""))
    prop = registry.get("property")
    if not isinstance(prop, dict):
        errors.append("registry:property:object required")
        return
    if schema is None:
        errors.append("schema:schema_source missing")
        return

    name = prop.get("name")
    if not isinstance(name, str):
        errors.append("property:name must be a string")
        return

    block = _prop_block(schema, name)
    if block is None:
        errors.append(f"property:{name}:not found in officecfg Appearance schema")
        return

    prop_type = prop.get("type")
    if isinstance(prop_type, str) and f'oor:type="{prop_type}"' not in block:
        errors.append(f"property:{name}:schema is not oor:type={prop_type!r}")

    default = prop.get("default")
    if isinstance(default, str) and f"<value>{default}</value>" not in block:
        errors.append(
            f"property:{name}:schema default drifted (expected <value>{default}</value>)"
        )

    lo = prop.get("min_inclusive")
    if isinstance(lo, str) and f'<minInclusive oor:value="{lo}"' not in block:
        errors.append(f"property:{name}:schema minInclusive drifted (expected {lo!r})")

    hi = prop.get("max_inclusive")
    if isinstance(hi, str) and f'<maxInclusive oor:value="{hi}"' not in block:
        errors.append(f"property:{name}:schema maxInclusive drifted (expected {hi!r})")


# --------------------------------------------------------------------------------------------------
# widget (adjustment bounds + labelled spin inside the frame)
# --------------------------------------------------------------------------------------------------
def _validate_widget(
    registry: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    ui = contents.get(registry.get("ui_source", ""))
    spec = registry.get("ui")
    frame_id = registry.get("frame_id")
    if not isinstance(spec, dict):
        errors.append("registry:ui:object required")
        return
    if ui is None:
        errors.append("widget:ui_source missing")
        return

    # Adjustment carries the bounds; it is a top-level object referenced by the spin.
    adj_id = spec.get("adjustment_id")
    adj_block = None
    if isinstance(adj_id, str):
        match = re.search(
            r'<object class="GtkAdjustment" id="' + re.escape(adj_id) + r'".*?</object>',
            ui,
            flags=re.DOTALL,
        )
        if match is None:
            errors.append(f"widget:adjustment id={adj_id!r} not found in appearance.ui")
        else:
            adj_block = match.group(0)
    if adj_block is not None:
        lo = spec.get("adjustment_lower")
        hi = spec.get("adjustment_upper")
        if isinstance(lo, str) and f'<property name="lower">{lo}</property>' not in adj_block:
            errors.append(f"widget:adjustment lower drifted (expected {lo!r})")
        if isinstance(hi, str) and f'<property name="upper">{hi}</property>' not in adj_block:
            errors.append(f"widget:adjustment upper drifted (expected {hi!r})")

    # Region of appearance.ui from the materialtheme frame onward, so the spin and its
    # label are verified INSIDE the frame, not merely somewhere in the file.
    frame_region = ""
    if isinstance(frame_id, str):
        if f'id="{frame_id}"' not in ui:
            errors.append(f"widget:frame id={frame_id!r} not found in appearance.ui")
        else:
            frame_region = ui[ui.index(f'id="{frame_id}"') :]

    spin_id = spec.get("spin_id")
    spin_class = spec.get("spin_class")
    if frame_region and isinstance(spin_id, str):
        if f'id="{spin_id}"' not in frame_region:
            errors.append(
                f"widget:spin id={spin_id!r} not found inside the {frame_id!r} frame"
            )
        elif isinstance(spin_class, str):
            spin_match = re.search(
                r'<object class="([^"]+)" id="' + re.escape(spin_id) + r'"', frame_region
            )
            if spin_match is None or spin_match.group(1) != spin_class:
                errors.append(
                    f"widget:spin id={spin_id!r} is not a {spin_class}"
                )
        # The spin must reference the bounded adjustment.
        if isinstance(adj_id, str) and f'<property name="adjustment">{adj_id}</property>' not in frame_region:
            errors.append(
                f"widget:spin id={spin_id!r} does not reference adjustment {adj_id!r}"
            )

    # The label must exist, mnemonic-point at the spin, and label-for it (mnemonic
    # accessibility: a non-labelled spin would be a gla11y no-labelled-by failure).
    label_id = spec.get("label_id")
    if frame_region and isinstance(label_id, str):
        if f'id="{label_id}"' not in frame_region:
            errors.append(
                f"widget:label id={label_id!r} not found inside the {frame_id!r} frame"
            )
        else:
            if isinstance(spin_id, str):
                if f'<property name="mnemonic-widget">{spin_id}</property>' not in frame_region:
                    errors.append(
                        f"widget:label id={label_id!r} does not mnemonic-widget the spin "
                        f"{spin_id!r}"
                    )
                if f'<relation type="label-for" target="{spin_id}"/>' not in frame_region:
                    errors.append(
                        f"widget:label id={label_id!r} has no label-for relation to the spin "
                        f"{spin_id!r}"
                    )
        underline = spec.get("mnemonic_underline")
        if isinstance(underline, str) and f">{underline}</property>" not in frame_region:
            errors.append(
                f"widget:label mnemonic caption drifted (expected {underline!r} with a '_' "
                "mnemonic marker)"
            )


# --------------------------------------------------------------------------------------------------
# controller (round-trip: reads AND writes)
# --------------------------------------------------------------------------------------------------
def _validate_controller(
    registry: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    controller = contents.get(registry.get("controller_source", ""))
    spec = registry.get("controller")
    if not isinstance(spec, dict):
        errors.append("registry:controller:object required")
        return
    if controller is None:
        errors.append("controller:controller_source missing")
        return

    binding = spec.get("weld_binding")
    if isinstance(binding, str) and binding not in controller:
        errors.append(f"controller:weld binding {binding!r} missing")

    for marker in spec.get("read_markers", []) or []:
        if isinstance(marker, str) and marker not in controller:
            errors.append(
                f"controller:READ marker {marker!r} missing -- the page must initialise the "
                "spin from the stored value (broken round-trip)"
            )
    for marker in spec.get("write_markers", []) or []:
        if isinstance(marker, str) and marker not in controller:
            errors.append(
                f"controller:WRITE marker {marker!r} missing -- the page must commit the "
                "spin value back to officecfg (broken round-trip)"
            )


# --------------------------------------------------------------------------------------------------
# header member markers
# --------------------------------------------------------------------------------------------------
def _validate_header(
    registry: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    header = contents.get(registry.get("controller_header", ""))
    if header is None:
        errors.append("header:controller_header missing")
        return
    for marker in registry.get("header_markers", []) or []:
        if isinstance(marker, str) and marker not in header:
            errors.append(f"header:marker {marker!r} missing from appearance.hxx")


# --------------------------------------------------------------------------------------------------
# Top-level
# --------------------------------------------------------------------------------------------------
def violations(registry: Mapping[str, Any], contents: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    _validate_integrity(registry, errors)
    _validate_schema(registry, contents, errors)
    _validate_widget(registry, contents, errors)
    _validate_controller(registry, contents, errors)
    _validate_header(registry, contents, errors)
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
        print(f"Material UI-scale contract failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Material UI-scale contract passed: the officecfg MaterialUiScale schema "
        "(xs:short, default 100, min 50 / max 400), the bounded GtkAdjustment + labelled "
        "GtkSpinButton inside the materialtheme frame, and the controller read+write "
        "round-trip are intact; the value stays stored-only (runtime_verified false)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
