#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material notification-overlay contract (WIN-SHL-003).

Each mutation weakens exactly one guarantee -- the overlay's frame-child vehicle, its
bottom-right anchoring arithmetic, the raise-without-focus z-order call, the Material
anchoring defaults, the controller's stack-.ui wiring, the Tab-escape focus behaviour, the
stack .ui's non-dialog top level / Material rhythm / welded widget ids, or the
governed-surface cross-reference back from the rewrite ledger -- and asserts the checker
fails closed on it. A green baseline proves the production tree currently passes.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-notification-overlay-contract.py"
SPEC = importlib.util.spec_from_file_location("check_notification_overlay_contract", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

HOST_HXX = "sfx2/source/notification/NotificationOverlayWindow.hxx"
HOST_CXX = "sfx2/source/notification/NotificationOverlayWindow.cxx"
PREFS = "include/sfx2/notificationcenter.hxx"
CONTROLLER = "sfx2/source/notification/NotificationStackController.cxx"
STACK_UI = "sfx2/uiconfig/ui/notificationstack.ui"
LEDGER = VALIDATOR.LEDGER_PATH


class NotificationOverlayContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, self.contents = VALIDATOR.load_repository(REPOSITORY)

    def failures(
        self, *, registry: dict | None = None, contents: dict[str, str] | None = None
    ) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry,
            self.contents if contents is None else contents,
        )

    def with_content(self, path: str, text: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents[path] = text
        return contents

    def replaced(self, path: str, old: str, new: str) -> dict[str, str]:
        text = self.contents[path]
        self.assertIn(old, text, f"fixture drift: {old!r} not in {path}")
        return self.with_content(path, text.replace(old, new, 1))

    # -- baseline ----------------------------------------------------------
    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    def test_every_declared_source_is_readable(self) -> None:
        for relative in VALIDATOR._declared_sources(self.registry):
            self.assertIn(relative, self.contents, relative)

    # -- host vehicle ------------------------------------------------------
    def test_dropping_interim_item_window_base_fails(self) -> None:
        contents = self.replaced(
            HOST_HXX,
            "class NotificationOverlayWindow final : public InterimItemWindow",
            "class NotificationOverlayWindow final : public FloatingWindow",
        )
        self.assertTrue(any("host:header:marker missing" in f for f in self.failures(contents=contents)))

    def test_floating_window_vehicle_trips_the_absence_guard(self) -> None:
        contents = self.replaced(
            HOST_CXX,
            "InterimItemWindow::Resize();",
            "FloatingWindow::Resize();",
        )
        self.assertTrue(any("host:absent-guard" in f for f in self.failures(contents=contents)))

    def test_dropping_bottom_right_arithmetic_fails(self) -> None:
        contents = self.replaced(
            HOST_CXX,
            "tools::Long nX = aParent.Width() - nWidth - nHInset;",
            "tools::Long nX = nHInset;",
        )
        self.assertTrue(any("host:source:marker missing" in f for f in self.failures(contents=contents)))

    def test_dropping_zorder_raise_fails(self) -> None:
        contents = self.replaced(HOST_CXX, "SetZOrder(nullptr, ZOrderFlags::First);", "")
        self.assertTrue(any("host:source:marker missing" in f for f in self.failures(contents=contents)))

    def test_markers_hidden_in_comments_do_not_count(self) -> None:
        contents = self.replaced(
            HOST_CXX,
            "SetZOrder(nullptr, ZOrderFlags::First);",
            "// SetZOrder(nullptr, ZOrderFlags::First);",
        )
        self.assertTrue(any("host:source:marker missing" in f for f in self.failures(contents=contents)))

    def test_empty_absent_markers_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["host"]["absent_markers"] = []
        self.assertTrue(any("host:absent_markers" in f for f in self.failures(registry=registry)))

    # -- anchoring defaults ------------------------------------------------
    def test_width_default_drift_fails(self) -> None:
        contents = self.replaced(PREFS, "sal_Int32 Width = 420;", "sal_Int32 Width = 900;")
        self.assertTrue(any("anchoring_defaults:Width" in f for f in self.failures(contents=contents)))

    def test_inset_default_drift_fails(self) -> None:
        contents = self.replaced(
            PREFS, "sal_Int32 HorizontalInset = 16;", "sal_Int32 HorizontalInset = 0;"
        )
        self.assertTrue(
            any("anchoring_defaults:HorizontalInset" in f for f in self.failures(contents=contents))
        )

    def test_missing_preferences_struct_fails(self) -> None:
        contents = self.replaced(
            PREFS, "struct SFX2_DLLPUBLIC NotificationPreferences", "struct NotificationPrefs"
        )
        self.assertTrue(any("anchoring_defaults:struct" in f for f in self.failures(contents=contents)))

    # -- controller --------------------------------------------------------
    def test_dropping_reposition_call_fails(self) -> None:
        contents = self.replaced(
            CONTROLLER,
            "m_xOverlay->RepositionBottomRight(rPrefs.HorizontalInset, rPrefs.VerticalInset, rPrefs.Width);",
            "m_xOverlay->Show();",
        )
        self.assertTrue(any("controller:marker missing" in f for f in self.failures(contents=contents)))

    def test_dropping_stack_ui_load_fails(self) -> None:
        contents = self.replaced(
            CONTROLLER,
            'u"sfx/ui/notificationstack.ui"_ustr, u"NotificationStack"_ustr,',
            'u"sfx/ui/other.ui"_ustr, u"Other"_ustr,',
        )
        self.assertTrue(any("controller:marker missing" in f for f in self.failures(contents=contents)))

    def test_dropping_focus_escape_fails(self) -> None:
        contents = self.replaced(
            CONTROLLER, "/*bAllowCycleFocusOut*/ true", "/*bAllowCycleFocusOut*/ false"
        )
        self.assertTrue(any("controller:focus-escape" in f for f in self.failures(contents=contents)))

    # -- stack .ui ---------------------------------------------------------
    def test_dialog_toplevel_fails(self) -> None:
        contents = self.replaced(
            STACK_UI, '<object class="GtkBox" id="NotificationStack">',
            '<object class="GtkDialog" id="NotificationStack">',
        )
        self.assertTrue(any("stack_ui:toplevel class" in f for f in self.failures(contents=contents)))

    def test_toplevel_spacing_drift_fails(self) -> None:
        contents = self.replaced(
            STACK_UI,
            '<property name="orientation">vertical</property>\n    <property name="spacing">9</property>',
            '<property name="orientation">vertical</property>\n    <property name="spacing">0</property>',
        )
        self.assertTrue(any("stack_ui:toplevel spacing" in f for f in self.failures(contents=contents)))

    def test_card_box_spacing_drift_fails(self) -> None:
        text = self.contents[STACK_UI]
        head, sep, tail = text.partition('<object class="GtkBox" id="stack_cards">')
        self.assertTrue(sep)
        contents = self.with_content(
            STACK_UI, head + sep + tail.replace('<property name="spacing">9</property>',
                                                '<property name="spacing">2</property>', 1)
        )
        self.assertTrue(any("stack_ui:card-box spacing" in f for f in self.failures(contents=contents)))

    def test_missing_welded_id_fails(self) -> None:
        contents = self.replaced(STACK_UI, 'id="manager_button"', 'id="manager_button_renamed"')
        failures = self.failures(contents=contents)
        self.assertTrue(any("stack_ui:welded id" in f for f in failures))

    def test_missing_live_region_fails(self) -> None:
        contents = self.replaced(STACK_UI, 'id="live_region"', 'id="live_region_gone"')
        self.assertTrue(any("stack_ui:required id" in f for f in self.failures(contents=contents)))

    # -- governed surfaces -------------------------------------------------
    def test_empty_governed_surfaces_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["governed_surfaces"] = []
        self.assertTrue(any("governed_surfaces" in f for f in self.failures(registry=registry)))

    def test_unknown_governed_surface_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["governed_surfaces"][0]["surface"] = "native:does-not-exist"
        self.assertTrue(
            any("is not a rewrite-ledger row" in f for f in self.failures(registry=registry))
        )

    def test_governed_surface_family_mismatch_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["governed_surfaces"][0]["family"] = "dialog"
        self.assertTrue(any("family is" in f for f in self.failures(registry=registry)))

    def test_duplicate_governed_surface_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["governed_surfaces"].append(copy.deepcopy(registry["governed_surfaces"][0]))
        self.assertTrue(any("enumerated twice" in f for f in self.failures(registry=registry)))

    def test_credited_row_pointing_at_another_contract_fails(self) -> None:
        ledger = json.loads(self.contents[LEDGER])
        for row in ledger["surfaces"]:
            if row["surface"] == "native:notification-overlay-window":
                row["rewrite_status"] = "rewritten-material"
                row["rewrite_evidence"] = {
                    "commit": "0" * 40,
                    "contract": "qa/windows-ui-contract/notification-overlay-composition.json",
                    "capture": {"scene": None, "sample_batch": "x", "captured": False},
                    "anatomy_markers": {"contract_marker": "material-something-else"},
                }
        contents = self.with_content(LEDGER, json.dumps(ledger))
        self.assertTrue(
            any("does not point back at this contract" in f for f in self.failures(contents=contents))
        )

    # -- registry header ---------------------------------------------------
    def test_runtime_verified_claim_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in f for f in self.failures(registry=registry)))

    def test_cross_reference_marker_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["ledger"]["cross_reference_marker"] = "material-other"
        self.assertTrue(
            any("cross_reference_marker" in f for f in self.failures(registry=registry))
        )


if __name__ == "__main__":
    unittest.main()
