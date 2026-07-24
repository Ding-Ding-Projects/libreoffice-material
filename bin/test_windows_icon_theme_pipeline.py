#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the WIN-FND-007 icon-theme pipeline contract."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-windows-icon-theme-pipeline.py"
SPEC = importlib.util.spec_from_file_location("check_windows_icon_theme_pipeline", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

HEADER = "vcl/inc/IconThemeSelector.hxx"
SELECTOR = "vcl/source/app/IconThemeSelector.cxx"
INFO = "vcl/source/app/IconThemeInfo.cxx"
FOUNDATIONS = "docs/design/01-foundations.md"
ROOT_DOC = "MATERIAL_DESIGN.md"
LINKS = "icon-themes/colibre/links.txt"
STARTCENTER_UI = "sfx2/uiconfig/ui/startcenter.ui"
ARTICLE_SVG_COLIBRE = "icon-themes/colibre/sfx2/res/startcenter/article.svg"
ARTICLE_SVG_SVGTHEME = "icon-themes/colibre_svg/sfx2/res/startcenter/article.svg"


class IconThemePipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, self.contents, self.theme_dirs = VALIDATOR.load_repository(REPOSITORY)

    def failures(self, *, registry=None, contents=None, theme_dirs=None) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry,
            self.contents if contents is None else contents,
            self.theme_dirs if theme_dirs is None else theme_dirs,
        )

    def with_content(self, path: str, text: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents[path] = text
        return contents

    def mutated(self, path: str, old: str, new: str) -> dict[str, str]:
        text = self.contents[path]
        self.assertIn(old, text, f"anchor {old!r} not in {path}")
        return self.with_content(path, text.replace(old, new, 1))

    # -- baseline ----------------------------------------------------------
    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    # -- fallback ----------------------------------------------------------
    def test_removed_fallback_id_fails(self) -> None:
        contents = self.mutated(
            HEADER, 'FALLBACK_LIGHT_ICON_THEME_ID = u"colibre"_ustr', 'FALLBACK_LIGHT_ICON_THEME_ID = u"breeze"_ustr'
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("fallback:" in e for e in errors), errors)

    # -- windows route -----------------------------------------------------
    def test_removed_windows_route_marker_fails(self) -> None:
        contents = self.mutated(SELECTOR, 'return "colibre_dark";', 'return "sifr_dark";')
        errors = self.failures(contents=contents)
        self.assertTrue(any("windows_route:" in e for e in errors), errors)

    def test_removed_windows_guard_fails(self) -> None:
        contents = self.mutated(SELECTOR, "#ifdef _WIN32", "#ifdef _NOT_WIN32")
        errors = self.failures(contents=contents)
        self.assertTrue(any("windows_route:" in e for e in errors), errors)

    # -- preferred override ------------------------------------------------
    def test_removed_preferred_override_fails(self) -> None:
        contents = self.mutated(SELECTOR, "return mPreferredIconTheme;", "return OUString();")
        errors = self.failures(contents=contents)
        self.assertTrue(any("preferred_override:" in e for e in errors), errors)

    # -- no material in selector ------------------------------------------
    def test_material_in_selector_fails(self) -> None:
        contents = self.with_content(
            SELECTOR, self.contents[SELECTOR] + '\n// route material_dark on Windows here later\n'
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("no_material_in_selector:" in e for e in errors), errors)

    # -- package naming ----------------------------------------------------
    def test_removed_package_prefix_fails(self) -> None:
        contents = self.mutated(
            INFO, 'ICON_THEME_PACKAGE_PREFIX[] = u"images_"', 'ICON_THEME_PACKAGE_PREFIX[] = u"icons_"'
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("package_naming:" in e for e in errors), errors)

    def test_removed_display_strip_fails(self) -> None:
        # The "_dark" display-strip marker occurs once; mutating it drops the pin.
        contents = self.mutated(INFO, 'endsWith("_dark", &aDisplayName)', 'endsWith("_x", &aDisplayName)')
        errors = self.failures(contents=contents)
        self.assertTrue(any("package_naming:" in e for e in errors), errors)

    # -- theme directory enumeration --------------------------------------
    def test_new_material_directory_fails(self) -> None:
        errors = self.failures(theme_dirs=sorted(self.theme_dirs + ["material"]))
        self.assertTrue(any("installed_theme_dirs" in e for e in errors), errors)
        self.assertTrue(any("'material'-prefixed" in e for e in errors), errors)

    def test_dropped_directory_fails(self) -> None:
        reduced = [d for d in self.theme_dirs if d != "colibre"]
        errors = self.failures(theme_dirs=reduced)
        self.assertTrue(any("installed_theme_dirs" in e and "declared-but-absent" in e for e in errors), errors)

    def test_material_theme_installed_true_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["material_theme_installed"] = True
        errors = self.failures(registry=registry)
        self.assertTrue(any("material_theme_installed:must be false" in e for e in errors), errors)

    # -- iconography prose -------------------------------------------------
    def test_removed_semantic_mirroring_rule_fails(self) -> None:
        contents = self.mutated(
            FOUNDATIONS, "RTL mirroring is applied per glyph", "RTL mirroring is applied to every glyph"
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("iconography_prose:" in e for e in errors), errors)

    def test_removed_honesty_flag_fails(self) -> None:
        contents = self.mutated(
            FOUNDATIONS,
            "theme for the native pipeline is specified here, not yet implemented",
            "theme for the native pipeline is now implemented",
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("not-yet-implemented honesty flag" in e for e in errors), errors)

    def test_removed_root_generated_art_rule_fails(self) -> None:
        contents = self.mutated(ROOT_DOC, "Generated art is not accepted as", "Generated art is fine as")
        errors = self.failures(contents=contents)
        self.assertTrue(any("iconography_prose:" in e and ROOT_DOC in e for e in errors), errors)

    # -- icon size linter citation ----------------------------------------
    def test_ci_enforced_claim_must_match_reality(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["icon_size_linter"]["ci_enforced"] = True
        errors = self.failures(registry=registry)
        self.assertTrue(any("icon_size_linter:ci_enforced" in e for e in errors), errors)

    def test_linter_referenced_in_workflow_requires_true(self) -> None:
        # If the workflow starts referencing the linter, ci_enforced:false becomes dishonest.
        workflow = self.registry["icon_size_linter"]["ci_workflow"]
        text = self.contents.get(workflow, "") + "\n        run: python3 bin/check-icon-sizes.py\n"
        errors = self.failures(contents=self.with_content(workflow, text))
        self.assertTrue(any("icon_size_linter:ci_enforced" in e for e in errors), errors)

    # -- material startcenter glyphs --------------------------------------
    def test_missing_authored_svg_fails(self) -> None:
        contents = dict(self.contents)
        self.assertIn(ARTICLE_SVG_SVGTHEME, contents)
        del contents[ARTICLE_SVG_SVGTHEME]
        errors = self.failures(contents=contents)
        self.assertTrue(any("authored glyph missing" in e for e in errors), errors)

    def test_authored_svg_wrong_fill_fails(self) -> None:
        contents = self.with_content(
            ARTICLE_SVG_COLIBRE,
            '<svg viewBox="0 0 18 18"><rect fill="#000000" width="18" height="18"/></svg>\n',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("monochrome fill" in e for e in errors), errors)

    def test_authored_glyph_aliased_fails(self) -> None:
        # Aliasing an authored name would shadow the real SVG via getRealImageName.
        text = self.contents[LINKS] + "\nsfx2/res/startcenter/article.png cmd/lc_open.png\n"
        errors = self.failures(contents=self.with_content(LINKS, text))
        self.assertTrue(any("must NOT be aliased" in e and "article" in e for e in errors), errors)

    def test_missing_reuse_alias_fails(self) -> None:
        text = self.contents[LINKS].replace(
            "sfx2/res/startcenter/folder_open.png cmd/lc_open.png\n", "", 1
        )
        errors = self.failures(contents=self.with_content(LINKS, text))
        self.assertTrue(any("missing the reuse-alias" in e and "folder_open" in e for e in errors), errors)

    def test_reuse_alias_wrong_target_fails(self) -> None:
        text = self.contents[LINKS].replace(
            "sfx2/res/startcenter/folder_open.png cmd/lc_open.png",
            "sfx2/res/startcenter/folder_open.png cmd/sc_ok.png",
            1,
        )
        errors = self.failures(contents=self.with_content(LINKS, text))
        self.assertTrue(any("expected 'cmd/lc_open.png'" in e for e in errors), errors)

    def test_missing_alias_target_fails(self) -> None:
        contents = dict(self.contents)
        self.assertIn("icon-themes/colibre/cmd/lc_open.png", contents)
        del contents["icon-themes/colibre/cmd/lc_open.png"]
        errors = self.failures(contents=contents)
        self.assertTrue(any("reuse-alias target missing" in e for e in errors), errors)

    def test_aliased_name_with_authored_file_fails(self) -> None:
        contents = self.with_content(
            "icon-themes/colibre/sfx2/res/startcenter/folder_open.svg",
            '<svg viewBox="0 0 18 18"><rect fill="#3a3a38" width="18" height="18"/></svg>\n',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("must not also ship an authored file" in e for e in errors), errors)

    def test_ui_unwired_glyph_fails(self) -> None:
        text = self.contents[STARTCENTER_UI].replace(
            "sfx2/res/startcenter/search.png", "sfx2/res/startcenter/newglyph.png", 1
        )
        errors = self.failures(contents=self.with_content(STARTCENTER_UI, text))
        self.assertTrue(
            any("neither an authored SVG nor a links.txt alias" in e for e in errors), errors
        )

    def test_dead_asset_fails(self) -> None:
        text = self.contents[STARTCENTER_UI].replace(
            "sfx2/res/startcenter/history.png", "window-history-symbolic", 1
        )
        errors = self.failures(contents=self.with_content(STARTCENTER_UI, text))
        self.assertTrue(any("dead assets" in e and "history" in e for e in errors), errors)

    def test_legacy_ref_present_fails(self) -> None:
        text = self.contents[STARTCENTER_UI].replace(
            "sfx2/res/startcenter/article.png", "res/odt_32_8.png", 1
        )
        errors = self.failures(contents=self.with_content(STARTCENTER_UI, text))
        self.assertTrue(any("legacy stock icon reference" in e for e in errors), errors)

    def test_missing_glyph_section_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        del registry["material_startcenter_glyphs"]
        errors = self.failures(registry=registry)
        self.assertTrue(any("material_startcenter_glyphs:object required" in e for e in errors), errors)

    def test_authored_aliased_overlap_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["material_startcenter_glyphs"]["aliased"]["article"] = "cmd/lc_open.png"
        errors = self.failures(registry=registry)
        self.assertTrue(any("both authored and aliased" in e for e in errors), errors)

    # -- meta --------------------------------------------------------------
    def test_runtime_verified_true_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["runtime_verified"] = True
        errors = self.failures(registry=registry)
        self.assertTrue(any("runtime_verified:no runtime evidence" in e for e in errors), errors)

    def test_contract_name_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["contract"] = "something-else"
        errors = self.failures(registry=registry)
        self.assertTrue(any("registry:contract" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
