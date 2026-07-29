#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material document-tab strip contract (stage 3).

Each test proves an inversion of the contract fails closed: the pristine tree
passes, and mutations covering production ownership/layout, lifecycle
synchronisation, disposed-frame safety, dynamic-set creation, active-page
selection, typography, CSS-hex decoding/round-trip, favourite behaviour, the
paint/raise paths, and the default-off guard all turn the checker red.
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
        self.frame_key = self.contract["frame_cxx"]
        self.frame_impl_key = self.contract["frame_impl_hxx"]
        self.frame2_key = self.contract["frame2_cxx"]
        self.viewframe_key = self.contract["viewframe_cxx"]
        self.viewframe2_key = self.contract["viewframe2_cxx"]
        self.tabbar_cxx_key = self.contract["tabbar_cxx"]

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

    def test_per_page_font_not_consumed_by_tabbar_fails(self) -> None:
        contents = self.mutated(
            self.tabbar_cxx_key,
            "pItem->moPageFont.value_or(bCurrent ? aFont : aLightFont)",
            "(bCurrent ? aFont : aLightFont)",
        )
        self.assertTrue(
            any("paint-path" in f for f in self.failures(contents=contents))
        )

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

    def test_wrong_history_path_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "/org.openoffice.Office.Common/History/DocumentTabStyles",
            "/org.openoffice.Office.Common/Histories/DocumentTabStyles",
        )
        self.assertTrue(any("editor:cxx" in f for f in self.failures(contents=contents)))

    def test_first_dynamic_style_cannot_be_created_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "xEntry.set(xFactory->createInstance(), uno::UNO_QUERY_THROW);",
            "xEntry.clear();",
        )
        self.assertTrue(any("createInstance" in f for f in self.failures(contents=contents)))

    def test_font_size_editor_reset_to_default_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "xFontSize->set_value(aStyle.nFontSize);",
            "xFontSize->set_value(SfxDocTabStyle::DEFAULT_FONT_SIZE);",
        )
        self.assertTrue(any("roundtrip" in f for f in self.failures(contents=contents)))

    def test_font_size_short_is_not_read_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "else if (sal_Int16 nValue16; aAny >>= nValue16)",
            "else if (sal_Int64 nValue64; aAny >>= nValue64)",
        )
        self.assertTrue(any("style:cxx" in f for f in self.failures(contents=contents)))

    def test_lossy_rgb_serialization_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "xColor->set_text(aStyle.aBackgroundColor);",
            "xColor->set_text(aStyle.oColor->AsRGBHexString());",
        )
        self.assertTrue(any("lossy" in f for f in self.failures(contents=contents)))

    # --- production ownership and lifecycle -------------------------------

    def test_no_frame_owner_fails(self) -> None:
        contents = self.mutated(
            self.frame_impl_key,
            "VclPtr<SfxDocumentTabBar> pDocumentTabBar",
            "VclPtr<vcl::Window> pDocumentTabBar",
        )
        self.assertTrue(any("owner" in f for f in self.failures(contents=contents)))

    def test_owner_requires_complete_document_tab_type_fails(self) -> None:
        contents = self.mutated(
            self.frame_impl_key,
            "#include <SfxDocumentTabBar.hxx>\n",
            "",
        )
        self.assertTrue(
            any("owner:definition" in f for f in self.failures(contents=contents))
        )

    def test_factory_not_called_by_frame_owner_fails(self) -> None:
        contents = self.mutated(
            self.frame_key,
            "SfxDocumentTabBar::Create(&GetWindow(), GetFrameInterface())",
            "VclPtr<SfxDocumentTabBar>()",
        )
        self.assertTrue(any("owner:create" in f for f in self.failures(contents=contents)))

    def test_layout_does_not_reserve_strip_height_fails(self) -> None:
        contents = self.mutated(
            self.frame_key,
            "aPos.AdjustY(nTabHeight);",
            "// content overlaps strip",
        )
        self.assertTrue(any("owner:layout" in f for f in self.failures(contents=contents)))

    def test_layout_does_not_subtract_horizontal_border_twice(self) -> None:
        contents = self.mutated(
            self.frame_key,
            "const tools::Long nAvailableWidth = std::max<tools::Long>(0, aSize.Width());",
            "const tools::Long nAvailableWidth"
            " = std::max<tools::Long>(0, aSize.Width() - nDeltaX);",
        )
        self.assertTrue(any("owner:layout" in f for f in self.failures(contents=contents)))

    def test_open_does_not_refresh_existing_strips_fails(self) -> None:
        old = (
            "m_pImpl->pWorkWin = new SfxWorkWindow(&pFrame->GetWindow(), *this, *pFrame);\n"
            "    // This is the normal product frame/layout seam: once a real view and its\n"
            "    // WorkWindow exist, every top-level frame owns and sizes its guarded strip.\n"
            "    RefreshDocumentTabBars_Impl();"
        )
        contents = self.mutated(
            self.frame_key,
            old,
            "m_pImpl->pWorkWin = new SfxWorkWindow(&pFrame->GetWindow(), *this, *pFrame);",
        )
        self.assertTrue(any("owner:workwindow" in f for f in self.failures(contents=contents)))

    def test_close_does_not_dispose_owned_strip_fails(self) -> None:
        contents = self.mutated(
            self.frame_key,
            "m_pImpl->pDocumentTabBar.disposeAndClear();",
            "m_pImpl->pDocumentTabBar.clear();",
        )
        self.assertTrue(any("lifetime" in f for f in self.failures(contents=contents)))

    # --- synchronization and disposed frames ------------------------------

    def test_title_change_does_not_refresh_fails(self) -> None:
        contents = self.mutated(
            self.viewframe2_key,
            "SfxFrame::RefreshDocumentTabBars_Impl();",
            "// title change not propagated",
        )
        self.assertTrue(any("UpdateTitle" in f for f in self.failures(contents=contents)))

    def test_current_frame_change_does_not_refresh_fails(self) -> None:
        contents = self.mutated(
            self.viewframe_key,
            "pFrame->GetFrame().RefreshDocumentTabBar_Impl();",
            "// activation not propagated",
        )
        self.assertTrue(any("SetViewFrame" in f for f in self.failures(contents=contents)))

    def test_rebuild_keeps_disposed_frames_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "if (!lcl_isLiveDocumentFrame(xFrame))",
            "if (!xFrame.is())",
        )
        self.assertTrue(any("Rebuild" in f for f in self.failures(contents=contents)))

    def test_selection_does_not_restore_owner_fails(self) -> None:
        old = (
            "const sal_uInt16 nSelectedPage = GetCurPageId();\n"
            "    RaiseFrameForPage(nSelectedPage);\n"
            "    SelectOwnerFrame();"
        )
        contents = self.mutated(
            self.cxx_key,
            old,
            "const sal_uInt16 nSelectedPage = GetCurPageId();\n"
            "    RaiseFrameForPage(nSelectedPage);",
        )
        self.assertTrue(any("selection" in f for f in self.failures(contents=contents)))

    def test_config_commit_does_not_refresh_all_strips_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "SfxFrame::RefreshDocumentTabBars_Impl();",
            "// config commit not propagated",
        )
        self.assertTrue(any("EditTabAppearance" in f for f in self.failures(contents=contents)))

    # --- CSS hex and favourite behaviour ----------------------------------

    def test_short_rgb_nibbles_not_expanded_fails(self) -> None:
        contents = self.mutated(self.cxx_key, "* 17;", "* 16;")
        self.assertTrue(any("hex:decode" in f for f in self.failures(contents=contents)))

    def test_rgba_alpha_byte_lost_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "lcl_hexByte(rColor, 7) : 255",
            "lcl_hexByte(rColor, 5) : 255",
        )
        self.assertTrue(any("hex:decode" in f for f in self.failures(contents=contents)))

    def test_favorite_sort_becomes_inert_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "if (a.aStyle.bFavorite != b.aStyle.bFavorite)",
            "if (false)",
        )
        self.assertTrue(any("favorite" in f for f in self.failures(contents=contents)))

    def test_favorite_visual_marker_removed_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            'u"\\u2605 "_ustr + rRow.aStyle.aLabel',
            "rRow.aStyle.aLabel",
        )
        self.assertTrue(any("favorite" in f for f in self.failures(contents=contents)))

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

    def test_missing_mapunit_definition_include_fails(self) -> None:
        contents = self.mutated(
            self.cxx_key,
            "#include <tools/mapunit.hxx>\n",
            "",
        )
        self.assertTrue(
            any("build:include" in f for f in self.failures(contents=contents))
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
