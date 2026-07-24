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
* ``matcher_strategy`` -- how the controller state becomes results.  Three
                          strategies validate the owner's *changed handler* itself
                          (local compiled-once matching, options hand-off to an
                          existing engine, or native-regex toggle synchronisation).
                          The fourth strategy,
                          ``controller-driven-search-sites``, decouples the match
                          from the changed handler: the changed handler becomes a
                          declared, matching-free *trigger* and the real search runs
                          in one or more declared ``search_sites`` (a shared method,
                          a button-triggered handler, or an enumeration/predicate
                          pair).  Each site is validated with the same fail-closed
                          marker contract, merely relocated -- state/options obtained
                          exactly once per invocation, the legacy default preserved
                          through the compatibility route, regex/options opt-in only
                          through the controller, and no undeclared matcher hiding
                          anywhere in the owner source.

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
    "controller-driven-search-sites",
)

DEFAULT_MODES = (
    "literal-case-sensitive-indexof-compatible",
    "literal-case-insensitive-contains-compatible",
    "engine-preserving-current-default",
    "regex-native-case-insensitive",
)

# Which default_mode values each strategy may declare.  The
# controller-driven-search-sites strategy accepts every default_mode; the per-site
# ``site_route`` further constrains which mode is valid (see SITE_ROUTE_DEFAULT_MODES).
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
    "controller-driven-search-sites": {
        "literal-case-sensitive-indexof-compatible",
        "literal-case-insensitive-contains-compatible",
        "engine-preserving-current-default",
        "regex-native-case-insensitive",
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
    "regex-native-case-insensitive": True,
}
# default_mode values that additionally require the constructor to seed
# ``aState.Mode = sfx2::RegexSearchMode::Literal;``.  Engine-preserving surfaces
# may seed Mode from the live engine state instead, so Mode is not pinned there.
MODE_REQUIRES_LITERAL_SEED = {
    "literal-case-sensitive-indexof-compatible",
    "literal-case-insensitive-contains-compatible",
}
# default_mode values that instead require the constructor to seed
# ``aState.Mode = sfx2::RegexSearchMode::RegularExpression;``.  This is the honest
# default for a surface whose *legacy* matcher already runs a case-insensitive
# regular expression (e.g. the Manage Changes comment filter): pinning Literal
# there would silently regress an existing regex into a literal substring.
MODE_REQUIRES_REGEX_SEED = {
    "regex-native-case-insensitive",
}

# ---------------------------------------------------------------------------
# controller-driven-search-sites vocabulary.
#
# This strategy decouples *where* the search executes from the widget's changed
# handler.  The widget's changed handler becomes a declared, matching-free trigger
# (``changed_handler_role``); the real matching lives in one or more declared
# ``search_sites``, each validated against the same fail-closed marker contract the
# in-handler strategies use, merely relocated.  Every token below is fail-closed.
# ---------------------------------------------------------------------------

# What the widget's changed handler is allowed to do.  Mapped to the substring the
# declared ``changed_handler_trigger`` MUST contain, so the role name cannot drift
# from the marker it certifies.  ``forward-to-site`` is validated separately: its
# trigger must name a declared site method.
CHANGED_HANDLER_ROLES = {
    "debounce-timer-start": ".Start(",
    "button-enabler": "set_sensitive",
    "deferred-dirty-flag": "= true",
    "forward-to-site": None,
}

SITE_ROUTES = (
    "legacy-literal-filter",
    "options-handoff",
    "live-predicate",
)

# Which default_mode each site_route may pair with.  A single registry entry has
# one default_mode, so mixing routes with incompatible mode requirements is
# rejected here.
SITE_ROUTE_DEFAULT_MODES = {
    "legacy-literal-filter": {
        "literal-case-sensitive-indexof-compatible",
        "literal-case-insensitive-contains-compatible",
    },
    "live-predicate": {
        "literal-case-sensitive-indexof-compatible",
        "literal-case-insensitive-contains-compatible",
    },
    "options-handoff": {
        "engine-preserving-current-default",
        "regex-native-case-insensitive",
    },
}

# Site routes whose body compiles a utl::TextSearch (legacy-literal-filter) or
# whose enumeration site does (live-predicate).  Used to pin the *total* number of
# compiled matchers in the owner source so an undeclared matcher cannot hide.
SITE_ROUTES_THAT_COMPILE = {"legacy-literal-filter", "live-predicate"}


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


# ---------------------------------------------------------------------------
# Per-surface .ui layout validation.
#
# Most integrations share the stock two-control layout (the search entry fills
# position 0 of a horizontal GtkBox and the ``.*``-labelled builder button sits
# immediately after it at position 1).  A surface may instead declare, through an
# optional ``ui_layout`` registry object, that it ships the rewritten Material
# search *pill* -- a decorative leading glyph, the expanding entry, a clear
# button, a ``.*`` GtkToggleButton that owns the regex mode, and the advanced
# builder button carrying the tune glyph.  When declared, that exact composition
# is validated instead of the stock invariant; every other integration keeps the
# stock layout unchanged.  Both paths are fail-closed: a declared child that is
# out of order, mis-classed, mis-packed, or missing its accessible wiring fails.
# ---------------------------------------------------------------------------

MATERIAL_SEARCH_PILL = "material-search-pill"
# The builder button in the Material pill is icon-only; its glyph must resolve to
# the shared "tune" advanced-search icon rather than a text label.
PILL_BUILDER_ICON_SUBSTRING = "tune"


def _validate_pill_builder(
    context: str,
    builder_object: ET.Element,
    objects: Mapping[str, ET.Element],
    errors: list[str],
) -> None:
    """The Material pill builder is an icon-only accessible button (tune glyph)."""
    props = _properties(builder_object)
    image_id = props.get("image")
    icon_name = ""
    if image_id:
        image_object = objects.get(image_id)
        if image_object is not None:
            icon_name = _properties(image_object).get("icon-name", "")
    if PILL_BUILDER_ICON_SUBSTRING not in icon_name:
        errors.append(
            f"{context}:ui-pill-builder:builder must carry the tune advanced-search icon"
        )
    for name, expected in (
        ("visible", "True"),
        ("can-focus", "True"),
        ("receives-default", "False"),
    ):
        if props.get(name) != expected:
            errors.append(f"{context}:ui-pill-builder:{name} must be {expected}")
    if not props.get("tooltip-text"):
        errors.append(f"{context}:ui-accessibility:tooltip missing")
    elif not _property_is_translated(builder_object, "tooltip-text"):
        errors.append(f"{context}:ui-accessibility:tooltip must be translated")
    accessible_object = _accessible_object(builder_object)
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


def _validate_material_search_pill(
    context: str,
    layout: Mapping[str, Any],
    widget_kind: str,
    root: ET.Element,
    objects: Mapping[str, ET.Element],
    entry_id: str,
    button_id: str,
    errors: list[str],
) -> None:
    """Validate the rewritten Material search-pill composition declared by ``ui_layout``.

    The pill is one horizontal ``GtkBox`` (spacing 6) whose direct children are, in
    the exact declared order and packing positions: a decorative leading glyph, the
    expanding search entry, a clear button, a ``.*`` GtkToggleButton owning the
    regex mode, and the advanced-builder button carrying the tune glyph and its
    accessible name/description/tooltip.
    """
    allowed_classes = WIDGET_UI_CLASSES[widget_kind]
    entry_object = objects.get(entry_id)
    builder_object = objects.get(button_id)
    if entry_object is None or entry_object.get("class") not in allowed_classes:
        errors.append(
            f"{context}:ui-entry:{' or '.join(allowed_classes)} {entry_id} missing"
        )
    if builder_object is None or builder_object.get("class") != "GtkButton":
        errors.append(f"{context}:ui-button:GtkButton {button_id} missing")

    raw_children = layout.get("children")
    if not isinstance(raw_children, list) or not raw_children:
        errors.append(f"{context}:ui-pill:children array required")
        return

    if entry_object is None:
        return
    parents = {child: parent for parent in root.iter() for child in parent}
    pill = _nearest_parent_object(entry_object, parents)
    if pill is None:
        errors.append(f"{context}:ui-pill:search entry has no container")
        return
    container_id = layout.get("container_id")
    if isinstance(container_id, str) and container_id and pill.get("id") != container_id:
        errors.append(
            f"{context}:ui-pill:container {pill.get('id')!r} does not match declared {container_id!r}"
        )
    pill_properties = _properties(pill)
    if (
        pill.get("class") != "GtkBox"
        or pill_properties.get("orientation") != "horizontal"
        or pill_properties.get("spacing") != "6"
    ):
        errors.append(f"{context}:ui-pill:horizontal GtkBox with spacing 6 required")

    children = _direct_object_children(pill)
    actual_ids = [child.get("id", "") for child in children]
    declared_ids = [
        spec.get("id") for spec in raw_children if isinstance(spec, dict)
    ]
    if actual_ids != declared_ids:
        errors.append(
            f"{context}:ui-pill:child order {actual_ids} does not match declared {declared_ids}"
        )

    id_to_child = {child.get("id", ""): child for child in children}
    roles_seen: set[str] = set()
    for position, spec in enumerate(raw_children):
        if not isinstance(spec, dict):
            errors.append(f"{context}:ui-pill:child[{position}] must be an object")
            continue
        child_id = spec.get("id")
        child_class = spec.get("class")
        role = spec.get("role")
        if role:
            roles_seen.add(role)
        child = id_to_child.get(child_id) if isinstance(child_id, str) else None
        if child is None:
            errors.append(
                f"{context}:ui-pill:child {child_id!r} is not a direct sibling at position {position}"
            )
            continue
        if isinstance(child_class, str) and child.get("class") != child_class:
            errors.append(f"{context}:ui-pill:{child_id} must be class {child_class}")
        packing = _packing_properties(child, parents)
        if packing.get("position") != str(position):
            errors.append(f"{context}:ui-pill:{child_id} must be at packing position {position}")
        properties = _properties(child)
        if role == "decorative-icon":
            if child.get("class") != "GtkImage":
                errors.append(f"{context}:ui-pill:{child_id} decorative icon must be GtkImage")
            if properties.get("can-focus") != "False":
                errors.append(
                    f"{context}:ui-pill:{child_id} decorative icon must not be focusable"
                )
            if packing.get("expand") != "False":
                errors.append(f"{context}:ui-pill:{child_id} decorative icon must not expand")
        elif role == "entry":
            if child_id != entry_id:
                errors.append(f"{context}:ui-pill:entry role must be {entry_id}")
            if properties.get("hexpand") != "True":
                errors.append(f"{context}:ui-entry:hexpand must be True")
            if packing.get("expand") != "True" or packing.get("fill") != "True":
                errors.append(f"{context}:ui-pill:entry must expand and fill")
        elif role == "clear":
            if child.get("class") != "GtkButton":
                errors.append(f"{context}:ui-pill:{child_id} clear control must be GtkButton")
        elif role == "mode-toggle":
            if child.get("class") != "GtkToggleButton":
                errors.append(
                    f"{context}:ui-pill:{child_id} regex-mode control must be GtkToggleButton"
                )
            if properties.get("label") != ".*":
                errors.append(f"{context}:ui-pill:{child_id} regex-mode toggle must be labelled '.*'")
        elif role == "builder":
            if child_id != button_id:
                errors.append(f"{context}:ui-pill:builder role must be {button_id}")
            _validate_pill_builder(context, child, objects, errors)
        else:
            errors.append(f"{context}:ui-pill:{child_id} unknown role {role!r}")

    for required_role in ("entry", "mode-toggle", "builder"):
        if required_role not in roles_seen:
            errors.append(f"{context}:ui-pill:missing required role {required_role}")


def _validate_ui(
    context: str,
    entry: Mapping[str, Any],
    widget_kind: str,
    ui_text: str,
    entry_id: str,
    button_id: str,
    errors: list[str],
) -> None:
    """Validate the .ui: adjacent accessible builder button next to the search control.

    A surface may opt into the rewritten Material search-pill layout by declaring a
    ``ui_layout`` object; that composition is then validated per-surface (see
    ``_validate_material_search_pill``).  Every other surface keeps the stock
    entry-fills-position-0 / builder-follows-at-position-1 invariant below.
    """
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

    ui_layout = entry.get("ui_layout")
    if ui_layout is not None:
        if not isinstance(ui_layout, Mapping):
            errors.append(f"{context}:ui_layout:object required")
            return
        if ui_layout.get("kind") == MATERIAL_SEARCH_PILL:
            _validate_material_search_pill(
                context, ui_layout, widget_kind, root, objects, entry_id, button_id, errors
            )
            return
        errors.append(f"{context}:ui_layout:unsupported kind {ui_layout.get('kind')!r}")
        return

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
    if default_mode in MODE_REQUIRES_REGEX_SEED:
        required.append("aState.Mode = sfx2::RegexSearchMode::RegularExpression;")
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


# ---------------------------------------------------------------------------
# controller-driven-search-sites strategy.
#
# The widget's changed handler becomes a declared, matching-free *trigger* and the
# real search executes in one or more declared ``search_sites``.  Each site is
# validated with the same fail-closed marker contract the in-handler strategies use,
# merely relocated: the site obtains the controller state/options exactly once, the
# match subject is tested through the exact legacy-preserving compatibility route,
# regex/options beyond the default stay opt-in through the controller, and no
# undeclared compiled matcher may hide anywhere else in the owner source.
# ---------------------------------------------------------------------------


def _validate_changed_handler_trigger(
    context: str,
    body: str,
    controller_member: str,
    role: str,
    trigger: str,
    site_signatures: tuple[str, ...],
    errors: list[str],
) -> None:
    """The widget's changed handler must be a matching-free trigger.

    It carries the declared trigger marker (whose shape is pinned by the role) and
    performs no local matching -- matching lives only in declared sites.
    """
    _forbid_local_matching(
        context,
        body,
        (
            ("std::make_unique<utl::TextSearch>", "changed-compiled-matcher"),
            ("->searchForward", "changed-matching"),
            (".indexOf(rState.Pattern)", "changed-legacy-literal"),
            (f"{controller_member}->GetSearchOptions()", "changed-search-options"),
        ),
        errors,
    )
    if not trigger:
        return
    if body.count(trigger) != 1:
        errors.append(f"{context}:changed-handler-trigger:{trigger} expected exactly 1")
    role_marker = CHANGED_HANDLER_ROLES.get(role)
    if role_marker is not None and role_marker not in trigger:
        errors.append(
            f"{context}:changed-handler-role:{role} trigger must contain {role_marker!r}"
        )
    if role == "forward-to-site":
        called = re.findall(r"([A-Za-z_]\w*)\s*\(", trigger)
        if not called or not any(
            name in sig for name in called for sig in site_signatures
        ):
            errors.append(
                f"{context}:changed-handler-role:forward-to-site trigger must name a declared site"
            )


def _validate_live_predicate_site(
    context: str,
    site_index: int,
    enum_body: str,
    pred_body: str,
    controller_member: str,
    matcher_member: str,
    match_subject: str,
    errors: list[str],
) -> None:
    """Compile once in the enumeration; test each item in the predicate.

    A live per-item predicate cannot compile a matcher per item (that would be a
    second compile site and a performance regression), yet it must stay live so the
    filter cannot go stale while the underlying collection changes.  The enumeration
    entry obtains the state once and compiles the controller's matcher once into a
    member; the predicate applies the exact compatibility route through that member.
    """
    prefix = f"{context}:site[{site_index}]"
    enum_normalized = " ".join(enum_body.split())
    pred_normalized = " ".join(pred_body.split())

    for marker, count, label in (
        (f"{controller_member}->GetState()", 1, "enum-state"),
        ("sfx2::RegexSearchService::Validate(rState)", 1, "enum-validation"),
        ("std::make_unique<utl::TextSearch>", 1, "enum-compiled-matcher"),
        (f"{controller_member}->GetSearchOptions()", 1, "enum-search-options"),
    ):
        if enum_body.count(marker) != count:
            errors.append(f"{prefix}:{label}:expected exactly {count}")

    compile_marker = (
        f"{matcher_member} = std::make_unique<utl::TextSearch>("
        f"{controller_member}->GetSearchOptions());"
    )
    if compile_marker not in enum_normalized:
        errors.append(f"{prefix}:enum-compile-target:matcher member assignment missing")
    for marker in (
        "const bool bValid = bEmpty || "
        "sfx2::RegexSearchService::Validate(rState).IsValid;",
        "const bool bLegacyCompatibleLiteral = rState.Mode == "
        "sfx2::RegexSearchMode::Literal && !rState.Flags.CaseInsensitive;",
        "if (bValid && !bEmpty && !bLegacyCompatibleLiteral)",
    ):
        if marker not in enum_normalized:
            errors.append(f"{prefix}:enum-guard:missing {marker}")

    compile_at = enum_body.find("std::make_unique<utl::TextSearch>")
    loop_match = re.search(r"\bfor\s*\(", enum_body)
    if compile_at < 0 or (loop_match is not None and compile_at > loop_match.start()):
        errors.append(f"{prefix}:enum-compiled-once:matcher must be built before any loop")

    # The per-item test never lives in the enumeration.
    _forbid_local_matching(
        context,
        enum_body,
        (
            ("->searchForward", "enum-matching"),
            (".indexOf(rState.Pattern)", "enum-legacy-literal"),
        ),
        errors,
    )

    if pred_body.count(f"{controller_member}->GetState()") != 1:
        errors.append(f"{prefix}:predicate-state:expected exactly 1")
    if pred_body.count(f"{match_subject}.indexOf(rState.Pattern)") != 1:
        errors.append(f"{prefix}:predicate-legacy-literal:expected exactly 1")
    if pred_body.count(f"{matcher_member}->searchForward({match_subject})") != 1:
        errors.append(f"{prefix}:predicate-matching:expected exactly 1")

    predicate_route = (
        "bEmpty || (bLegacyCompatibleLiteral && "
        f"{match_subject}.indexOf(rState.Pattern) >= 0) || "
        f"({matcher_member} && {matcher_member}->searchForward({match_subject}))"
    )
    if predicate_route not in pred_normalized:
        errors.append(f"{prefix}:predicate-route:compatibility expression missing")
    if (
        "const bool bLegacyCompatibleLiteral = rState.Mode == "
        "sfx2::RegexSearchMode::Literal && !rState.Flags.CaseInsensitive;"
    ) not in pred_normalized:
        errors.append(f"{prefix}:predicate-guard:bLegacyCompatibleLiteral missing")

    # No per-item compile or options; those belong to the enumeration only.
    _forbid_local_matching(
        context,
        pred_body,
        (
            ("std::make_unique<utl::TextSearch>", "predicate-compiled-matcher"),
            (f"{controller_member}->GetSearchOptions()", "predicate-search-options"),
        ),
        errors,
    )


def _validate_controller_driven_sites(
    context: str,
    entry: Mapping[str, Any],
    source: str,
    header: str,
    controller_member: str,
    default_mode: str,
    changed_handler_body: str,
    errors: list[str],
) -> None:
    role = _required_text(entry, "changed_handler_role", context, errors)
    trigger = _required_text(entry, "changed_handler_trigger", context, errors)
    if role and role not in CHANGED_HANDLER_ROLES:
        errors.append(f"{context}:changed_handler_role:unsupported role")
        role = ""

    raw_sites = entry.get("search_sites")
    if not isinstance(raw_sites, list) or not raw_sites:
        errors.append(f"{context}:search_sites:non-empty array required")
        raw_sites = []

    site_signatures: list[str] = []
    compiling_sites = 0
    for site_index, raw_site in enumerate(raw_sites):
        prefix = f"{context}:site[{site_index}]"
        if not isinstance(raw_site, dict):
            errors.append(f"{prefix}:object required")
            continue
        signature = _required_text(raw_site, "signature", prefix, errors)
        route = _required_text(raw_site, "site_route", prefix, errors)
        if signature:
            site_signatures.append(signature)
        if route and route not in SITE_ROUTES:
            errors.append(f"{prefix}:site_route:unsupported route")
            route = ""
        if (
            route
            and default_mode
            and default_mode not in SITE_ROUTE_DEFAULT_MODES[route]
        ):
            errors.append(
                f"{prefix}:site_route:{route} incompatible with default_mode {default_mode}"
            )
        if route in SITE_ROUTES_THAT_COMPILE:
            compiling_sites += 1
        if not route or not signature:
            continue

        site_body = _function_body(source, signature)
        if site_body is None:
            errors.append(f"{prefix}:signature:site body not found for {signature}")
            continue
        site_normalized = " ".join(site_body.split())

        if route == "legacy-literal-filter":
            match_subject = _required_text(raw_site, "match_subject", prefix, errors)
            if match_subject:
                _validate_legacy_handler(
                    prefix, site_body, site_normalized, controller_member,
                    match_subject, errors,
                )
        elif route == "options-handoff":
            handoff_sink = _required_text(raw_site, "handoff_sink", prefix, errors)
            _validate_options_handoff_handler(
                prefix, site_body, site_normalized, controller_member,
                handoff_sink, errors,
            )
        elif route == "live-predicate":
            enum_signature = _required_text(
                raw_site, "enumeration_signature", prefix, errors
            )
            matcher_member = _required_text(raw_site, "matcher_member", prefix, errors)
            match_subject = _required_text(raw_site, "match_subject", prefix, errors)
            if enum_signature:
                # A forward-to-site changed handler may name the enumeration entry
                # rather than the per-item predicate, so both count as declared.
                site_signatures.append(enum_signature)
            enum_body = _function_body(source, enum_signature) if enum_signature else None
            if enum_signature and enum_body is None:
                errors.append(
                    f"{prefix}:enumeration_signature:enumeration body not found"
                )
            elif enum_body is not None and matcher_member and match_subject:
                _validate_live_predicate_site(
                    context, site_index, enum_body, site_body, controller_member,
                    matcher_member, match_subject, errors,
                )
            if matcher_member and (
                f"std::unique_ptr<utl::TextSearch> {matcher_member};" not in header
            ):
                errors.append(
                    f"{prefix}:matcher-member:std::unique_ptr<utl::TextSearch> "
                    f"{matcher_member} member missing"
                )

    # Every compiled matcher in the owner source must belong to a declared compiling
    # site; a stray make_unique<utl::TextSearch> is an undeclared bypass matcher.
    total_compiles = source.count("std::make_unique<utl::TextSearch>")
    if total_compiles != compiling_sites:
        errors.append(
            f"{context}:undeclared-matcher:source has {total_compiles} compiled matcher(s), "
            f"expected {compiling_sites} from declared sites"
        )
    if compiling_sites and "#include <unotools/textsearch.hxx>" not in source:
        errors.append(f"{context}:source-wiring:missing #include <unotools/textsearch.hxx>")

    _validate_changed_handler_trigger(
        context, changed_handler_body, controller_member, role, trigger,
        tuple(site_signatures), errors,
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

        # Stage 1 inline `.*` mode-toggle registration.  A surface that ships the
        # inline RegexSearchController::ToggleMode() button declares its widget id
        # here; the field is optional this stage (the 13-surface rollout plus the
        # persistence_key / invalid_pattern_policy fields land in a later stage).
        # When declared it must be a non-empty widget id and reconcile with the
        # coverage field's inline_mode_toggle_id so the two registries can never
        # silently drift on the toggle id.
        mode_toggle_id = entry.get("mode_toggle_id")
        if mode_toggle_id is not None:
            if not isinstance(mode_toggle_id, str) or not mode_toggle_id.strip():
                errors.append(
                    f"{context}:mode_toggle_id:non-empty widget id required when declared"
                )
            elif (
                covered is not None
                and covered.get("inline_mode_toggle_id") != mode_toggle_id
            ):
                errors.append(
                    f"{context}:mode_toggle_id:coverage inline_mode_toggle_id must match "
                    f"{mode_toggle_id!r}"
                )

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
        if f"{button_member}->connect_clicked" in source:
            errors.append(f"{context}:source-wiring:direct builder click bypasses controller")

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
            elif matcher_strategy == "controller-driven-search-sites":
                _validate_controller_driven_sites(
                    context, entry, source, header, controller_member,
                    default_mode, body, errors,
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
