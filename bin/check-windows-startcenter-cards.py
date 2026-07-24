#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed source contract for the Material Start Center document cards.

``qa/windows-ui-contract/startcenter-cards.json`` registers the native Material
document-card grid drawn by the two Start Center ThumbnailView subclasses --
``RecentDocsView`` and ``TemplateDefaultView`` -- per docs/design/06-containers.md
6.6 and docs/design/09-start-center.md 9.1/9.10. This checker cross-validates each
declaration against the real tree:

* ``palette_tokens`` / ``shape_tokens`` -- every color role the card consumes must
  exist in BOTH palettes of definition.xml, and every corner-radius token must
  exist with the exact value. A renamed role, a dropped scheme, or a changed
  radius (token drift) fails closed.
* ``renderer`` -- the shared renderer source must include the token accessor
  header and contain the guard, the token lookups and every anatomy marker in
  *code* (C/C++ comments are stripped first), so comment-only wiring can never
  satisfy the contract; the header must declare each geometry constant with the
  exact value, so the anatomy metrics cannot silently drift.
* ``views`` -- each Start Center view source must include the renderer header,
  invoke the guarded renderer, pass its localized empty-grid resource, keep the
  non-Material base paint as the fallback, and lay the grid out with the card
  metrics. Each empty-grid resource must be defined with the expected copy. The
  migrated first-run pins are enforced against code: the pre-rewrite gate
  (``pinned_absent_markers``) must be gone, the stock Welcome bitmap must be
  REQUIRED-ABSENT from the Material guard block (``guard_absent_markers``) yet
  still present on the stock path (``stock_markers``), and the first-run
  invitation / no-match wiring must live inside the guard
  (``guard_present_markers``). Invitation string copy (``invite_resources``,
  authored by the Strings/Icons owner) is cross-checked only once defined.

The registry establishes source-complete scope; it never claims a native build,
card pixels or runtime evidence (``runtime_verified: false`` throughout).
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/startcenter-cards.json"
DEFINITION_PATH = "vcl/uiconfig/theme_definitions/material/definition.xml"

REQUIRED_VIEW_IDS = {"recentdocs.card-grid", "templatedefault.card-grid"}


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _without_cpp_comments(source: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", source, flags=re.DOTALL)


def _guard_block(code: str, opener: str) -> str | None:
    """Return the body (including braces) of the *block-form* ``opener`` guard.

    ``opener`` (e.g. ``if (sfx2::IsMaterialStartCenterActive())``) also appears in
    the constructor in single-statement form, so only the occurrence immediately
    followed by ``{`` -- the Paint override's Material guard block -- is matched;
    the block is then brace-balanced to its close. ``code`` must already be
    comment-stripped. Returns ``None`` when no block-form guard exists.
    """
    start = 0
    while True:
        idx = code.find(opener, start)
        if idx < 0:
            return None
        cursor = idx + len(opener)
        while cursor < len(code) and code[cursor].isspace():
            cursor += 1
        if cursor < len(code) and code[cursor] == "{":
            depth = 0
            for pos in range(cursor, len(code)):
                if code[pos] == "{":
                    depth += 1
                elif code[pos] == "}":
                    depth -= 1
                    if depth == 0:
                        return code[cursor : pos + 1]
            return None
        start = idx + len(opener)


def load_repository(repo_root: Path = REPOSITORY) -> tuple[dict[str, Any], dict[str, str]]:
    registry = _read_json(repo_root / REGISTRY_PATH)
    paths: set[str] = {DEFINITION_PATH}

    renderer = registry.get("renderer")
    if isinstance(renderer, dict):
        for key in ("source", "header"):
            value = renderer.get(key)
            if isinstance(value, str):
                paths.add(value)

    resource_file = registry.get("empty_message_resource_file")
    if isinstance(resource_file, str):
        paths.add(resource_file)

    for view in registry.get("views", []):
        if isinstance(view, dict) and isinstance(view.get("source"), str):
            paths.add(view["source"])

    contents: dict[str, str] = {}
    for relative in paths:
        path = repo_root / relative
        if path.is_file():
            contents[relative] = path.read_text(encoding="utf-8")
    return registry, contents


# --------------------------------------------------------------------------------------------------
# definition.xml token existence + value fidelity
# --------------------------------------------------------------------------------------------------
def _parse_definition(text: str, errors: list[str]) -> ET.Element | None:
    try:
        return ET.fromstring(text)
    except ET.ParseError as error:
        errors.append(f"definition:xml:{error}")
        return None


def _palettes(root: ET.Element) -> dict[str, dict[str, str]]:
    palettes: dict[str, dict[str, str]] = {}
    for palette in root.findall("palette"):
        scheme = palette.get("scheme", "")
        colors: dict[str, str] = {}
        for color in palette.findall("color"):
            name = color.get("name")
            if name is not None:
                colors[name] = color.get("value", "")
        palettes[scheme] = colors
    return palettes


def _radii(root: ET.Element) -> dict[str, str]:
    radii: dict[str, str] = {}
    shapes = root.find("shapes")
    if shapes is None:
        return radii
    for radius in shapes.findall("radius"):
        name = radius.get("name")
        if name is not None:
            radii[name] = radius.get("value", "")
    return radii


def _validate_definition_tokens(
    registry: Mapping[str, Any], root: ET.Element, errors: list[str]
) -> None:
    palettes = _palettes(root)
    # Cards resolve their palette per active scheme, so every role must exist in
    # both the default (light) and dark palettes.
    for scheme in ("", "dark"):
        if scheme not in palettes:
            errors.append(f"definition:palette:missing scheme {scheme!r}")
    for role in registry.get("palette_tokens", []):
        if not isinstance(role, str):
            continue
        for scheme, colors in palettes.items():
            if scheme not in ("", "dark"):
                continue
            if role not in colors:
                errors.append(
                    f"definition:palette:token drift: role {role!r} missing from scheme {scheme!r}"
                )

    radii = _radii(root)
    shape_tokens = registry.get("shape_tokens", {})
    if isinstance(shape_tokens, dict):
        for name, expected in shape_tokens.items():
            actual = radii.get(name)
            if actual is None:
                errors.append(f"definition:shapes:token drift: radius {name!r} missing")
            elif actual != expected:
                errors.append(
                    f"definition:shapes:token drift: radius {name!r} is {actual!r}, "
                    f"expected {expected!r}"
                )


# --------------------------------------------------------------------------------------------------
# Renderer source + header
# --------------------------------------------------------------------------------------------------
def _validate_renderer(
    registry: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    renderer = registry.get("renderer")
    if not isinstance(renderer, dict):
        errors.append("registry:renderer:object required")
        return

    source_path = renderer.get("source")
    source = contents.get(source_path) if isinstance(source_path, str) else None
    if source is None:
        errors.append(f"renderer:source {source_path} missing")
        code = ""
    else:
        code = _without_cpp_comments(source)

    include = renderer.get("token_include")
    if isinstance(include, str) and code and f"#include {include}" not in code:
        errors.append(f"renderer:missing #include {include}")

    for marker in renderer.get("guard_markers", []):
        if isinstance(marker, str) and code and marker not in code:
            errors.append(f"renderer:guard marker missing in code ({marker})")

    # Every declared palette role must be consumed as a quoted literal in code.
    for role in registry.get("palette_tokens", []):
        if isinstance(role, str) and code and f'"{role}"' not in code:
            errors.append(f"renderer:palette role {role!r} not consumed in code")

    # Every anatomy region must carry each of its code markers.
    for entry in registry.get("anatomy", []):
        if not isinstance(entry, dict):
            errors.append("renderer:anatomy entry must be object")
            continue
        role = entry.get("role", "?")
        for marker in entry.get("markers", []):
            if isinstance(marker, str) and code and marker not in code:
                errors.append(f"renderer:anatomy:{role}:marker missing in code ({marker})")

    # Header must declare each geometry constant with the exact value.
    header_path = renderer.get("header")
    header = contents.get(header_path) if isinstance(header_path, str) else None
    if header is None:
        errors.append(f"renderer:header {header_path} missing")
    else:
        header_code = _without_cpp_comments(header)
        constants = renderer.get("geometry_constants", {})
        if isinstance(constants, dict):
            for name, value in constants.items():
                if not re.search(rf"\b{re.escape(name)}\s*=\s*{int(value)}\b", header_code):
                    errors.append(
                        f"renderer:header:geometry constant {name} != {value} (drift or missing)"
                    )


# --------------------------------------------------------------------------------------------------
# View wiring + empty-grid resources
# --------------------------------------------------------------------------------------------------
def _validate_views(
    registry: Mapping[str, Any], contents: Mapping[str, str], errors: list[str]
) -> None:
    resource_file = registry.get("empty_message_resource_file")
    resource_text = contents.get(resource_file) if isinstance(resource_file, str) else None
    if resource_text is None:
        errors.append(f"registry:empty_message_resource_file {resource_file} missing")

    views = registry.get("views")
    if not isinstance(views, list) or not views:
        errors.append("registry:views:non-empty array required")
        views = []
    if registry.get("expected_views") != len(views):
        errors.append("registry:expected_views:count drift")

    seen_ids: set[str] = set()
    for index, view in enumerate(views):
        context = f"views[{index}]"
        if not isinstance(view, dict):
            errors.append(f"{context}:object required")
            continue
        view_id = view.get("view_id")
        if not isinstance(view_id, str) or not view_id:
            errors.append(f"{context}:view_id:non-empty string required")
            continue
        context = f"view[{view_id}]"
        if view_id in seen_ids:
            errors.append(f"{context}:view_id:duplicate")
        seen_ids.add(view_id)

        if view.get("status") != "source-declared":
            errors.append(f"{context}:status:must be source-declared")
        if not isinstance(view.get("runtime_verified"), bool):
            errors.append(f"{context}:runtime_verified:boolean required")
        elif view["runtime_verified"]:
            errors.append(f"{context}:runtime_verified:no runtime evidence exists; must be false")

        source_path = view.get("source")
        source = contents.get(source_path) if isinstance(source_path, str) else None
        if source is None:
            errors.append(f"{context}:source {source_path} missing")
            continue
        code = _without_cpp_comments(source)

        for marker in view.get("markers", []):
            if isinstance(marker, str) and marker not in code:
                errors.append(f"{context}:marker missing in code ({marker})")

        fallthrough = view.get("fallthrough_marker")
        if isinstance(fallthrough, str) and fallthrough not in code:
            errors.append(
                f"{context}:non-Material fallback missing ({fallthrough}); "
                "the default paint path must be preserved"
            )

        # Migrated first-run pins (see the view's migration_note). The pre-rewrite
        # gate (IsMaterialStartCenterActive() && !mItemList.empty()) is REMOVED and
        # the Material path now owns the first-run render, so the pins flip from
        # "assert the gate + Welcome bitmap present" to:
        #
        #   * pinned_absent_markers  -- the removed gate must be gone from the file;
        #   * guard_absent_markers   -- the stock Welcome bitmap is REQUIRED-ABSENT
        #     from the Material guard block (it survives only on the stock path);
        #   * guard_present_markers  -- the invitation / no-match wiring must live
        #     inside the Material guard block;
        #   * stock_markers          -- the stock Welcome bitmap must still exist in
        #     the file (outside the guard) so the default theme stays releasable.
        for marker in view.get("pinned_absent_markers", []):
            if isinstance(marker, str) and marker in code:
                errors.append(
                    f"{context}:removed gate marker still present in code ({marker}); "
                    "the pre-rewrite empty-list gate must stay removed"
                )

        for marker in view.get("stock_markers", []):
            if isinstance(marker, str) and marker not in code:
                errors.append(
                    f"{context}:stock fallback marker missing in code ({marker}); "
                    "the non-Material Welcome path must be preserved"
                )

        guard_opener = view.get("guard_opener")
        guard_present = view.get("guard_present_markers", [])
        guard_absent = view.get("guard_absent_markers", [])
        if isinstance(guard_opener, str) and (guard_present or guard_absent):
            block = _guard_block(code, guard_opener)
            if block is None:
                errors.append(
                    f"{context}:Material guard block not found (opener {guard_opener!r}); "
                    "the guarded card path must be preserved"
                )
            else:
                for marker in guard_present:
                    if isinstance(marker, str) and marker not in block:
                        errors.append(
                            f"{context}:guard marker missing inside Material block ({marker})"
                        )
                for marker in guard_absent:
                    if isinstance(marker, str) and marker in block:
                        errors.append(
                            f"{context}:stock-only marker present inside Material block "
                            f"({marker}); it must be REQUIRED-ABSENT under the guard"
                        )

        # Invitation strings are authored by the Strings/Icons owner (F) in the same
        # wave; the frozen interface manifest fixes their macro names. Cross-check
        # copy fidelity only IF the macro is already defined -- the reference markers
        # above hard-pin the wiring regardless of F's landing order.
        for resource in view.get("invite_resources", []):
            if not isinstance(resource, str) or resource_text is None:
                continue
            if not re.search(rf"#define\s+{re.escape(resource)}\b", resource_text):
                continue
            if not re.search(
                rf'#define\s+{re.escape(resource)}\b.*?NC_\("{re.escape(resource)}",\s*"[^"]*"',
                resource_text,
                re.DOTALL,
            ):
                errors.append(
                    f"{context}:invitation resource {resource} defined but not a well-formed NC_ string"
                )

        resource = view.get("empty_message_resource")
        if isinstance(resource, str) and resource_text is not None:
            define = re.search(
                rf'#define\s+{re.escape(resource)}\b.*?NC_\("{re.escape(resource)}",\s*"([^"]*)"',
                resource_text,
                re.DOTALL,
            )
            if define is None:
                errors.append(f"{context}:empty resource {resource} not defined in {resource_file}")
            else:
                wanted = view.get("empty_message_contains")
                if isinstance(wanted, str) and wanted not in define.group(1):
                    errors.append(
                        f"{context}:empty resource {resource} copy {define.group(1)!r} lacks {wanted!r}"
                    )

    missing_required = REQUIRED_VIEW_IDS - seen_ids
    if missing_required:
        errors.append(f"registry:views:missing required {', '.join(sorted(missing_required))}")


# --------------------------------------------------------------------------------------------------
def violations(registry: Mapping[str, Any], contents: Mapping[str, str]) -> list[str]:
    errors: list[str] = []

    if registry.get("schema_version") != 1:
        errors.append("registry:schema_version:must be 1")
    if registry.get("contract") != "material-startcenter-cards":
        errors.append("registry:contract:unexpected value")
    if registry.get("platform") != "windows":
        errors.append("registry:platform:must be windows")
    if registry.get("definition_file") != DEFINITION_PATH:
        errors.append("registry:definition_file:unexpected path")
    if registry.get("runtime_verified") is not False:
        errors.append("registry:runtime_verified:no runtime evidence exists; must be false")

    root = _parse_definition(contents.get(DEFINITION_PATH, ""), errors)
    if root is not None:
        _validate_definition_tokens(registry, root, errors)

    _validate_renderer(registry, contents, errors)
    _validate_views(registry, contents, errors)

    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    registry, contents = load_repository(repo_root)
    errors = violations(registry, contents)
    if errors:
        raise ValidationError("\n".join(errors))


def main() -> int:
    try:
        validate_repository()
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Start Center card contract failed:\n{error}", file=sys.stderr)
        return 1
    registry, _ = load_repository()
    print(
        "Start Center card contract passed: "
        f"{len(registry['views'])} Material card grid(s) with palette/shape token fidelity, "
        "guarded renderer anatomy, and preserved non-Material fallbacks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
