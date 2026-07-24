#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material Start Center document-card contract."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-windows-startcenter-cards.py"
SPEC = importlib.util.spec_from_file_location("check_windows_startcenter_cards", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

DEFINITION = VALIDATOR.DEFINITION_PATH
RENDERER = "sfx2/source/control/startcentercard.cxx"
HEADER = "sfx2/inc/startcentercard.hxx"
RECENT = "sfx2/source/control/recentdocsview.cxx"
TEMPLATE = "sfx2/source/control/templatedefaultview.cxx"
STRINGS = "include/sfx2/strings.hrc"


class StartCenterCardContractTest(unittest.TestCase):
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

    # -- baseline ----------------------------------------------------------
    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    # -- definition token drift -------------------------------------------
    def test_palette_role_missing_from_scheme_fails(self) -> None:
        definition = self.contents[DEFINITION].replace(
            'name="surface-container-low"', 'name="scl-renamed"', 1
        )
        errors = self.failures(contents=self.with_content(DEFINITION, definition))
        self.assertTrue(
            any("token drift" in e and "surface-container-low" in e for e in errors), errors
        )

    def test_shape_radius_value_drift_fails(self) -> None:
        definition = self.contents[DEFINITION].replace(
            'name="corner-container" value="12"', 'name="corner-container" value="10"', 1
        )
        errors = self.failures(contents=self.with_content(DEFINITION, definition))
        self.assertTrue(
            any("token drift" in e and "corner-container" in e for e in errors), errors
        )

    def test_shape_radius_missing_fails(self) -> None:
        definition = self.contents[DEFINITION].replace(
            'name="corner-focus" value="6"', 'name="corner-focus-x" value="6"', 1
        )
        errors = self.failures(contents=self.with_content(DEFINITION, definition))
        self.assertTrue(
            any("corner-focus" in e and "missing" in e for e in errors), errors
        )

    # -- renderer ----------------------------------------------------------
    def test_renderer_guard_missing_fails(self) -> None:
        # The guarded token resolve is cached per scheme, so the call appears at
        # more than one site; the mutation must strip every occurrence to make the
        # guard marker vanish from code.
        source = self.contents[RENDERER].replace("MaterialTokens::fromThemeDefinition", "xxx")
        errors = self.failures(contents=self.with_content(RENDERER, source))
        self.assertTrue(any("renderer:guard marker missing" in e for e in errors), errors)

    def test_renderer_token_include_required(self) -> None:
        source = self.contents[RENDERER].replace("#include <vcl/MaterialTokens.hxx>", "", 1)
        errors = self.failures(contents=self.with_content(RENDERER, source))
        self.assertTrue(any("renderer:missing #include" in e for e in errors), errors)

    def test_renderer_comment_only_wiring_fails(self) -> None:
        # Comment out the real card-container draw call; comment-stripping must
        # make the anatomy marker vanish.
        source = self.contents[RENDERER].replace(
            "    rDev.DrawRect(rArea, nCardRadius, nCardRadius);",
            "    //rDev.DrawRect(rArea, nCardRadius, nCardRadius);",
            1,
        )
        errors = self.failures(contents=self.with_content(RENDERER, source))
        self.assertTrue(
            any("anatomy:card-container:marker missing" in e for e in errors), errors
        )

    def test_renderer_palette_role_not_consumed_fails(self) -> None:
        source = self.contents[RENDERER].replace('"surface-container-low"', '"surface"', 1)
        errors = self.failures(contents=self.with_content(RENDERER, source))
        self.assertTrue(
            any("palette role 'surface-container-low' not consumed" in e for e in errors), errors
        )

    def test_header_geometry_drift_fails(self) -> None:
        header = self.contents[HEADER].replace(
            "SC_CARD_PREVIEW_HEIGHT = 118", "SC_CARD_PREVIEW_HEIGHT = 100", 1
        )
        errors = self.failures(contents=self.with_content(HEADER, header))
        self.assertTrue(
            any("geometry constant SC_CARD_PREVIEW_HEIGHT" in e for e in errors), errors
        )

    # -- view wiring -------------------------------------------------------
    def test_view_renderer_call_missing_fails(self) -> None:
        source = self.contents[RECENT].replace(
            "sfx2::MaterialStartCenterCards::Paint(", "sfx2::MaterialStartCenterCards::NoPaint(", 1
        )
        errors = self.failures(contents=self.with_content(RECENT, source))
        self.assertTrue(any("view[recentdocs.card-grid]:marker missing" in e for e in errors), errors)

    def test_view_non_material_fallback_removed_fails(self) -> None:
        source = self.contents[RECENT].replace(
            "ThumbnailView::Paint(rRenderContext, aRect);",
            "ThumbnailView::PaintNone(rRenderContext, aRect);",
            1,
        )
        errors = self.failures(contents=self.with_content(RECENT, source))
        self.assertTrue(
            any("non-Material fallback missing" in e for e in errors), errors
        )

    def test_template_view_fallback_removed_fails(self) -> None:
        source = self.contents[TEMPLATE].replace(
            "TemplateLocalView::Paint(rRenderContext, rRect);",
            "TemplateLocalView::PaintNone(rRenderContext, rRect);",
            1,
        )
        errors = self.failures(contents=self.with_content(TEMPLATE, source))
        self.assertTrue(
            any("non-Material fallback missing" in e for e in errors), errors
        )

    def test_empty_resource_missing_fails(self) -> None:
        strings = self.contents[STRINGS].replace("STR_SC_NO_RECENT_MATCH", "STR_RENAMED_RECENT")
        errors = self.failures(contents=self.with_content(STRINGS, strings))
        self.assertTrue(any("not defined in" in e for e in errors), errors)

    def test_empty_resource_wrong_copy_fails(self) -> None:
        strings = self.contents[STRINGS].replace(
            "No recent documents match this pattern.", "Nothing to see here.", 1
        )
        errors = self.failures(contents=self.with_content(STRINGS, strings))
        self.assertTrue(any("lacks 'No recent documents match'" in e for e in errors), errors)

    # -- unavailable-preview anatomy (design 9.5) --------------------------
    def test_unavailable_accessor_call_removed_fails(self) -> None:
        # Drop the isUnavailable() read that drives the dimmed preview; the
        # anatomy marker must vanish so the missing-file dimming can't be silently
        # deleted while the role stays registered.
        source = self.contents[RENDERER].replace("rItem.isUnavailable()", "false", 1)
        errors = self.failures(contents=self.with_content(RENDERER, source))
        self.assertTrue(
            any("anatomy:unavailable-preview:marker missing" in e and "isUnavailable" in e
                for e in errors),
            errors,
        )

    def test_unavailable_disabled_container_token_removed_fails(self) -> None:
        # Re-point the dimming fill off @disabled-container: the token is both a
        # palette role and the unavailable-preview anatomy marker, so either check
        # must trip.
        source = self.contents[RENDERER].replace('"disabled-container"', '"surface"', 1)
        errors = self.failures(contents=self.with_content(RENDERER, source))
        self.assertTrue(any("disabled-container" in e for e in errors), errors)

    def test_disabled_container_scheme_drift_fails(self) -> None:
        # Rename the disabled-container role out of the light palette only; the
        # unavailable-preview dimming would resolve to nothing in that scheme.
        definition = self.contents[DEFINITION].replace(
            'name="disabled-container"', 'name="disabled-container-x"', 1
        )
        errors = self.failures(contents=self.with_content(DEFINITION, definition))
        self.assertTrue(
            any("token drift" in e and "disabled-container" in e for e in errors), errors
        )

    # -- migrated first-run pins (design 9.5) ------------------------------
    def test_recent_gate_reintroduced_fails(self) -> None:
        # The pre-rewrite gate is REMOVED; the Material path now owns the first-run
        # render via the invitation. Re-adding the gate to the Paint guard must trip
        # the pinned-absent marker so the regression can't slip back.
        source = self.contents[RECENT].replace(
            "IsMaterialStartCenterActive())\n    {",
            "IsMaterialStartCenterActive() && !mItemList.empty())\n    {",
            1,
        )
        self.assertNotEqual(source, self.contents[RECENT], "mutation did not apply")
        errors = self.failures(contents=self.with_content(RECENT, source))
        self.assertTrue(
            any("view[recentdocs.card-grid]:removed gate marker still present" in e
                for e in errors),
            errors,
        )

    def test_recent_welcome_removed_from_stock_fails(self) -> None:
        # The Welcome bitmap survives only on the stock path; deleting it there
        # would leave the default theme without a first-run screen. The stock pin
        # must trip.
        source = self.contents[RECENT].replace("STR_WELCOME_LINE1", "STR_WELCOME_RENAMED")
        errors = self.failures(contents=self.with_content(RECENT, source))
        self.assertTrue(
            any("stock fallback marker missing" in e and "STR_WELCOME_LINE1" in e
                for e in errors),
            errors,
        )

    def test_recent_welcome_inside_guard_fails(self) -> None:
        # The Welcome bitmap is REQUIRED-ABSENT from the Material guard block. Leak a
        # Welcome marker into the guard and the guard-absent pin must trip.
        source = self.contents[RECENT].replace(
            "aVisibleItems.reserve(mItemList.size());",
            "aVisibleItems.reserve(mItemList.size()); (void)STR_WELCOME_LINE1;",
            1,
        )
        self.assertNotEqual(source, self.contents[RECENT], "mutation did not apply")
        errors = self.failures(contents=self.with_content(RECENT, source))
        self.assertTrue(
            any("stock-only marker present inside Material block" in e and "STR_WELCOME_LINE1" in e
                for e in errors),
            errors,
        )

    def test_recent_invitation_reference_removed_fails(self) -> None:
        # Drop the first-run invitation title from the guarded empty state; both the
        # whole-file marker and the guard-present pin must trip.
        source = self.contents[RECENT].replace("SfxResId(STR_SC_INVITE_TITLE)", "OUString()", 1)
        errors = self.failures(contents=self.with_content(RECENT, source))
        self.assertTrue(
            any("STR_SC_INVITE_TITLE" in e for e in errors), errors
        )

    def test_renderer_invitation_helper_removed_fails(self) -> None:
        # Comment-strip-proof: rename the invitation painter; the first-run-invitation
        # anatomy marker must vanish.
        source = self.contents[RENDERER].replace("lcl_paintInvitation", "lcl_disabled")
        errors = self.failures(contents=self.with_content(RENDERER, source))
        self.assertTrue(
            any("anatomy:first-run-invitation:marker missing" in e and "lcl_paintInvitation" in e
                for e in errors),
            errors,
        )

    def test_invite_geometry_drift_fails(self) -> None:
        header = self.contents[HEADER].replace(
            "SC_CARD_INVITE_TITLE_TEXT = 18", "SC_CARD_INVITE_TITLE_TEXT = 16", 1
        )
        errors = self.failures(contents=self.with_content(HEADER, header))
        self.assertTrue(
            any("geometry constant SC_CARD_INVITE_TITLE_TEXT" in e for e in errors), errors
        )

    def test_template_gate_reintroduced_fails(self) -> None:
        source = self.contents[TEMPLATE].replace(
            "IsMaterialStartCenterActive())\n    {",
            "IsMaterialStartCenterActive() && !mItemList.empty())\n    {",
            1,
        )
        self.assertNotEqual(source, self.contents[TEMPLATE], "mutation did not apply")
        errors = self.failures(contents=self.with_content(TEMPLATE, source))
        self.assertTrue(
            any("view[templatedefault.card-grid]:removed gate marker still present" in e
                for e in errors),
            errors,
        )

    # -- registry integrity ------------------------------------------------
    def test_runtime_verified_true_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["runtime_verified"] = True
        errors = self.failures(registry=registry)
        self.assertTrue(any("runtime_verified" in e for e in errors), errors)

    def test_view_runtime_verified_true_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["views"][0]["runtime_verified"] = True
        errors = self.failures(registry=registry)
        self.assertTrue(any("no runtime evidence exists" in e for e in errors), errors)

    def test_expected_views_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["expected_views"] = 99
        errors = self.failures(registry=registry)
        self.assertIn("registry:expected_views:count drift", errors)

    def test_missing_required_view_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["views"] = [
            v for v in registry["views"] if v["view_id"] != "templatedefault.card-grid"
        ]
        registry["expected_views"] = len(registry["views"])
        errors = self.failures(registry=registry)
        self.assertTrue(
            any("missing required templatedefault.card-grid" in e for e in errors), errors
        )


if __name__ == "__main__":
    unittest.main()
