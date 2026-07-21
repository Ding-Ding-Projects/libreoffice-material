#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Validate source-complete native integrations of the shared regex builder.

This checker is a strict *parameterized* contract, not a single hard-coded
template.  Every registered integration declares three orthogonal parameters and
the checker cross-validates the .ui, header, constructor and handler against the
exact, fail-closed marker set implied by that combination:

* ``widget_kind``      -- "entry" (GtkEntry / weld::Entry) or "combobox"
                          (editable GtkComboBox[Text] / weld::ComboBox).  This
                          selects the widget class, the member type, the weld
                          factory, the handler argument type and therefore the
                          matching ``RegexSearchController`` constructor overload.
* ``default_mode``     -- the seeded ``RegexSearchState`` the constructor installs
                          before the user opts in through the builder.  The
                          declared mode pins the ``CaseInsensitive`` flag the
                          constructor MUST set; the value is never optional.
* ``matcher_strategy`` -- how the owner's changed handler turns the controller
                          state into results.  Each strategy has its own required
                          marker contract (local compiled-once matching, options
                          hand-off to an existing engine, or native-regex toggle
                          synchronisation).

Adding a parameter combination never weakens the checker: an unsupported or
mismatched combination fails closed.  If a search surface cannot honestly satisfy
any supported combination it stays unintegrated.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping


REPOSITORY = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "qa/windows-ui-contract/regex-search-integrations.json"
COVERAGE_PATH = "qa/windows-ui-contract/search-field-coverage.json"
CONTROLLER_SOURCE = "sfx2/source/dialog/RegexSearchController.cxx"


# ---------------------------------------------------------------------------
# Parameter vocabulary.  Every value below is fail-closed: an entry that names a
# token outside these sets, or a (strategy, default_mode) pair outside
# ``STRATEGY_DEFAULT_MODES``, is rejected.
# ---------------------------------------------------------------------------

WIDGET_KINDS = ("entry", "combobox")

# Allowed .ui object classes for the search control, per widget_kind.
WIDGET_UI_CLASSES = {
    "entry": ("GtkEntry",),
    "combobox": ("GtkComboBox", "GtkComboBoxText"),
}
# weld member declaration type, per widget_kind.
WIDGET_MEMBER_TYPE = {
    "entry": "weld::Entry",
    "combobox": "weld::ComboBox",
}
# GtkBuilder weld factory call, per widget_kind.
WIDGET_WELD_FACTORY = {
    "entry": "weld_entry",
    "combobox": "weld_combo_box",
}
# IMPL_LINK_NOARG / DECL_LINK argument type, per widget_kind.  This is the type
# the matching RegexSearchController constructor overload forwards to.
WIDGET_HANDLER_ARG = {
    "entry": "weld::TextWidget&",
    "combobox": "weld::ComboBox&",
}

MATCHER_STRATEGIES = (
    "legacy-literal-or-compiled-once-utl-textsearch",
    "options-handoff-to-existing-search-engine",
    "native-regex-option-sync",
)

DEFAULT_MODES = (
    "literal-case-sensitive-indexof-compatible",
    "literal-case-insensitive-contains-compatible",
    "engine-preserving-current-default",
)

# Which default_mode values each strategy may declare.
STRATEGY_DEFAULT_MODES = {
    "legacy-literal-or-compiled-once-utl-textsearch": {
        "literal-case-sensitive-indexof-compatible",
        "literal-case-insensitive-contains-compatible",
    },
    "options-handoff-to-existing-search-engine": {
        "engine-preserving-current-default",
    },
    "native-regex-option-sync": {
        "engine-preserving-current-default",
    },
}

# The CaseInsensitive flag the constructor MUST seed for a given default_mode.
# ``None`` means the value is taken from the per-entry
# ``engine_default_case_insensitive`` boolean (engine-preserving surfaces mirror
# the existing engine's default, which the entry must state explicitly).
MODE_CASE_INSENSITIVE = {
    "literal-case-sensitive-indexof-compatible": False,
    "literal-case-insensitive-contains-compatible": True,
    "engine-preserving-current-default": None,
}
# default_mode values that additionally require the constructor to seed
# ``aState.Mode = sfx2::RegexSearchMode::Literal;``.  Engine-preserving surfaces
# may seed Mode from the live engine state instead, so Mode is not pinned there.
MODE_REQUIRES_LITERAL_SEED = {
    "literal-case-sensitive-indexof-compatible",
    "literal-case-insensitive-contains-compatible",
}


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _required_text(entry: Mapping[str, Any], key: str, context: str, errors: list[str]) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{context}:{key}:non-empty text required")
        return ""
    return value


def _function_body(source: str, signature: str) -> str | None:
    start = source.find(signature)
    if start < 0:
        return None
    opening = source.find("{", start + len(signature))
    if opening < 0:
        return None
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    return None


def _without_cpp_comments(source: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", source, flags=re.DOTALL)


def _properties(element: ET.Element) -> dict[str, str]:
    return {
        child.get("name", ""): (child.text or "").strip()
        for child in element
        if child.tag.rsplit("}", 1)[-1] == "property"
    }


def _property_element(element: ET.Element, name: str) -> ET.Element | None:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] == "property" and child.get("name") == name:
            return child
    return None


def _property_is_translated(element: ET.Element, name: str) -> bool:
    prop = _property_element(element, name)
    return (
        prop is not None
        and prop.get("translatable") == "yes"
        and bool(prop.get("context"))
    )


def _nearest_parent_object(
    element: ET.Element, parents: Mapping[ET.Element, ET.Element]
) -> ET.Element | None:
    parent = parents.get(element)
    while parent is not None:
        if parent.tag.rsplit("}", 1)[-1] == "object":
            return parent
        parent = parents.get(parent)
    return None


def _direct_object_children(element: ET.Element) -> list[ET.Element]:
    result: list[ET.Element] = []
    for child in element:
        if child.tag.rsplit("}", 1)[-1] != "child":
            continue
        result.extend(
            grandchild
            for grandchild in child
            if grandchild.tag.rsplit("}", 1)[-1] == "object"
        )
    return result


def _packing_properties(
    element: ET.Element, parents: Mapping[ET.Element, ET.Element]
) -> dict[str, str]:
    wrapper = parents.get(element)
    if wrapper is None or wrapper.tag.rsplit("}", 1)[-1] != "child":
        return {}
    for child in wrapper:
        if child.tag.rsplit("}", 1)[-1] == "packing":
            return _properties(child)
    return {}


def _accessible_object(element: ET.Element) -> ET.Element | None:
    for child in element:
        if child.tag.rsplit("}", 1)[-1] != "child" or child.get("internal-child") != "accessible":
            continue
        for candidate in child:
            if candidate.tag.rsplit("}", 1)[-1] == "object":
                return candidate
    return None


def load_repository(
    repo_root: Path = REPOSITORY,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    registry = _read_json(repo_root / REGISTRY_PATH)
    coverage = _read_json(repo_root / COVERAGE_PATH)
    paths = {REGISTRY_PATH, COVERAGE_PATH, CONTROLLER_SOURCE}
    for raw_entry in registry.get("integrations", []):
        if not isinstance(raw_entry, dict):
            continue
        for key in ("ui_file", "header_file", "source_file"):
            value = raw_entry.get(key)
            if isinstance(value, str) and value:
                paths.add(value)
    contents: dict[str, str] = {}
    for relative in paths:
        path = repo_root / relative
        if path.is_file():
            contents[relative] = path.read_text(encoding="utf-8")
    return registry, coverage, contents


def _validate_ui(
    context: str,
    entry: Mapping[str, Any],
    widget_kind: str,
    ui_text: str,
    entry_id: str,
    button_id: str,
    errors: list[str],
) -> None:
    """Validate the .ui: adjacent accessible builder button next to the search control."""
    try:
        root = ET.fromstring(ui_text)
    except ET.ParseError as error:
        errors.append(f"{context}:ui-xml:{error}")
        return

    objects = {
        element.get("id", ""): element
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "object" and element.get("id")
    }
    entry_object = objects.get(entry_id)
    button_object = objects.get(button_id)
    allowed_classes = WIDGET_UI_CLASSES[widget_kind]
    if entry_object is None or entry_object.get("class") not in allowed_classes:
        errors.append(
            f"{context}:ui-entry:{' or '.join(allowed_classes)} {entry_id} missing"
        )
    if button_object is None or button_object.get("class") != "GtkButton":
        errors.append(f"{context}:ui-button:GtkButton {button_id} missing")

    # An editable combo box must actually own an entry so the ComboBox controller
    # overload's has_entry() precondition holds; a read-only combo cannot host a
    # text query and must not masquerade as one.
    if (
        widget_kind == "combobox"
        and entry_object is not None
        and entry_object.get("class") in allowed_classes
        and _properties(entry_object).get("has-entry") != "True"
    ):
        errors.append(f"{context}:ui-entry:editable combobox requires has-entry True")

    if entry_object is not None and button_object is not None:
        parents = {child: parent for parent in root.iter() for child in parent}
        entry_parent = _nearest_parent_object(entry_object, parents)
        button_parent = _nearest_parent_object(button_object, parents)
        if entry_parent is None or entry_parent is not button_parent:
            errors.append(f"{context}:ui-adjacency:entry and builder need one parent")
        else:
            parent_properties = _properties(entry_parent)
            if (
                entry_parent.get("class") != "GtkBox"
                or parent_properties.get("orientation") != "horizontal"
                or parent_properties.get("spacing") != "6"
            ):
                errors.append(
                    f"{context}:ui-parent:horizontal GtkBox with spacing 6 required"
                )
            children = _direct_object_children(entry_parent)
            try:
                entry_position = children.index(entry_object)
                button_position = children.index(button_object)
            except ValueError:
                errors.append(f"{context}:ui-adjacency:controls are not direct siblings")
            else:
                if button_position != entry_position + 1:
                    errors.append(f"{context}:ui-adjacency:builder must follow entry")

            entry_packing = _packing_properties(entry_object, parents)
            button_packing = _packing_properties(button_object, parents)
            if entry_packing != {"expand": "True", "fill": "True", "position": "0"}:
                errors.append(f"{context}:ui-packing:entry must fill position 0")
            if button_packing != {"expand": "False", "fill": "True", "position": "1"}:
                errors.append(f"{context}:ui-packing:builder must fit position 1")

        entry_properties = _properties(entry_object)
        if entry_properties.get("hexpand") != "True":
            errors.append(f"{context}:ui-entry:hexpand must be True")
        button_properties = _properties(button_object)
        for name, expected in (
            ("label", ".*"),
            ("visible", "True"),
            ("can-focus", "True"),
            ("receives-default", "False"),
        ):
            if button_properties.get(name) != expected:
                errors.append(f"{context}:ui-button:{name} must be {expected}")
        if not button_properties.get("tooltip-text"):
            errors.append(f"{context}:ui-accessibility:tooltip missing")
        elif not _property_is_translated(button_object, "tooltip-text"):
            errors.append(f"{context}:ui-accessibility:tooltip must be translated")
        accessible_object = _accessible_object(button_object)
        accessible = _properties(accessible_object) if accessible_object is not None else {}
        for name in (
            "AtkObject::accessible-name",
            "AtkObject::accessible-description",
        ):
            if not accessible.get(name):
                errors.append(f"{context}:ui-accessibility:{name} missing")
            elif accessible_object is not None and not _property_is_translated(
                accessible_object, name
            ):
                errors.append(f"{context}:ui-accessibility:{name} must be translated")

    # native-regex-option-sync surfaces re-use the dialog's existing "Regular
    # expression" check button; the declared toggle must exist as a check button.
    if entry.get("matcher_strategy") == "native-regex-option-sync":
        toggle_id = entry.get("native_regex_toggle_id")
        if isinstance(toggle_id, str) and toggle_id:
            toggle_object = objects.get(toggle_id)
            if toggle_object is None or toggle_object.get("class") not in (
                "GtkCheckButton",
                "GtkToggleButton",
            ):
                errors.append(
                    f"{context}:ui-native-toggle:GtkCheckButton {toggle_id} missing"
                )


def _validate_constructor(
    context: str,
    constructor: str,
    controller_member: str,
    controller_parent: str,
    entry_member: str,
    button_member: str,
    owner_type: str,
    handler: str,
    default_mode: str,
    case_insensitive: bool | None,
    errors: list[str],
) -> None:
    controller_wiring = re.compile(
        re.escape(controller_member)
        + r"\s*=\s*std::make_unique<sfx2::RegexSearchController>\s*\(\s*"
        + re.escape(controller_parent)
        + r"\s*,\s*\*"
        + re.escape(entry_member)
        + r"\s*,\s*\*"
        + re.escape(button_member)
        + r"\s*,\s*LINK\s*\(\s*this\s*,\s*"
        + re.escape(owner_type)
        + r"\s*,\s*"
        + re.escape(handler)
        + r"\s*\)\s*\)\s*;"
    )
    if controller_wiring.search(constructor) is None:
        errors.append(f"{context}:source-wiring:controller constructor mismatch")

    required = [f"{controller_member}->SetState(aState);"]
    if default_mode in MODE_REQUIRES_LITERAL_SEED:
        required.append("aState.Mode = sfx2::RegexSearchMode::Literal;")
    if case_insensitive is not None:
        # The seeded CaseInsensitive flag is cross-validated against the declared
        # default_mode and is never optional.
        required.append(
            f"aState.Flags.CaseInsensitive = {'true' if case_insensitive else 'false'};"
        )
    for marker in required:
        if marker not in constructor:
            errors.append(f"{context}:literal-default:missing {marker}")


def _validate_legacy_handler(
    context: str,
    body: str,
    normalized_body: str,
    controller_member: str,
    match_subject: str,
    errors: list[str],
) -> None:
    marker_counts = (
        (f"{controller_member}->GetState()", 1, "state"),
        ("sfx2::RegexSearchService::Validate(rState)", 1, "validation"),
        ("std::make_unique<utl::TextSearch>", 1, "compiled-matcher"),
        (f"{controller_member}->GetSearchOptions()", 1, "search-options"),
        ("xSearch->searchForward", 1, "matching"),
        (f"{match_subject}.indexOf(rState.Pattern)", 1, "legacy-literal"),
    )
    for marker, count, label in marker_counts:
        if body.count(marker) != count:
            errors.append(f"{context}:handler-{label}:expected exactly {count}")

    compile_at = body.find("std::make_unique<utl::TextSearch>")
    loop_match = re.search(r"\bfor\s*\(", body)
    if compile_at < 0 or loop_match is None or compile_at > loop_match.start():
        errors.append(f"{context}:compiled-once:matcher must be built before the loop")
    if re.search(r"\bwhile\s*\(", body):
        errors.append(f"{context}:handler-zero-width:repeated matcher loop forbidden")

    # The declared match subject must be the range-for loop variable, so the
    # compatibility markers below cannot point at an unrelated identifier.
    subject_loop = re.compile(
        r"\bfor\s*\(\s*const\s+OUString&\s+" + re.escape(match_subject) + r"\s*:"
    )
    if subject_loop.search(body) is None:
        errors.append(
            f"{context}:handler-match-subject:{match_subject} must be the range-for loop variable"
        )

    compatibility_markers = (
        "const bool bValid = bEmpty || "
        "sfx2::RegexSearchService::Validate(rState).IsValid;",
        "const bool bLegacyCompatibleLiteral = rState.Mode == "
        "sfx2::RegexSearchMode::Literal && !rState.Flags.CaseInsensitive;",
        "if (bValid && !bEmpty && !bLegacyCompatibleLiteral)",
        "bEmpty || (bLegacyCompatibleLiteral && "
        f"{match_subject}.indexOf(rState.Pattern) >= 0) || "
        f"(xSearch && xSearch->searchForward({match_subject}))",
    )
    for marker in compatibility_markers:
        if marker not in normalized_body:
            errors.append(f"{context}:handler:compatibility route missing {marker}")
    if "bEmpty || (bLegacyCompatibleLiteral &&" not in normalized_body:
        errors.append(f"{context}:handler:empty/invalid fail-closed route missing")


def _forbid_local_matching(
    context: str,
    body: str,
    forbidden: tuple[tuple[str, str], ...],
    errors: list[str],
) -> None:
    for marker, label in forbidden:
        if marker in body:
            errors.append(f"{context}:handler-{label}:local matching path forbidden")


def _validate_options_handoff_handler(
    context: str,
    body: str,
    normalized_body: str,
    controller_member: str,
    handoff_sink: str,
    errors: list[str],
) -> None:
    if body.count(f"{controller_member}->GetSearchOptions()") != 1:
        errors.append(f"{context}:handler-search-options:expected exactly 1")
    _forbid_local_matching(
        context,
        body,
        (
            ("std::make_unique<utl::TextSearch>", "compiled-matcher"),
            ("->searchForward", "matching"),
            (".indexOf(rState.Pattern)", "legacy-literal"),
        ),
        errors,
    )
    if handoff_sink and handoff_sink not in normalized_body:
        errors.append(f"{context}:handler-handoff:sink {handoff_sink} missing")


def _validate_native_sync_handler(
    context: str,
    body: str,
    controller_member: str,
    native_regex_toggle: str,
    errors: list[str],
) -> None:
    if body.count(f"{controller_member}->GetState()") != 1:
        errors.append(f"{context}:handler-state:expected exactly 1")
    sync_marker = (
        f"{native_regex_toggle}->set_active(rState.Mode == "
        "sfx2::RegexSearchMode::RegularExpression)"
    )
    if native_regex_toggle and body.count(sync_marker) != 1:
        errors.append(f"{context}:handler-native-regex-sync:expected exactly 1")
    _forbid_local_matching(
        context,
        body,
        (
            ("std::make_unique<utl::TextSearch>", "compiled-matcher"),
            ("->searchForward", "matching"),
            (".indexOf(rState.Pattern)", "legacy-literal"),
            (f"{controller_member}->GetSearchOptions()", "search-options"),
        ),
        errors,
    )


def violations(
    registry: Mapping[str, Any],
    coverage: Mapping[str, Any],
    contents: Mapping[str, str],
) -> list[str]:
    errors: list[str] = []
    if registry.get("schema_version") != 1:
        errors.append("registry:schema_version:must be 1")
    if registry.get("contract") != "windows-native-regex-search-integrations":
        errors.append("registry:contract:unexpected value")
    if registry.get("platform") != "windows":
        errors.append("registry:platform:must be windows")

    raw_integrations = registry.get("integrations")
    if not isinstance(raw_integrations, list):
        errors.append("registry:integrations:array required")
        raw_integrations = []
    if not raw_integrations:
        errors.append("registry:integrations:at least one source integration required")
    if registry.get("expected_integrations") != len(raw_integrations):
        errors.append("registry:expected_integrations:count drift")

    shipping = {
        item.get("coverage_id"): item
        for item in coverage.get("shipping_fields", [])
        if isinstance(item, dict) and isinstance(item.get("coverage_id"), str)
    }
    seen_ids: set[str] = set()
    seen_controls: set[tuple[str, str]] = set()

    controller_source = contents.get(CONTROLLER_SOURCE, "")
    for marker, label in (
        ("set_accessible_name(SfxResId(STR_REGEX_BUILDER_ACCESSIBLE_NAME))", "name"),
        (
            "set_accessible_description(\n"
            "        SfxResId(STR_REGEX_BUILDER_ACCESSIBLE_DESCRIPTION))",
            "description",
        ),
        ("set_tooltip_text(SfxResId(STR_REGEX_BUILDER_TOOLTIP))", "tooltip"),
    ):
        if marker not in controller_source:
            errors.append(f"shared-controller-accessibility:{label}:marker missing")

    required_keys = (
        "coverage_id",
        "surface",
        "status",
        "ui_file",
        "entry_id",
        "builder_button_id",
        "header_file",
        "source_file",
        "owner_type",
        "owner_changed_handler",
        "entry_member",
        "builder_member",
        "controller_member",
        "controller_parent",
        "widget_kind",
        "matcher_strategy",
        "default_mode",
    )

    for index, raw_entry in enumerate(raw_integrations):
        context = f"integrations[{index}]"
        if not isinstance(raw_entry, dict):
            errors.append(f"{context}:object required")
            continue
        entry = raw_entry
        values = {key: _required_text(entry, key, context, errors) for key in required_keys}
        coverage_id = values["coverage_id"]
        ui_file = values["ui_file"]
        entry_id = values["entry_id"]
        button_id = values["builder_button_id"]
        header_file = values["header_file"]
        source_file = values["source_file"]
        owner_type = values["owner_type"]
        handler = values["owner_changed_handler"]
        entry_member = values["entry_member"]
        button_member = values["builder_member"]
        controller_member = values["controller_member"]
        widget_kind = values["widget_kind"]
        matcher_strategy = values["matcher_strategy"]
        default_mode = values["default_mode"]

        if coverage_id in seen_ids:
            errors.append(f"{context}:coverage_id:duplicate {coverage_id}")
        seen_ids.add(coverage_id)
        control_key = (ui_file, entry_id)
        if control_key in seen_controls:
            errors.append(f"{context}:control:duplicate {ui_file}#{entry_id}")
        seen_controls.add(control_key)

        covered = shipping.get(coverage_id)
        if covered is None:
            errors.append(f"{context}:coverage-link:not a shipping search field")
        elif (
            covered.get("ui_file") != ui_file
            or covered.get("widget_id") != entry_id
            or covered.get("regex_builder") != "adjacent-advanced-builder"
        ):
            errors.append(f"{context}:coverage-link:registry locator or policy mismatch")

        if values["status"] != "source-integrated":
            errors.append(f"{context}:status:must be source-integrated")
        if not isinstance(entry.get("runtime_verified"), bool):
            errors.append(f"{context}:runtime_verified:boolean required")

        # -- Parameter vocabulary and (strategy, default_mode) compatibility ----
        if widget_kind and widget_kind not in WIDGET_KINDS:
            errors.append(f"{context}:widget_kind:unsupported kind")
            widget_kind = ""
        if matcher_strategy and matcher_strategy not in MATCHER_STRATEGIES:
            errors.append(f"{context}:matcher_strategy:unsupported strategy")
            matcher_strategy = ""
        if default_mode and default_mode not in DEFAULT_MODES:
            errors.append(f"{context}:default_mode:unsupported mode")
            default_mode = ""
        if (
            matcher_strategy
            and default_mode
            and default_mode not in STRATEGY_DEFAULT_MODES[matcher_strategy]
        ):
            errors.append(
                f"{context}:default_mode:incompatible with matcher_strategy {matcher_strategy}"
            )

        # -- Conditionally-required, strategy/mode-specific fields --------------
        match_subject = ""
        handoff_sink = ""
        native_regex_toggle = ""
        case_insensitive: bool | None = (
            MODE_CASE_INSENSITIVE.get(default_mode) if default_mode else False
        )
        if matcher_strategy == "legacy-literal-or-compiled-once-utl-textsearch":
            match_subject = _required_text(entry, "match_subject", context, errors)
        if matcher_strategy == "options-handoff-to-existing-search-engine":
            handoff_sink = _required_text(entry, "handoff_sink", context, errors)
        if matcher_strategy == "native-regex-option-sync":
            native_regex_toggle = _required_text(entry, "native_regex_toggle", context, errors)
            _required_text(entry, "native_regex_toggle_id", context, errors)
        if default_mode == "engine-preserving-current-default":
            declared = entry.get("engine_default_case_insensitive")
            if not isinstance(declared, bool):
                errors.append(
                    f"{context}:engine_default_case_insensitive:boolean required"
                )
                case_insensitive = None
            else:
                case_insensitive = declared

        ui_text = contents.get(ui_file)
        if ui_text is None:
            errors.append(f"{context}:ui-file:missing {ui_file}")
        elif widget_kind:
            _validate_ui(context, entry, widget_kind, ui_text, entry_id, button_id, errors)

        header = _without_cpp_comments(contents.get(header_file, ""))
        member_type = WIDGET_MEMBER_TYPE.get(widget_kind, "weld::Entry")
        for marker, label in (
            ("class RegexSearchController;", "controller-forward-declaration"),
            (f"std::unique_ptr<weld::Button> {button_member};", "builder-member"),
            (
                f"std::unique_ptr<sfx2::RegexSearchController> {controller_member};",
                "controller-member",
            ),
        ):
            if marker not in header:
                errors.append(f"{context}:header:{label} missing")

        entry_member_at = header.find(f"std::unique_ptr<{member_type}> {entry_member};")
        button_member_at = header.find(f"std::unique_ptr<weld::Button> {button_member};")
        controller_member_at = header.find(
            f"std::unique_ptr<sfx2::RegexSearchController> {controller_member};"
        )
        if entry_member_at < 0:
            errors.append(
                f"{context}:header:{member_type} {entry_member} member missing"
            )
        if (
            entry_member_at < 0
            or button_member_at < 0
            or controller_member_at < entry_member_at
            or controller_member_at < button_member_at
        ):
            errors.append(
                f"{context}:header:lifetime:controller must follow the entry and button"
            )

        source = _without_cpp_comments(contents.get(source_file, ""))
        weld_factory = WIDGET_WELD_FACTORY.get(widget_kind, "weld_entry")
        source_markers = [
            "#include <sfx2/RegexSearchController.hxx>",
            f'{weld_factory}(u"{entry_id}"_ustr)',
            f'weld_button(u"{button_id}"_ustr)',
        ]
        if matcher_strategy == "legacy-literal-or-compiled-once-utl-textsearch":
            source_markers.append("#include <unotools/textsearch.hxx>")
        if matcher_strategy == "native-regex-option-sync":
            toggle_id = entry.get("native_regex_toggle_id")
            if isinstance(toggle_id, str) and toggle_id:
                source_markers.append(f'weld_check_button(u"{toggle_id}"_ustr)')
        for marker in source_markers:
            if marker not in source:
                errors.append(f"{context}:source-wiring:missing {marker}")
        if f"{entry_member}->connect_changed" in source:
            errors.append(f"{context}:source-wiring:direct changed handler bypasses controller")

        # The handler argument type is the type the declared widget_kind's
        # controller overload forwards, so it also cross-checks widget_kind.
        if widget_kind:
            handler_signature = (
                f"IMPL_LINK_NOARG({owner_type}, {handler}, "
                f"{WIDGET_HANDLER_ARG[widget_kind]}, void)"
            )
            if handler_signature not in source:
                errors.append(
                    f"{context}:handler:signature must be {handler_signature}"
                )

        constructor = _function_body(source, f"{owner_type}::{owner_type}(")
        if constructor is None:
            errors.append(f"{context}:constructor:not found")
        elif default_mode:
            _validate_constructor(
                context,
                constructor,
                controller_member,
                values["controller_parent"],
                entry_member,
                button_member,
                owner_type,
                handler,
                default_mode,
                case_insensitive,
                errors,
            )

        body = _function_body(source, f"IMPL_LINK_NOARG({owner_type}, {handler}")
        if body is None:
            errors.append(f"{context}:handler:not found")
        elif matcher_strategy:
            normalized_body = " ".join(body.split())
            if matcher_strategy == "legacy-literal-or-compiled-once-utl-textsearch":
                _validate_legacy_handler(
                    context, body, normalized_body, controller_member, match_subject, errors
                )
            elif matcher_strategy == "options-handoff-to-existing-search-engine":
                _validate_options_handoff_handler(
                    context, body, normalized_body, controller_member, handoff_sink, errors
                )
            elif matcher_strategy == "native-regex-option-sync":
                _validate_native_sync_handler(
                    context, body, controller_member, native_regex_toggle, errors
                )

    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    registry, coverage, contents = load_repository(repo_root)
    errors = violations(registry, coverage, contents)
    if errors:
        raise ValidationError("\n".join(errors))


def main() -> int:
    try:
        validate_repository()
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Windows regex-search integration contract failed:\n{error}", file=sys.stderr)
        return 1
    registry, _, _ = load_repository()
    print(
        "Windows regex-search integrations passed: "
        f"{len(registry['integrations'])} source-integrated field(s) with adjacent accessible "
        "builder, controller-owned callback, and per-strategy fail-closed matching contracts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
