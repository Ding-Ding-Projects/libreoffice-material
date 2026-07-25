#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material document-tab strip contract (stage 3).

Each test proves an inversion of the contract fails closed: the pristine tree
passes, and every mutation (a dropped TabBar::Paint ride, a selection-dependent
accent, a hardcoded colour, the TabsEnabled guard removed or defaulted on, a
topness-violating cast smuggled into the frame-raise, the reused Window-menu
path deleted, or a missing appearance-editor id) turns the checker red.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-document-tab-strip.py"
SPEC = importlib.util.spec_from_file_location("check_document_tab_strip", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class DocumentTabStripContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract, self.contents = VALIDATOR.load_repository(REPOSITORY)
        self.cxx_key = self.contract["strip_cxx"]
        self.hxx_key = self.contract["strip_hxx"]
        self.ui_key = self.contract["appearance_ui"]
        self.lib_key = self.contract["library_mk"]
        self.uimk_key = self.contract["uiconfig_mk"]
        self.xcs_key = self.contract["tabs_enabled_guard"]["schema_file"]
        self.ref_key = self.contract["reused_frame_raise_api"]["reference_source"]

    def failures(self, *, contract=None, contents=None) -> list[str]:
        return VALIDATOR.violations(
            self.contract if contract is None else contract,
            self.contents if contents is None else contents,
        )

    def mutated(self, key: str, old: str, new: str) -> dict[str, str]:
        contents = dict(self.contents)
        self.assertIn(old, contents[key], f"fixture drift: {old!r} not in {key}")
        contents[key] = contents[key].replace(old, new)
        return contents

    # --- pristine ----------------------------------------------------------

    def test_pristine_passes(self) -> None:
        self.assertEqual(self.failures(), [])

    # --- TabBar subclass / ride -------------------------------------------

    def test_missing_base_paint_ride_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key, "TabBar::Paint(rRenderContext, rRect);", "// no base paint"
        )
        self.assertTrue(any("base paint" in f for f in self.failures(contents=contents)))

    def test_not_a_tabbar_subclass_fails(self) -> None:
        contents = self.mutated(
            self.hxx_key,
            "class SfxDocumentTabBar final : public TabBar",
            "class SfxDocumentTabBar final : public vcl::Window",
        )
        self.assertTrue(self.failures(contents=contents))

    # --- Material paint ride ----------------------------------------------

    def test_missing_material_token_marker_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key, 'findColor("outline-variant")', 'findColor("primary")'
        )
        self.assertTrue(self.failures(contents=contents))

    def test_missing_env_guard_fails(self) -> None:
        contents = self.mutated(self.cxx_key, "VCL_FILE_WIDGET_THEME", "SOME_OTHER_ENV")
        self.assertTrue(self.failures(contents=contents))

    def test_selection_dependent_accent_fails(self) -> None:
        # Smuggle a selection consult into the overlay body.
        contents = self.mutated(
            self.cxx_key,
            "rRenderContext.SetFillColor(aColor);",
            "if (IsPageSelected(nPageId)) rRenderContext.SetFillColor(aColor);",
        )
        self.assertTrue(
            any("selection state" in f for f in self.failures(contents=contents))
        )

    # --- style-sourced rendering ------------------------------------------

    def test_hardcoded_colour_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "maMaterialTabColors[nPageId] = rColor;",
            "maMaterialTabColors[nPageId] = Color(0xFF0000);",
        )
        self.assertTrue(
            any("hardcoded" in f for f in self.failures(contents=contents))
        )

    def test_missing_normalizer_use_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key, "SfxDocTabStyle::Normalize", "SomeOther::Normalize"
        )
        self.assertTrue(self.failures(contents=contents))

    # --- TabsEnabled guard -------------------------------------------------

    def test_factory_without_nullptr_guard_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "    if (!IsTabsEnabled())\n        return nullptr;",
            "    // guard removed",
        )
        self.assertTrue(
            any("guard" in f for f in self.failures(contents=contents))
        )

    def test_tabsenabled_default_true_fails(self) -> None:
        old = '<prop oor:name="TabsEnabled" oor:type="xs:boolean" oor:nillable="false">'
        # Flip only the TabsEnabled default value.
        xcs = self.contents[self.xcs_key]
        idx = xcs.find(old)
        seg = xcs[idx : idx + 400].replace("<value>false</value>", "<value>true</value>", 1)
        contents = dict(self.contents)
        contents[self.xcs_key] = xcs[:idx] + seg + xcs[idx + 400 :]
        self.assertTrue(
            any("default" in f for f in self.failures(contents=contents))
        )

    # --- frame-raise reuse -------------------------------------------------

    def test_topness_cast_in_raise_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "pWin->GrabFocus();",
            "static_cast<WorkWindow*>(pWin.get())->ToTop(); pWin->GrabFocus();",
        )
        self.assertTrue(
            any("topness-violating" in f for f in self.failures(contents=contents))
        )

    def test_missing_totop_in_raise_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "pWin->ToTop(ToTopFlags::RestoreWhenMin);",
            "// window not raised",
        )
        self.assertTrue(self.failures(contents=contents))

    def test_reference_frame_raise_path_vanished_fails(self) -> None:
        contents = self.mutated(
            self.ref_key,
            "pWin->ToTop( ToTopFlags::RestoreWhenMin );",
            "pWin->Show();",
        )
        self.assertTrue(
            any("reference" in f for f in self.failures(contents=contents))
        )

    # --- appearance editor -------------------------------------------------

    def test_missing_context_menu_marker_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key, "CommandEventId::ContextMenu", "CommandEventId::Wheel"
        )
        self.assertTrue(self.failures(contents=contents))

    def test_missing_ui_widget_id_fails(self) -> None:
        contents = self.mutated(self.ui_key, 'id="fontsize"', 'id="removed"')
        self.assertTrue(
            any("fontsize" in f for f in self.failures(contents=contents))
        )

    # --- build registration ------------------------------------------------

    def test_missing_library_registration_fails(self) -> None:
        contents = self.mutated(
            self.lib_key,
            "sfx2/source/appl/documenttabbar \\",
            "sfx2/source/appl/othermodule \\",
        )
        self.assertTrue(
            any("library" in f for f in self.failures(contents=contents))
        )

    def test_missing_uiconfig_registration_fails(self) -> None:
        contents = self.mutated(
            self.uimk_key,
            "sfx2/uiconfig/ui/documenttabappearance \\",
            "sfx2/uiconfig/ui/otherdialog \\",
        )
        self.assertTrue(
            any("uiconfig" in f for f in self.failures(contents=contents))
        )

    # --- runtime honesty ---------------------------------------------------

    def test_runtime_verified_true_fails(self) -> None:
        contract = dict(self.contract)
        contract["runtime_verified"] = True
        self.assertTrue(
            any("runtime_verified" in f for f in self.failures(contract=contract))
        )


if __name__ == "__main__":
    unittest.main()
