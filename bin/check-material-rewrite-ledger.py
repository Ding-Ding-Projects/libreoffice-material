#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed Material-rewrite burn-down ledger for the full-program rewrite.

``qa/windows-ui-contract/material-rewrite-ledger.json`` is the single headline
instrument of the Material rewrite program. Its measured universe is derived
1:1 from the WIN-SYS-016 registry closure
(``qa/windows-ui-contract/ui-registry.json``): every one of the owner-mapped
surfaces (the ``.ui`` files plus the native-only surfaces) is exactly one ledger
row carrying ``rewrite_status`` (``pending`` | ``in-progress`` |
``rewritten-material``) and ``rewrite_evidence``.

The ledger derives its rows by IMPORTING ``build_registry()`` from
``bin/check-windows-ui-registry-closure.py`` -- it never re-walks Git itself, so
the two files are structurally impossible to diverge undetected. Each surface is
classified into one of nine families (dialog, message-dialog, options-page,
panel-fragment, menu, popover, sidebar-panel, wizard-assistant, native-shell)
whose acceptance predicate ("is this surface rewritten to Material?") is either
static (parsed from the ``.ui`` XML: dialog/message/surface-body/popover) or a
cross-reference to the composition contract that owns the surface (menu,
sidebar-panel, native-shell -- families the theme renders, so their ``.ui``
carries no static Material fingerprint and static --evaluate never credits them).

Field ownership split (the invariant that lets ``--regenerate`` re-sync
structure without touching campaign progress):

* ``owner`` / ``inventory_id`` -- COPIED from the closure and parity-locked.
* ``family`` / ``rewrite_class`` -- recomputed by the classifier on regenerate.
* ``rewrite_status`` / ``rewrite_evidence`` -- the ONLY campaign-mutable state a
  wave edits; preserved verbatim across regeneration.

``--regenerate`` rewrites the row set (structure only, statuses preserved).
``--evaluate`` goes further: it STATICALLY PARSES every static-family surface's
``.ui`` via ElementTree and recomputes its status, crediting
``rewritten-material`` only where the surface satisfies its FULL family predicate
(the dialog/message/surface-body/popover markers), and leaving it ``pending``
otherwise -- conservative, no partial credit. Composition families (menu,
sidebar-panel, native-shell) keep their contract-cross-reference status
untouched. The credit is earned and reproducible: re-running ``--evaluate`` from
a clean checkout re-derives the same markers and the same pass/fail from the
tree. The default mode validates and prints the headline coverage number.
Validation runs seven fail-closed checks: C1 closure parity + digest, C2
attribution parity, C3 no status regression (baseline = the committed file), C4
anatomy-marker persistence, C5 evidence completeness, C6 classifier parity, C7
coverage parity.

This is source-level evidence only: ``runtime_verified`` is false everywhere and
no native build, dialog pixel, or runtime interaction is claimed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
CLOSURE_MODULE_PATH = REPOSITORY / "bin/check-windows-ui-registry-closure.py"
DEFAULT_LEDGER = REPOSITORY / "qa/windows-ui-contract/material-rewrite-ledger.json"

SCHEMA_VERSION = 1
CONTRACT = "windows-material-rewrite-ledger"
PLATFORM = "windows"
GENERATOR = "bin/check-material-rewrite-ledger.py"
CLOSURE_REGISTRY = "qa/windows-ui-contract/ui-registry.json"
CLOSURE_GENERATOR = "bin/check-windows-ui-registry-closure.py"
DESIGN_ARCHIVE_SHA = "0b79406d"

SOURCE_NOTE = (
    "Source-level burn-down ledger of the Material rewrite program, derived 1:1 "
    "from WIN-SYS-016. Regenerate with --regenerate. Not a claim of native "
    "build or runtime evidence."
)

PENDING = "pending"
IN_PROGRESS = "in-progress"
REWRITTEN = "rewritten-material"
STATUS_VALUES = (PENDING, IN_PROGRESS, REWRITTEN)
STATUS_ORDINAL = {PENDING: 0, IN_PROGRESS: 1, REWRITTEN: 2}

# Capture batch stamped on a surface credited PURELY by static .ui evaluation
# (``--evaluate``). No runtime pixel capture is claimed for these -- honesty bar
# consistent with the source_note ("no dialog pixel ... is claimed"). The
# ``captured`` flag is therefore false and ``scene`` is null; the batch name is
# the sole non-empty capture field, which is what the C5 evidence shape needs.
STATIC_EVAL_BATCH = "static-anatomy-evaluation"

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

# --- GTK response codes (mirrors bin/check-material-dialog-anatomy.py) ------
RET_OK = -5
RET_CANCEL = -6
RET_CLOSE = -7
RET_YES = -8
RET_NO = -9
RET_HELP = -11
PRIMARY_RESPONSES = frozenset({RET_OK, RET_YES})
SECONDARY_RESPONSES = frozenset({RET_CANCEL, RET_CLOSE, RET_NO})
# Labels that are not verbs: a destructive/action primary must never degrade to one.
NON_VERB_LABELS = frozenset(
    {"ok", "yes", "no", "cancel", "close", "apply", "help", "retry"}
)
DESTRUCTIVE_CLASS = "destructive-action"

# --- Family taxonomy -------------------------------------------------------
FAMILY_DIALOG = "dialog"
FAMILY_MESSAGE = "message-dialog"
FAMILY_OPTIONS = "options-page"
FAMILY_PANEL = "panel-fragment"
FAMILY_MENU = "menu"
FAMILY_POPOVER = "popover"
FAMILY_SIDEBAR = "sidebar-panel"
FAMILY_WIZARD = "wizard-assistant"
FAMILY_NATIVE = "native-shell"

ALL_FAMILIES = (
    FAMILY_DIALOG,
    FAMILY_MESSAGE,
    FAMILY_OPTIONS,
    FAMILY_PANEL,
    FAMILY_MENU,
    FAMILY_POPOVER,
    FAMILY_SIDEBAR,
    FAMILY_WIZARD,
    FAMILY_NATIVE,
)

RC_DIALOG_ANATOMY = "dialog-anatomy"
RC_SURFACE_BODY = "surface-body"
RC_POPOVER_ANATOMY = "popover-anatomy"
RC_MENU_COMPOSITION = "menu-composition"
RC_PANEL_COMPOSITION = "panel-composition"
RC_SHELL_COMPOSITION = "shell-composition"

STATIC_UI = "static-ui"
COMPOSITION_CODE = "composition-code"

# family -> (rewrite_class, evidence_kind, design_ref, required_markers)
FAMILY_DEFS: Mapping[str, dict[str, Any]] = {
    FAMILY_DIALOG: {
        "rewrite_class": RC_DIALOG_ANATOMY,
        "evidence_kind": STATIC_UI,
        "design_ref": "docs/design/08-dialogs.md#8.1",
        "required_markers": [
            "action-order-help-secondary-primary",
            "primary-can-default-bound",
            "material-footer-spacing",
            "material-content-grid",
            "ellipsize-and-mnemonic",
            "title-modal",
        ],
    },
    FAMILY_MESSAGE: {
        "rewrite_class": RC_DIALOG_ANATOMY,
        "evidence_kind": STATIC_UI,
        "design_ref": "docs/design/08-dialogs.md#8.1",
        "required_markers": [
            "action-order-help-safe-primary",
            "title-modal",
            "destructive-class-and-verb-when-destructive",
            "safe-is-enter-default-when-destructive",
        ],
    },
    FAMILY_OPTIONS: {
        "rewrite_class": RC_SURFACE_BODY,
        "evidence_kind": STATIC_UI,
        "design_ref": "docs/design/08-dialogs.md#8.2",
        "required_markers": [
            "material-content-grid",
            "ellipsize-and-mnemonic",
            "no-own-action-widgets",
        ],
    },
    FAMILY_PANEL: {
        "rewrite_class": RC_SURFACE_BODY,
        "evidence_kind": STATIC_UI,
        "design_ref": "docs/design/06-panels.md#6.7",
        "required_markers": [
            "material-content-grid",
            "ellipsize-and-mnemonic",
            "no-own-action-widgets",
        ],
    },
    FAMILY_MENU: {
        # Menus carry no static Material fingerprint the rewrite introduces: the
        # theme owns their rendering (radius, elevation, item padding), and the
        # only .ui edits the rewrite makes are structural (separators / item
        # order). A byte-identical-to-stock menu must NOT be auto-credited on
        # pre-existing .uno: action-names, so the family is a COMPOSITION-style
        # family routed to the menu-composition contract exactly like
        # sidebar-panel -- static --evaluate never credits it (0 via static
        # parse); a genuine credit rides the contract cross-reference.
        "rewrite_class": RC_MENU_COMPOSITION,
        "evidence_kind": COMPOSITION_CODE,
        "design_ref": "docs/design/05-navigation.md",
        "required_markers": ["composition-contract-marker"],
    },
    FAMILY_POPOVER: {
        # A popover is rewritten-material ONLY when it statically shows real
        # Material container anatomy (the content container declares spacing AND
        # margins) AND has dropped the legacy chrome (no border-width override
        # anywhere -- that override is exactly the stock padding the rewrite
        # removes so the theme owns the radius). A decorative icon-name earns
        # nothing on its own.
        "rewrite_class": RC_POPOVER_ANATOMY,
        "evidence_kind": STATIC_UI,
        "design_ref": "docs/design/05-navigation.md",
        "required_markers": [
            "material-container-spacing",
            "material-container-margins",
            "no-legacy-border-width",
        ],
    },
    FAMILY_SIDEBAR: {
        "rewrite_class": RC_PANEL_COMPOSITION,
        "evidence_kind": COMPOSITION_CODE,
        "design_ref": "docs/design/06-panels.md#6.7",
        "required_markers": ["composition-contract-marker"],
    },
    FAMILY_WIZARD: {
        "rewrite_class": RC_DIALOG_ANATOMY,
        "evidence_kind": STATIC_UI,
        "design_ref": "docs/design/08-dialogs.md#8.2",
        "required_markers": [
            "wizard-forward-primary",
            "material-content-grid",
            "title-modal",
        ],
    },
    FAMILY_NATIVE: {
        "rewrite_class": RC_SHELL_COMPOSITION,
        "evidence_kind": COMPOSITION_CODE,
        "design_ref": "docs/design/09-start-center.md",
        "required_markers": ["composition-contract-marker"],
    },
}

# non-.ui command-surface config layer (kept OUT of surfaces[] parity)
COMMAND_SURFACE_CONFIG = {
    "note": (
        "Non-.ui command-surface XML (toolbar / popupmenu / menubar / statusbar "
        "under */uiconfig/) is carried here by cross-reference so 'no surface "
        "exempt' holds without polluting the strict 1:1 closure-parity check on "
        "surfaces[]."
    ),
    "cross_referenced_contracts": [
        "notebookbar-composition.json",
        "menu-composition.json",
        "statusbar-composition.json",
        "command-overflow.json",
    ],
    "counts": {"toolbar": 419, "popupmenu": 193, "menubar": 21, "statusbar": 13},
    "status": "cross-referenced-not-enumerated",
}

OPT_PAGE_RE = re.compile(r"^opt.*page\.ui$")
MENU_TOPLEVEL_CLASSES = frozenset({"GtkMenu", "GtkPopoverMenu"})

# Per-wave soft budget: how many surfaces of a family may flip to
# rewritten-material in one ~3h CI wave before the capture harness is warned.
# Exceeding a cap is a loud stderr WARN, never a fail-closed error, so batches
# stay verifiable without blocking honest progress.
FAMILY_BATCH_CAP = {
    FAMILY_DIALOG: 24,
    FAMILY_PANEL: 24,
    FAMILY_MESSAGE: 16,
    FAMILY_MENU: 30,
    FAMILY_POPOVER: 20,
    FAMILY_OPTIONS: 12,
    FAMILY_SIDEBAR: 8,
    FAMILY_WIZARD: 1,
    FAMILY_NATIVE: 2,
}


class ValidationError(RuntimeError):
    """Raised when the Material-rewrite ledger is invalid."""


# --------------------------------------------------------------------------
# Closure module import (single source of truth for the surface universe)
# --------------------------------------------------------------------------
_CLOSURE_MODULE_NAME = "_material_rewrite_ledger_closure"


def load_closure_module():
    """Import ``build_registry`` from the closure checker.

    Registers the module in ``sys.modules`` BEFORE ``exec_module`` -- the
    hyphenated-filename module cannot be imported normally, and skipping the
    pre-registration is the classic ``exec_module`` pitfall for modules that
    reference their own name.
    """

    existing = sys.modules.get(_CLOSURE_MODULE_NAME)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(
        _CLOSURE_MODULE_NAME, CLOSURE_MODULE_PATH
    )
    if spec is None or spec.loader is None:
        raise ValidationError(
            f"cannot load closure module from {CLOSURE_MODULE_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[_CLOSURE_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def fresh_closure(repo_root: Path) -> tuple[dict[str, Any], str, dict[str, tuple[str, str]]]:
    """Return (registry, digest, attribution) from a fresh closure enumeration."""

    closure = load_closure_module()
    registry = closure.build_registry(repo_root)
    digest = "sha256:" + hashlib.sha256(
        closure.serialize_registry(registry).encode("utf-8")
    ).hexdigest()
    attribution: dict[str, tuple[str, str]] = {}
    for entry in list(registry.get("surfaces", [])) + list(
        registry.get("native_surfaces", [])
    ):
        attribution[entry["surface"]] = (entry["owner"], entry["inventory_id"])
    return registry, digest, attribution


# --------------------------------------------------------------------------
# XML helpers
# --------------------------------------------------------------------------
def _tag(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _toplevel_objects(root: ET.Element) -> list[ET.Element]:
    return [child for child in root if _tag(child.tag) == "object"]


def _direct_properties(obj: ET.Element) -> dict[str, str]:
    props: dict[str, str] = {}
    for child in obj:
        if _tag(child.tag) == "property" and child.get("name"):
            props[child.get("name")] = (child.text or "").strip()
    return props


def _style_classes(obj: ET.Element) -> set[str]:
    classes: set[str] = set()
    for child in obj:
        if _tag(child.tag) != "style":
            continue
        for cls in child:
            if _tag(cls.tag) == "class" and cls.get("name"):
                classes.add(cls.get("name"))
    return classes


def _clean_label(raw: str) -> str:
    return raw.replace("_", "").replace("&", "").replace("~", "").strip().strip("._ ").lower()


def _parse_root(repo_root: Path, surface: str) -> ET.Element:
    path = repo_root / surface
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise ValidationError(f"cannot parse .ui surface {surface}: {error}") from error


# --------------------------------------------------------------------------
# Classifier
# --------------------------------------------------------------------------
def classify(surface: str, root: ET.Element | None) -> str:
    """Return the family for a surface (root is None for native surfaces)."""

    if surface.startswith("native:"):
        return FAMILY_NATIVE
    assert root is not None
    objs = _toplevel_objects(root)
    classes = [obj.get("class") for obj in objs]
    has_action_widgets = any(
        _tag(node.tag) == "action-widgets" for obj in objs for node in obj.iter()
    )
    base = PurePosixName(surface)

    if "GtkMessageDialog" in classes:
        return FAMILY_MESSAGE
    if "GtkAssistant" in classes:
        return FAMILY_WIZARD
    if OPT_PAGE_RE.match(base):
        return FAMILY_OPTIONS
    if "GtkDialog" in classes or has_action_widgets:
        return FAMILY_DIALOG
    if classes and all(cls in MENU_TOPLEVEL_CLASSES for cls in classes):
        return FAMILY_MENU
    if "GtkPopover" in classes:
        return FAMILY_POPOVER
    if "sidebar" in base or base.endswith("panel.ui"):
        return FAMILY_SIDEBAR
    return FAMILY_PANEL


def PurePosixName(surface: str) -> str:
    return surface.rsplit("/", 1)[-1]


def rewrite_class_for(family: str) -> str:
    return FAMILY_DEFS[family]["rewrite_class"]


def evidence_kind_for(family: str) -> str:
    return FAMILY_DEFS[family]["evidence_kind"]


# --------------------------------------------------------------------------
# Static marker derivation
# --------------------------------------------------------------------------
def _find_dialog_object(root: ET.Element) -> ET.Element | None:
    for obj in _toplevel_objects(root):
        if obj.get("class") in ("GtkDialog", "GtkMessageDialog", "GtkAssistant"):
            return obj
    return None


def _action_widgets(dialog: ET.Element) -> list[tuple[str, int | None]]:
    out: list[tuple[str, int | None]] = []
    for node in dialog.iter():
        if _tag(node.tag) != "action-widgets":
            continue
        for aw in node:
            if _tag(aw.tag) != "action-widget":
                continue
            ident = (aw.text or "").strip()
            raw = aw.get("response", "")
            try:
                response: int | None = int(raw)
            except (TypeError, ValueError):
                response = None
            out.append((ident, response))
    return out


def _button_index(dialog: ET.Element) -> dict[str, ET.Element]:
    index: dict[str, ET.Element] = {}
    for obj in dialog.iter():
        if _tag(obj.tag) == "object" and obj.get("class") == "GtkButton" and obj.get("id"):
            index.setdefault(obj.get("id"), obj)
    return index


def _button_label(button: ET.Element) -> str:
    return _direct_properties(button).get("label", "")


def _content_grid_material(dialog: ET.Element) -> bool:
    for obj in dialog.iter():
        if _tag(obj.tag) != "object" or obj.get("class") != "GtkGrid":
            continue
        props = _direct_properties(obj)
        has_spacing = "row-spacing" in props or "column-spacing" in props
        has_margin = any(
            key in props
            for key in ("margin-start", "margin-end", "margin-top", "margin-bottom")
        )
        if has_spacing and has_margin:
            return True
    return False


def _count_ellipsize(dialog: ET.Element) -> int:
    count = 0
    for obj in dialog.iter():
        if _tag(obj.tag) == "object" and obj.get("class") == "GtkLabel":
            if _direct_properties(obj).get("ellipsize", "").lower() == "end":
                count += 1
    return count


def _count_mnemonic_labels(dialog: ET.Element) -> int:
    count = 0
    for obj in dialog.iter():
        if _tag(obj.tag) == "object" and obj.get("class") == "GtkLabel":
            if "mnemonic-widget" in _direct_properties(obj):
                count += 1
    return count


def _footer_spacing(dialog: ET.Element) -> int | None:
    for obj in dialog.iter():
        if _tag(obj.tag) == "object" and obj.get("class") == "GtkButtonBox":
            raw = _direct_properties(obj).get("spacing")
            if raw is None:
                continue
            try:
                return int(raw)
            except ValueError:
                return None
    return None


def _to_bool(raw: str) -> bool:
    return raw.strip().lower() in ("true", "1", "yes")


def derive_dialog_markers(root: ET.Element) -> dict[str, Any]:
    """Derive the dialog-anatomy marker snapshot for a dialog/message/wizard .ui."""

    dialog = _find_dialog_object(root)
    if dialog is None:
        raise ValidationError("no GtkDialog/GtkMessageDialog/GtkAssistant toplevel found")
    dprops = _direct_properties(dialog)
    is_message = dialog.get("class") == "GtkMessageDialog"

    action = _action_widgets(dialog)
    order = [resp for _ident, resp in action]
    buttons = _button_index(dialog)

    primary_id = action[-1][0] if action else None
    primary_response = action[-1][1] if action else None
    primary_button = buttons.get(primary_id) if primary_id else None
    primary_label = _clean_label(_button_label(primary_button)) if primary_button is not None else ""
    primary_is_verb = bool(primary_label) and primary_label not in NON_VERB_LABELS
    primary_can_default = False
    if primary_button is not None:
        pprops = _direct_properties(primary_button)
        primary_can_default = _to_bool(pprops.get("can-default", "")) or _to_bool(
            pprops.get("has-default", "")
        )
    destructive_class = (
        primary_button is not None and DESTRUCTIVE_CLASS in _style_classes(primary_button)
    )

    default_id: str | None = None
    default_response: int | None = None
    for ident, resp in action:
        button = buttons.get(ident)
        if button is not None and _to_bool(_direct_properties(button).get("has-default", "")):
            default_id = ident
            default_response = resp
            break

    help_first = (RET_HELP in order) and (order[0] == RET_HELP if order else False)
    has_border = False
    try:
        has_border = int(dprops.get("border-width", "0")) > 0
    except ValueError:
        has_border = False

    return {
        "is_message_dialog": is_message,
        "message_type": dprops.get("message-type") or None,
        "action_order": order,
        "help_first": help_first,
        "primary_id": primary_id,
        "primary_response": primary_response,
        "primary_label": primary_label,
        "primary_is_verb": primary_is_verb,
        "primary_can_default": primary_can_default,
        "default_id": default_id,
        "default_response": default_response,
        "destructive_class": destructive_class,
        "footer_spacing": _footer_spacing(dialog),
        "content_grid_material": _content_grid_material(dialog),
        "ellipsize_count": _count_ellipsize(dialog),
        "mnemonic_content_labels": _count_mnemonic_labels(dialog),
        "has_legacy_border": has_border,
        "title_present": bool(dprops.get("title")),
        "modal": _to_bool(dprops.get("modal", "")),
    }


def derive_surface_body_markers(root: ET.Element) -> dict[str, Any]:
    objs = _toplevel_objects(root)
    has_action_widgets = any(
        _tag(node.tag) == "action-widgets" for obj in objs for node in obj.iter()
    )
    return {
        "content_grid_material": _content_grid_material(root),
        "ellipsize_count": _count_ellipsize(root),
        "mnemonic_content_labels": _count_mnemonic_labels(root),
        "has_own_action_widgets": has_action_widgets,
    }


def _find_popover_object(root: ET.Element) -> ET.Element | None:
    """Return the popover toplevel (or the first nested GtkPopover)."""

    for obj in _toplevel_objects(root):
        if obj.get("class") == "GtkPopover":
            return obj
    for obj in root.iter():
        if _tag(obj.tag) == "object" and obj.get("class") == "GtkPopover":
            return obj
    return None


def _first_child_object(obj: ET.Element) -> ET.Element | None:
    """Return the first ``<child><object>`` under ``obj`` (its content container)."""

    for child in obj:
        if _tag(child.tag) != "child":
            continue
        for grandchild in child:
            if _tag(grandchild.tag) == "object":
                return grandchild
    return None


def _has_legacy_border_anywhere(root: ET.Element) -> bool:
    """True if any object declares a positive ``border-width`` override.

    ``border-width`` is the stock GTK chrome the Material rewrite removes so the
    theme owns the popover radius/padding; its presence anywhere in the file is
    proof the surface still carries legacy chrome and is not yet Material.
    """

    for node in root.iter():
        if _tag(node.tag) == "property" and node.get("name") == "border-width":
            raw = (node.text or "").strip()
            try:
                if int(raw) > 0:
                    return True
            except ValueError:
                # a non-integer border-width override is still legacy chrome
                return True
    return False


def derive_popover_markers(root: ET.Element) -> dict[str, Any]:
    """Derive the Material container-anatomy snapshot for a popover ``.ui``.

    The rewrite gives a popover's content container explicit Material spacing and
    margins and drops the legacy ``border-width`` override. A decorative
    ``icon-name`` on a child is deliberately NOT a marker here -- it exists on
    stock popovers untouched by the rewrite, so it can never earn credit alone.
    """

    popover = _find_popover_object(root)
    container = _first_child_object(popover) if popover is not None else None
    cprops = _direct_properties(container) if container is not None else {}
    has_spacing = any(
        key in cprops for key in ("spacing", "row-spacing", "column-spacing")
    )
    has_margin = any(
        key in cprops
        for key in ("margin-start", "margin-end", "margin-top", "margin-bottom", "margin")
    )
    return {
        "popover_present": popover is not None,
        "container_class": container.get("class") if container is not None else None,
        "container_has_spacing": has_spacing,
        "container_has_margin": has_margin,
        "has_legacy_border": _has_legacy_border_anywhere(root),
    }


def derive_static_markers(family: str, root: ET.Element) -> dict[str, Any]:
    if family in (FAMILY_DIALOG, FAMILY_MESSAGE, FAMILY_WIZARD):
        return derive_dialog_markers(root)
    if family in (FAMILY_OPTIONS, FAMILY_PANEL):
        return derive_surface_body_markers(root)
    if family == FAMILY_POPOVER:
        return derive_popover_markers(root)
    # FAMILY_MENU is a composition-cross-referenced family (evidence_kind
    # COMPOSITION_CODE) and is never statically derived here.
    raise ValidationError(f"family {family!r} has no static marker derivation")


# --------------------------------------------------------------------------
# Acceptance predicates
# --------------------------------------------------------------------------
def _footer_anatomy_ok(markers: Mapping[str, Any]) -> tuple[bool, str]:
    order = markers.get("action_order") or []
    if not order:
        return False, "no action-widgets footer"
    if order[-1] not in PRIMARY_RESPONSES:
        return False, f"primary response {order[-1]} not in {sorted(PRIMARY_RESPONSES)}"
    body = list(order)
    if body and body[0] == RET_HELP:
        body = body[1:]
    elif RET_HELP in body:
        return False, "help present but not first"
    body = body[:-1]  # drop the primary
    for resp in body:
        if resp not in SECONDARY_RESPONSES:
            return False, f"secondary response {resp} not in {sorted(SECONDARY_RESPONSES)}"
    return True, ""


def _is_destructive_variant(markers: Mapping[str, Any]) -> bool:
    return (
        (markers.get("message_type") in ("warning", "question"))
        and bool(markers.get("destructive_class"))
    )


def predicate_message_dialog(markers: Mapping[str, Any]) -> tuple[bool, str]:
    if not markers.get("is_message_dialog"):
        return False, "not a GtkMessageDialog"
    ok, why = _footer_anatomy_ok(markers)
    if not ok:
        return False, why
    if not markers.get("title_present"):
        return False, "no title"
    if not markers.get("modal"):
        return False, "not modal"
    if _is_destructive_variant(markers):
        if not markers.get("destructive_class"):
            return False, "destructive primary lacks destructive-action class"
        if not markers.get("primary_is_verb"):
            return False, "destructive primary label is not a verb"
        if markers.get("default_response") == markers.get("primary_response"):
            return False, "destructive action is the Enter default"
        if markers.get("default_response") not in SECONDARY_RESPONSES:
            return False, "safe action is not the Enter default"
    return True, ""


def predicate_dialog(markers: Mapping[str, Any]) -> tuple[bool, str]:
    if markers.get("is_message_dialog"):
        # a GtkMessageDialog classified as dialog would be a classifier bug
        return predicate_message_dialog(markers)
    ok, why = _footer_anatomy_ok(markers)
    if not ok:
        return False, why
    if not markers.get("primary_can_default"):
        return False, "primary button not can-default"
    if markers.get("default_response") != markers.get("primary_response"):
        return False, "Enter default not bound to the primary"
    spacing = markers.get("footer_spacing")
    if not (isinstance(spacing, int) and spacing >= 10):
        return False, "footer button box spacing < 10 (non-Material)"
    if not markers.get("content_grid_material"):
        return False, "content grid lacks Material spacing/margins"
    if markers.get("ellipsize_count", 0) < 1:
        return False, "no ellipsize=end label"
    if markers.get("mnemonic_content_labels", 0) < 1:
        return False, "no mnemonic-widget content label"
    if markers.get("has_legacy_border"):
        return False, "legacy border-width override fights the theme radius"
    if not markers.get("title_present"):
        return False, "no title"
    if not markers.get("modal"):
        return False, "not modal"
    return True, ""


def predicate_wizard(markers: Mapping[str, Any]) -> tuple[bool, str]:
    order = markers.get("action_order") or []
    if not order or order[-1] not in PRIMARY_RESPONSES:
        return False, "wizard forward action is not the primary"
    if not markers.get("content_grid_material"):
        return False, "wizard page content grid lacks Material spacing/margins"
    if not markers.get("title_present"):
        return False, "no title"
    return True, ""


def predicate_surface_body(markers: Mapping[str, Any]) -> tuple[bool, str]:
    if markers.get("has_own_action_widgets"):
        return False, "surface-body pane must not carry its own action-widgets footer"
    if not markers.get("content_grid_material"):
        return False, "content grid lacks Material spacing/margins"
    if markers.get("ellipsize_count", 0) < 1:
        return False, "no ellipsize=end label"
    if markers.get("mnemonic_content_labels", 0) < 1:
        return False, "no mnemonic-widget content label"
    return True, ""


def predicate_popover(markers: Mapping[str, Any]) -> tuple[bool, str]:
    """Accept a popover only with Material container anatomy AND no legacy chrome.

    Both prongs are required: a stock popover that keeps its ``border-width``
    padding fails the second prong, and a popover whose content container has no
    explicit spacing/margins fails the first. Neither a decorative ``icon-name``
    nor a pre-existing ``.uno:`` action can substitute for either -- that was the
    over-crediting hole (reusing ``predicate_menu``) this predicate closes.
    """

    if not markers.get("popover_present"):
        return False, "no GtkPopover toplevel"
    if markers.get("has_legacy_border"):
        return False, "legacy border-width override present (stock chrome the rewrite removes)"
    if markers.get("container_class") is None:
        return False, "popover has no content container"
    if not markers.get("container_has_spacing"):
        return False, "content container declares no Material spacing"
    if not markers.get("container_has_margin"):
        return False, "content container declares no Material margins"
    return True, ""


def static_predicate(family: str, markers: Mapping[str, Any]) -> tuple[bool, str]:
    if family == FAMILY_MESSAGE:
        return predicate_message_dialog(markers)
    if family == FAMILY_DIALOG:
        return predicate_dialog(markers)
    if family == FAMILY_WIZARD:
        return predicate_wizard(markers)
    if family in (FAMILY_OPTIONS, FAMILY_PANEL):
        return predicate_surface_body(markers)
    if family == FAMILY_POPOVER:
        return predicate_popover(markers)
    # FAMILY_MENU rides the menu-composition contract, not a static predicate.
    return False, f"family {family!r} has no static predicate"


# --------------------------------------------------------------------------
# Ledger assembly (--regenerate)
# --------------------------------------------------------------------------
def _null_evidence() -> dict[str, Any]:
    return {"commit": None, "contract": None, "capture": None, "anatomy_markers": {}}


def _root_cache(repo_root: Path) -> dict[str, ET.Element]:
    return {}


def _classify_surface(repo_root: Path, surface: str, cache: dict[str, ET.Element]) -> str:
    if surface.startswith("native:"):
        return FAMILY_NATIVE
    root = cache.get(surface)
    if root is None:
        root = _parse_root(repo_root, surface)
        cache[surface] = root
    return classify(surface, root)


def _head_commit(repo_root: Path) -> str | None:
    """Return the 40-hex HEAD commit, or None when it cannot be resolved."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    out = completed.stdout.decode("utf-8", errors="replace").strip()
    return out if COMMIT_RE.match(out) else None


def _static_capture() -> dict[str, Any]:
    return {"scene": None, "sample_batch": STATIC_EVAL_BATCH, "captured": False}


def build_static_evidence(
    family: str, head_commit: str | None, markers: Mapping[str, Any]
) -> dict[str, Any]:
    """Assemble the evidence block for a surface newly credited by --evaluate.

    The ``contract`` field points at the family's design-spec section (the
    anatomy the surface was statically evaluated against), the ``capture`` block
    honestly records that no runtime pixel was taken, and ``anatomy_markers`` is
    the freshly derived snapshot -- which C4 later re-derives and requires to
    still match byte-for-byte.
    """

    if not (isinstance(head_commit, str) and COMMIT_RE.match(head_commit)):
        raise ValidationError(
            "--evaluate needs a 40-hex HEAD commit to stamp a new rewritten flip; "
            "none could be resolved (run inside a Git checkout)"
        )
    return {
        "commit": head_commit,
        "contract": FAMILY_DEFS[family]["design_ref"],
        "capture": _static_capture(),
        "anatomy_markers": json.loads(json.dumps(markers)),
    }


def evaluate_surface_status(
    repo_root: Path,
    surface: str,
    family: str,
    cache: dict[str, ET.Element],
    prior_status: str,
    prior_evidence: Mapping[str, Any],
    head_commit: str | None,
) -> tuple[str, dict[str, Any]]:
    """Recompute a surface's status from the LIVE .ui tree (``--evaluate``).

    * Composition families (sidebar-panel, native-shell) keep the existing
      contract-cross-reference path: their status/evidence is campaign-owned and
      is never recomputed statically -- returned verbatim.
    * Static families are credited ``rewritten-material`` iff ALL of the family
      predicate's markers pass; otherwise the surface stays ``pending``. There is
      no partial credit: a some-but-not-all surface is ``pending``.
    * Fail-closed no-regression: a status already at or above the evaluated one
      is never dropped. A surface that was ``rewritten-material`` but no longer
      satisfies its predicate keeps that status here so the honest place to fail
      is C4 anatomy persistence, not a silent downgrade.
    * A still-passing surface that was already ``rewritten-material`` keeps its
      richer prior evidence (e.g. a real pixel capture) verbatim rather than
      being overwritten with the static-evaluation stub.
    """

    prior_evidence = json.loads(json.dumps(prior_evidence))
    if evidence_kind_for(family) == COMPOSITION_CODE:
        return prior_status, prior_evidence

    root = cache.get(surface)
    if root is None:
        root = _parse_root(repo_root, surface)
        cache[surface] = root
    try:
        markers = derive_static_markers(family, root)
        passed, _why = static_predicate(family, markers)
    except ValidationError:
        passed = False
        markers = None

    if passed:
        assert markers is not None
        if prior_status == REWRITTEN and prior_evidence.get("commit"):
            return REWRITTEN, prior_evidence
        return REWRITTEN, build_static_evidence(family, head_commit, markers)

    if STATUS_ORDINAL.get(prior_status, 0) > STATUS_ORDINAL[PENDING]:
        return prior_status, prior_evidence
    return PENDING, _null_evidence()


def build_ledger(
    repo_root: Path,
    existing: Mapping[str, Any] | None,
    *,
    allow_status_loss: bool = False,
    rename_map: Mapping[str, str] | None = None,
    evaluate: bool = False,
) -> dict[str, Any]:
    """Enumerate fresh from the closure and (re)build the ledger deterministically.

    ``evaluate=False`` (plain --regenerate) re-syncs structure only and preserves
    each surface's campaign ``rewrite_status``/``rewrite_evidence`` verbatim.
    ``evaluate=True`` (--evaluate) additionally RECOMPUTES the status of every
    static family from the live .ui tree via ``evaluate_surface_status`` --
    crediting ``rewritten-material`` only where the full family predicate passes.
    Composition families are never statically recomputed either way.
    """

    repo_root = repo_root.resolve()
    registry, digest, attribution = fresh_closure(repo_root)
    rename_map = dict(rename_map or {})
    rename_target_of = {new: old for old, new in rename_map.items()}
    head_commit = _head_commit(repo_root) if evaluate else None

    prior_rows: dict[str, Mapping[str, Any]] = {}
    if existing is not None:
        for row in existing.get("surfaces", []):
            if isinstance(row, Mapping) and isinstance(row.get("surface"), str):
                prior_rows[row["surface"]] = row

    # Refuse to silently drop campaign progress: a prior in-progress/rewritten
    # row whose surface vanished from the closure must be re-homed with
    # --rename-map OLD=NEW or explicitly discarded with --allow-status-loss.
    fresh_set = set(attribution)
    lost: list[str] = []
    for old_surface, prior in prior_rows.items():
        status = prior.get("rewrite_status")
        if status in (IN_PROGRESS, REWRITTEN) and old_surface not in fresh_set:
            renamed = rename_map.get(old_surface)
            if renamed and renamed in fresh_set:
                continue
            if not allow_status_loss:
                lost.append(f"{old_surface} ({status})")
    if lost:
        raise ValidationError(
            "--regenerate would drop non-pending campaign progress for: "
            + "; ".join(sorted(lost))
            + " (supply --rename-map OLD=NEW to carry it forward, or "
            "--allow-status-loss to discard it)"
        )

    cache = _root_cache(repo_root)
    surfaces: list[dict[str, Any]] = []
    for surface, (owner, inventory_id) in sorted(attribution.items()):
        family = _classify_surface(repo_root, surface, cache)
        prior = prior_rows.get(surface)
        if prior is None and surface in rename_target_of:
            prior = prior_rows.get(rename_target_of[surface])
        prior_status = PENDING
        prior_evidence: dict[str, Any] = _null_evidence()
        if prior is not None:
            candidate = prior.get("rewrite_status")
            if candidate in STATUS_VALUES:
                prior_status = candidate
            candidate_evidence = prior.get("rewrite_evidence")
            if isinstance(candidate_evidence, Mapping):
                prior_evidence = json.loads(json.dumps(candidate_evidence))
        if evaluate:
            status, evidence = evaluate_surface_status(
                repo_root,
                surface,
                family,
                cache,
                prior_status,
                prior_evidence,
                head_commit,
            )
        else:
            status, evidence = prior_status, prior_evidence
        surfaces.append(
            {
                "surface": surface,
                "owner": owner,
                "inventory_id": inventory_id,
                "family": family,
                "rewrite_class": rewrite_class_for(family),
                "rewrite_status": status,
                "rewrite_evidence": evidence,
            }
        )

    coverage = compute_coverage(surfaces)
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "platform": PLATFORM,
        "generator": GENERATOR,
        "closure_registry": CLOSURE_REGISTRY,
        "closure_generator": CLOSURE_GENERATOR,
        "closure_registry_digest": digest,
        "design_archive_sha": DESIGN_ARCHIVE_SHA,
        "source_note": SOURCE_NOTE,
        "rewrite_status_values": list(STATUS_VALUES),
        "family_defs": {family: FAMILY_DEFS[family] for family in ALL_FAMILIES},
        "coverage": coverage,
        "command_surface_config": COMMAND_SURFACE_CONFIG,
        "surfaces": surfaces,
    }
    return ledger


def compute_coverage(surfaces: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(surfaces)
    tally = {PENDING: 0, IN_PROGRESS: 0, REWRITTEN: 0}

    def bucket() -> dict[str, int]:
        return {"total": 0, PENDING: 0, IN_PROGRESS: 0, REWRITTEN: 0}

    by_family: dict[str, dict[str, int]] = {}
    by_owner: dict[str, dict[str, int]] = {}
    by_inventory: dict[str, dict[str, int]] = {}
    for row in surfaces:
        status = row["rewrite_status"]
        tally[status] = tally.get(status, 0) + 1
        for key, table in (
            (row["family"], by_family),
            (row["owner"], by_owner),
            (row["inventory_id"], by_inventory),
        ):
            entry = table.setdefault(key, bucket())
            entry["total"] += 1
            entry[status] += 1
    rewritten = tally[REWRITTEN]
    coverage_pct = round(rewritten / total * 100, 2) if total else 0.0
    return {
        "total_surfaces": total,
        "pending": tally[PENDING],
        "in_progress": tally[IN_PROGRESS],
        "rewritten_material": rewritten,
        "coverage_pct": coverage_pct,
        "by_family": {key: by_family[key] for key in sorted(by_family)},
        "by_owner": {key: by_owner[key] for key in sorted(by_owner)},
        "by_inventory_id": {key: by_inventory[key] for key in sorted(by_inventory)},
    }


# --------------------------------------------------------------------------
# File I/O
# --------------------------------------------------------------------------
def serialize_ledger(ledger: Mapping[str, Any]) -> str:
    return json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"


def write_ledger(ledger_path: Path, ledger: Mapping[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(serialize_ledger(ledger))


def read_ledger(ledger_path: Path) -> dict[str, Any]:
    try:
        text = ledger_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValidationError(f"cannot read ledger {ledger_path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValidationError(f"ledger {ledger_path} is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise ValidationError(f"ledger {ledger_path} must be a JSON object")
    return data


def load_committed_baseline(repo_root: Path, ledger_path: Path) -> dict[str, Any] | None:
    """Return the committed (HEAD) ledger, or None on the first commit.

    C3 uses the committed file as the prior campaign state; a missing baseline
    (first commit) means every surface's baseline status is treated as pending.
    """

    try:
        rel = ledger_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        rel = ledger_path.name
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"HEAD:{rel}"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    try:
        data = json.loads(completed.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# --------------------------------------------------------------------------
# Validation (C1..C7)
# --------------------------------------------------------------------------
def _format_keys(keys, limit: int = 12) -> str:
    values = sorted(keys)
    shown = values[:limit]
    suffix = "" if len(values) <= limit else f"; ... and {len(values) - limit} more"
    return "; ".join(shown) + suffix


def _ledger_rows(ledger: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = ledger.get("surfaces")
    if not isinstance(rows, list):
        raise ValidationError("ledger surfaces section must be a list")
    index: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or "surface" not in row:
            raise ValidationError("ledger surface row is malformed")
        key = row["surface"]
        if not isinstance(key, str):
            raise ValidationError("ledger surface key must be a string")
        if key in index:
            raise ValidationError(f"duplicate surface row in ledger: {key}")
        index[key] = row
    return index


def _validate_meta(ledger: Mapping[str, Any], digest: str, failures: list[str]) -> None:
    checks = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT,
        "platform": PLATFORM,
        "generator": GENERATOR,
        "closure_registry": CLOSURE_REGISTRY,
        "closure_generator": CLOSURE_GENERATOR,
        "closure_registry_digest": digest,
    }
    for field, want in checks.items():
        if ledger.get(field) != want:
            failures.append(
                f"C1 meta field {field!r} drifted: expected {want!r}, "
                f"found {ledger.get(field)!r}"
                + (" -- run --regenerate" if field == "closure_registry_digest" else "")
            )


def _validate_closure_parity(
    rows: Mapping[str, Mapping[str, Any]],
    attribution: Mapping[str, tuple[str, str]],
    failures: list[str],
) -> None:
    ledger_set = set(rows)
    fresh_set = set(attribution)
    missing = fresh_set - ledger_set
    extra = ledger_set - fresh_set
    if missing:
        failures.append(
            f"C1 ledger diverges from closure; run --regenerate: {len(missing)} "
            f"surface(s) missing from the ledger: {_format_keys(missing)}"
        )
    if extra:
        failures.append(
            f"C1 ledger diverges from closure; run --regenerate: {len(extra)} "
            f"ledger surface(s) not in the closure: {_format_keys(extra)}"
        )


def _validate_attribution(
    rows: Mapping[str, Mapping[str, Any]],
    attribution: Mapping[str, tuple[str, str]],
    failures: list[str],
) -> None:
    for surface in sorted(set(rows) & set(attribution)):
        owner, inventory_id = attribution[surface]
        row = rows[surface]
        if row.get("owner") != owner:
            failures.append(
                f"C2 attribution: {surface} owner {row.get('owner')!r} != closure "
                f"{owner!r}"
            )
        if row.get("inventory_id") != inventory_id:
            failures.append(
                f"C2 attribution: {surface} inventory_id {row.get('inventory_id')!r} "
                f"!= closure {inventory_id!r}"
            )


def _validate_classifier(
    repo_root: Path,
    rows: Mapping[str, Mapping[str, Any]],
    attribution: Mapping[str, tuple[str, str]],
    cache: dict[str, ET.Element],
    failures: list[str],
) -> None:
    for surface in sorted(set(rows) & set(attribution)):
        family = _classify_surface(repo_root, surface, cache)
        row = rows[surface]
        if row.get("family") != family:
            failures.append(
                f"C6 classifier: {surface} family {row.get('family')!r} != fresh "
                f"{family!r}"
            )
        expected_rc = rewrite_class_for(family)
        if row.get("rewrite_class") != expected_rc:
            failures.append(
                f"C6 classifier: {surface} rewrite_class {row.get('rewrite_class')!r} "
                f"!= {expected_rc!r}"
            )


def _validate_status_regression(
    rows: Mapping[str, Mapping[str, Any]],
    baseline: Mapping[str, Any] | None,
    failures: list[str],
    warnings: list[str],
) -> None:
    baseline_status: dict[str, str] = {}
    if baseline is not None:
        for row in baseline.get("surfaces", []):
            if isinstance(row, Mapping) and isinstance(row.get("surface"), str):
                status = row.get("rewrite_status")
                baseline_status[row["surface"]] = (
                    status if status in STATUS_VALUES else PENDING
                )
    for surface, row in rows.items():
        prior = baseline_status.get(surface, PENDING)
        now = row.get("rewrite_status")
        if now not in STATUS_VALUES:
            failures.append(f"C3 status: {surface} has invalid rewrite_status {now!r}")
            continue
        if STATUS_ORDINAL[now] < STATUS_ORDINAL[prior]:
            waiver = row.get("regression_waiver")
            if isinstance(waiver, Mapping) and waiver.get("reason") and waiver.get("commit"):
                warnings.append(
                    f"C3 WARN: {surface} regressed {prior} -> {now} under waiver "
                    f"({waiver.get('reason')})"
                )
            else:
                failures.append(
                    f"C3 status regression: {surface} regressed {prior} -> {now} "
                    "(no regression_waiver)"
                )


def _validate_evidence_shape(row: Mapping[str, Any], surface: str, failures: list[str]) -> None:
    status = row.get("rewrite_status")
    evidence = row.get("rewrite_evidence")
    if not isinstance(evidence, Mapping):
        failures.append(f"C5 evidence: {surface} rewrite_evidence must be an object")
        return
    commit = evidence.get("commit")
    contract = evidence.get("contract")
    capture = evidence.get("capture")
    markers = evidence.get("anatomy_markers")
    if status == PENDING:
        if commit is not None or contract is not None or capture is not None:
            failures.append(
                f"C5 evidence: pending {surface} must have null commit/contract/capture"
            )
        if markers:
            failures.append(
                f"C5 evidence: pending {surface} must have empty anatomy_markers"
            )
    elif status == IN_PROGRESS:
        if not (isinstance(commit, str) and COMMIT_RE.match(commit)):
            failures.append(
                f"C5 evidence: in-progress {surface} must set a 40-hex commit"
            )
    elif status == REWRITTEN:
        if not (isinstance(commit, str) and COMMIT_RE.match(commit)):
            failures.append(
                f"C5 evidence: rewritten {surface} must set a 40-hex commit"
            )
        if not isinstance(contract, str) or not contract:
            failures.append(
                f"C5 evidence: rewritten {surface} must name an owning contract"
            )
        if not isinstance(capture, Mapping) or not (
            capture.get("scene") or capture.get("sample_batch")
        ):
            failures.append(
                f"C5 evidence: rewritten {surface} capture needs scene or sample_batch"
            )
        if not isinstance(markers, Mapping) or not markers:
            failures.append(
                f"C5 evidence: rewritten {surface} anatomy_markers must be non-empty"
            )


def _validate_anatomy_persistence(
    repo_root: Path,
    rows: Mapping[str, Mapping[str, Any]],
    cache: dict[str, ET.Element],
    failures: list[str],
) -> None:
    for surface in sorted(rows):
        row = rows[surface]
        if row.get("rewrite_status") != REWRITTEN:
            continue
        family = row.get("family")
        if family not in FAMILY_DEFS:
            failures.append(f"C4 anatomy: {surface} has unknown family {family!r}")
            continue
        evidence = row.get("rewrite_evidence")
        if not isinstance(evidence, Mapping):
            continue  # C5 already flagged
        stored = evidence.get("anatomy_markers")
        kind = evidence_kind_for(family)
        if kind == STATIC_UI:
            try:
                root = cache.get(surface) or _parse_root(repo_root, surface)
                cache[surface] = root
                fresh = derive_static_markers(family, root)
            except ValidationError as error:
                failures.append(f"C4 anatomy: {surface} re-derivation failed: {error}")
                continue
            ok, why = static_predicate(family, fresh)
            if not ok:
                failures.append(
                    f"C4 anatomy: rewritten {surface} no longer satisfies the {family} "
                    f"predicate ({why})"
                )
            if stored != fresh:
                failures.append(
                    f"C4 anatomy: {surface} markers changed since flip "
                    "(stored snapshot != freshly derived)"
                )
        else:  # composition-code
            _validate_composition_marker(repo_root, surface, evidence, failures)


def _validate_composition_marker(
    repo_root: Path,
    surface: str,
    evidence: Mapping[str, Any],
    failures: list[str],
) -> None:
    contract_rel = evidence.get("contract")
    markers = evidence.get("anatomy_markers")
    if not isinstance(contract_rel, str) or not contract_rel:
        failures.append(f"C4 composition: {surface} names no owning contract")
        return
    contract_path = repo_root / contract_rel
    if not contract_path.is_file():
        failures.append(
            f"C4 composition: {surface} owning contract {contract_rel} does not exist"
        )
        return
    if not isinstance(markers, Mapping):
        failures.append(f"C4 composition: {surface} anatomy_markers must be an object")
        return
    token = markers.get("contract_marker")
    if not isinstance(token, str) or not token:
        failures.append(
            f"C4 composition: {surface} anatomy_markers.contract_marker missing"
        )
        return
    try:
        contract_data = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        failures.append(
            f"C4 composition: cannot read owning contract {contract_rel}: {error}"
        )
        return
    if not (isinstance(contract_data, Mapping) and contract_data.get("contract") == token):
        failures.append(
            f"C4 composition: marker {token!r} for {surface} vanished from "
            f"{contract_rel} (cross-reference broken)"
        )


def _validate_coverage(
    ledger: Mapping[str, Any],
    rows: Mapping[str, Mapping[str, Any]],
    failures: list[str],
) -> None:
    expected = compute_coverage(list(rows.values()))
    actual = ledger.get("coverage")
    if actual != expected:
        failures.append(
            "C7 coverage block does not match a fresh recompute; run --regenerate"
        )


def _validate_acceptance_table(ledger: Mapping[str, Any], failures: list[str]) -> None:
    """Reject hand-tampering of the machine-readable acceptance/config tables."""

    expected_defs = {family: FAMILY_DEFS[family] for family in ALL_FAMILIES}
    if ledger.get("family_defs") != expected_defs:
        failures.append(
            "family_defs acceptance table drifted from the checker source of "
            "truth; run --regenerate (a hand-edit must not relax a predicate)"
        )
    if ledger.get("rewrite_status_values") != list(STATUS_VALUES):
        failures.append("rewrite_status_values drifted; run --regenerate")
    if ledger.get("command_surface_config") != COMMAND_SURFACE_CONFIG:
        failures.append("command_surface_config drifted; run --regenerate")


def _warn_wave_budget(
    rows: Mapping[str, Mapping[str, Any]],
    baseline: Mapping[str, Any] | None,
    warnings: list[str],
) -> None:
    """Soft (WARN-only) per-wave budget guard on rewritten-material flips.

    Skipped on the first commit (no baseline) so the initial baseline seed is
    never flagged as an over-budget wave.
    """

    if baseline is None:
        return
    base_rewritten: dict[str, int] = {}
    for row in baseline.get("surfaces", []):
        if isinstance(row, Mapping) and row.get("rewrite_status") == REWRITTEN:
            base_rewritten[row.get("family")] = base_rewritten.get(row.get("family"), 0) + 1
    now_rewritten: dict[str, int] = {}
    for row in rows.values():
        if row.get("rewrite_status") == REWRITTEN:
            now_rewritten[row.get("family")] = now_rewritten.get(row.get("family"), 0) + 1
    for family, cap in FAMILY_BATCH_CAP.items():
        delta = now_rewritten.get(family, 0) - base_rewritten.get(family, 0)
        if delta > cap:
            warnings.append(
                f"WARN wave budget: {delta} {family} surfaces flipped to "
                f"rewritten-material this wave, exceeding the batchable cap {cap} "
                "(keep the capture batch verifiable)"
            )


def validate(repo_root: Path, ledger_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    ledger = read_ledger(ledger_path)
    _registry, digest, attribution = fresh_closure(repo_root)

    failures: list[str] = []
    warnings: list[str] = []

    rows = _ledger_rows(ledger)
    cache = _root_cache(repo_root)

    _validate_meta(ledger, digest, failures)
    _validate_closure_parity(rows, attribution, failures)
    _validate_attribution(rows, attribution, failures)
    _validate_classifier(repo_root, rows, attribution, cache, failures)

    baseline = load_committed_baseline(repo_root, ledger_path)
    _validate_status_regression(rows, baseline, failures, warnings)
    _warn_wave_budget(rows, baseline, warnings)

    for surface in sorted(rows):
        _validate_evidence_shape(rows[surface], surface, failures)

    _validate_anatomy_persistence(repo_root, rows, cache, failures)
    _validate_coverage(ledger, rows, failures)
    _validate_acceptance_table(ledger, failures)

    for warning in warnings:
        print(warning, file=sys.stderr)

    if failures:
        raise ValidationError("\n".join(failures))
    return ledger


# --------------------------------------------------------------------------
# Headline
# --------------------------------------------------------------------------
def headline_lines(ledger: Mapping[str, Any]) -> list[str]:
    coverage = ledger.get("coverage", {})
    total = coverage.get("total_surfaces", 0)
    rewritten = coverage.get("rewritten_material", 0)
    in_progress = coverage.get("in_progress", 0)
    pending = coverage.get("pending", 0)
    pct = coverage.get("coverage_pct", 0.0)
    lines = [
        f"Material rewrite burn-down: {pct}% rewritten-material "
        f"({rewritten}/{total}) | in-progress {in_progress} | pending {pending}"
    ]
    by_family = coverage.get("by_family", {})
    for family in ALL_FAMILIES:
        stats = by_family.get(family)
        if stats:
            lines.append(
                f"  family {family:16s} {stats.get(REWRITTEN, 0):4d}/{stats.get('total', 0):4d} "
                f"rewritten (in-progress {stats.get(IN_PROGRESS, 0)}, pending {stats.get(PENDING, 0)})"
            )
    by_owner = coverage.get("by_owner", {})
    rewritten_owners = {
        owner: stats
        for owner, stats in by_owner.items()
        if stats.get(REWRITTEN, 0) or stats.get(IN_PROGRESS, 0)
    }
    for owner in sorted(rewritten_owners):
        stats = rewritten_owners[owner]
        lines.append(
            f"  owner  {owner:16s} {stats.get(REWRITTEN, 0):4d}/{stats.get('total', 0):4d} "
            f"rewritten (in-progress {stats.get(IN_PROGRESS, 0)})"
        )
    return lines


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    parser.add_argument("--registry", type=Path, default=None, help="closure registry (unused override slot; closure enumerates fresh)")
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="rewrite the ledger row set (structure only; statuses preserved)",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help=(
            "recompute static-family statuses from the live .ui tree and write "
            "the ledger (credits rewritten-material only where the full family "
            "predicate passes; composition families keep their contract path)"
        ),
    )
    parser.add_argument(
        "--rename-map",
        action="append",
        default=[],
        metavar="OLD=NEW",
        help="carry a renamed surface's status/evidence forward (repeatable)",
    )
    parser.add_argument(
        "--allow-status-loss",
        action="store_true",
        help="permit --regenerate to drop non-pending rows whose surface vanished",
    )
    return parser.parse_args(argv)


def _parse_rename_map(pairs: Sequence[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValidationError(f"--rename-map entry {pair!r} must be OLD=NEW")
        old, new = pair.split("=", 1)
        if not old or not new:
            raise ValidationError(f"--rename-map entry {pair!r} must be OLD=NEW")
        mapping[old] = new
    return mapping


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    ledger_path = (
        args.ledger.resolve()
        if args.ledger is not None
        else repo_root / "qa/windows-ui-contract/material-rewrite-ledger.json"
    )
    try:
        if args.regenerate or args.evaluate:
            existing = read_ledger(ledger_path) if ledger_path.is_file() else None
            ledger = build_ledger(
                repo_root,
                existing,
                allow_status_loss=args.allow_status_loss,
                rename_map=_parse_rename_map(args.rename_map),
                evaluate=args.evaluate,
            )
            write_ledger(ledger_path, ledger)
        ledger = validate(repo_root, ledger_path)
    except ValidationError as error:
        print(f"Material rewrite ledger failed:\n{error}", file=sys.stderr)
        return 1

    for line in headline_lines(ledger):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
