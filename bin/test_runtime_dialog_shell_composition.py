#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for runtime-composed Material dialog shells."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-runtime-dialog-shell-composition.py"
SPEC = importlib.util.spec_from_file_location("runtime_dialog_shell_composition", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

VIEW3D = "chart2/uiconfig/ui/3dviewdialog.ui"
ATTRIBUTE = "chart2/uiconfig/ui/attributedialog.ui"
CUSTOMIZE = "cui/uiconfig/ui/customizedialog.ui"
HYPERLINK = "cui/uiconfig/ui/hyperlinkdlg.ui"
SHAPE_PARAGRAPH = "chart2/uiconfig/ui/paradialog.ui"
BORDER_AREA = "cui/uiconfig/ui/borderareatransparencydialog.ui"
FORMAT_SECTION = "sw/uiconfig/swriter/ui/formatsectiondialog.ui"
PDF_OPTIONS = "filter/uiconfig/ui/pdfoptionsdialog.ui"
PICTURE = "sw/uiconfig/swriter/ui/picturedialog.ui"
VIEW3D_HOST = "chart2/source/controller/dialogs/dlg_View3D.cxx"
ATTRIBUTE_HOST = "chart2/source/controller/dialogs/dlg_ObjectProperties.cxx"
SHAPE_PARAGRAPH_HOST = "chart2/source/controller/dialogs/dlg_ShapeParagraph.cxx"
BORDER_HOST = "cui/source/tabpages/bbdlg.cxx"


class RuntimeDialogShellCompositionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, self.contents, self.ledger = VALIDATOR.load_repository(REPOSITORY)

    def failures(
        self,
        *,
        registry: dict | None = None,
        contents: dict[str, str] | None = None,
        ledger: dict | None = None,
    ) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry,
            self.contents if contents is None else contents,
            self.ledger if ledger is None else ledger,
        )

    def replace_once(self, path: str, old: str, new: str) -> dict[str, str]:
        source = self.contents[path]
        self.assertEqual(source.count(old), 1, f"expected exactly one {old!r} in {path}")
        contents = dict(self.contents)
        contents[path] = source.replace(old, new, 1)
        return contents

    def shell(self, registry: dict, surface: str) -> dict:
        return next(item for item in registry["shells"] if item["surface"] == surface)

    def ledger_row(self, ledger: dict, surface: str) -> dict:
        return next(item for item in ledger["surfaces"] if item["surface"] == surface)

    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    def test_every_expected_surface_has_one_contract_row(self) -> None:
        surfaces = [item["surface"] for item in self.registry["shells"]]
        self.assertEqual(len(surfaces), len(set(surfaces)))
        self.assertEqual(set(surfaces), set(VALIDATOR.EXPECTED_SURFACES))

    def test_runtime_claim_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in item for item in self.failures(registry=registry)))

    def test_dependency_contract_marker_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.shell(registry, PDF_OPTIONS)["dependency_contract"]["contract_marker"] = "wrong"
        errors = self.failures(registry=registry)
        self.assertTrue(any(PDF_OPTIONS in item and "dependency contract marker" in item for item in errors), errors)

    def test_surface_allow_list_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["shells"][0]["surface"] = "cui/uiconfig/ui/not-a-real-dialog.ui"
        self.assertTrue(any("surface set drifted" in item for item in self.failures(registry=registry)))

    def test_material_margin_drift_fails(self) -> None:
        contents = self.replace_once(
            VIEW3D,
            '<property name="margin-start">12</property>',
            '<property name="margin-start">0</property>',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("margin-start" in item and "expected 12" in item for item in errors), errors)

    def test_legacy_border_return_fails(self) -> None:
        contents = self.replace_once(
            PICTURE,
            '<property name="title" translatable="yes" context="picturedialog|PictureDialog">Image</property>',
            '<property name="border-width">6</property>\n    <property name="title" translatable="yes" context="picturedialog|PictureDialog">Image</property>',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any(PICTURE in item and "legacy positive border-width" in item for item in errors), errors)

    def test_expanded_shell_vertical_margin_drift_fails(self) -> None:
        contents = self.replace_once(
            SHAPE_PARAGRAPH,
            '<property name="margin-top">12</property>',
            '<property name="margin-top">6</property>',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("margin-top" in item and "expected 12" in item for item in errors), errors)

    def test_scrollable_notebook_regression_fails(self) -> None:
        contents = self.replace_once(
            CUSTOMIZE,
            '<property name="scrollable">True</property>',
            '<property name="scrollable">False</property>',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("scrollable=True" in item for item in errors), errors)

    def test_modeless_contract_drift_fails(self) -> None:
        contents = self.replace_once(
            HYPERLINK,
            '<property name="modal">False</property>',
            '<property name="modal">True</property>',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any(HYPERLINK in item and "modal=False" in item for item in errors), errors)

    def test_runtime_title_marker_removed_fails(self) -> None:
        contents = self.replace_once(
            ATTRIBUTE_HOST,
            "m_xDialog->set_title(rDialogParameter.getLocalizedName());",
            "m_xDialog->set_title_removed(rDialogParameter.getLocalizedName());",
        )
        errors = self.failures(contents=contents)
        self.assertTrue(
            any(ATTRIBUTE in item and "runtime title marker occurs 0 times" in item for item in errors),
            errors,
        )

    def test_runtime_page_occurrence_drift_fails(self) -> None:
        contents = self.replace_once(
            ATTRIBUTE_HOST,
            'AddTabPage(u"xerrorbar"_ustr',
            'AddTabPage(u"xerrorbar-removed"_ustr',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(
            any(ATTRIBUTE in item and "runtime page occurrences drifted" in item for item in errors),
            errors,
        )

    def test_static_page_claim_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.shell(registry, VIEW3D)["notebook"]["static_pages"] = 1
        errors = self.failures(registry=registry)
        self.assertTrue(any("empty runtime host" in item for item in errors), errors)

    def test_footer_response_drift_fails(self) -> None:
        contents = self.replace_once(
            VIEW3D,
            '<action-widget response="-5">ok</action-widget>',
            '<action-widget response="101">ok</action-widget>',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("footer action-widget" in item for item in errors), errors)

    def test_auxiliary_reset_removed_fails(self) -> None:
        contents = self.replace_once(
            CUSTOMIZE,
            '<object class="GtkButton" id="reset">',
            '<object class="GtkButton" id="reset-removed">',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("auxiliary footer button 'reset' is missing" in item for item in errors), errors)

    def test_runtime_host_marker_removed_fails(self) -> None:
        contents = self.replace_once(
            VIEW3D_HOST,
            'm_xTabControl->append_page(u"geometry"_ustr',
            'm_xTabControl->append_page(u"geometry-removed"_ustr',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any("host marker occurs 0 times" in item for item in errors), errors)

    def test_conditional_page_host_marker_removed_fails(self) -> None:
        contents = self.replace_once(
            SHAPE_PARAGRAPH_HOST,
            'AddTabPage(u"asian"_ustr',
            'AddTabPage(u"asian-removed"_ustr',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any(SHAPE_PARAGRAPH in item and "host marker occurs 0 times" in item for item in errors), errors)

    def test_shared_branch_host_marker_removed_fails(self) -> None:
        contents = self.replace_once(
            BORDER_HOST,
            'u"BorderAreaTransparencyDialog"_ustr',
            'u"BorderAreaTransparencyDialogRemoved"_ustr',
        )
        errors = self.failures(contents=contents)
        self.assertTrue(any(BORDER_AREA in item and "host marker occurs 0 times" in item for item in errors), errors)

    def test_runtime_host_marker_order_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        markers = self.shell(registry, VIEW3D)["host"]["ordered_markers"]
        markers[2], markers[4] = markers[4], markers[2]
        errors = self.failures(registry=registry)
        self.assertTrue(any("host markers are out of declared order" in item for item in errors), errors)

    def test_bounded_host_region_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self.shell(registry, FORMAT_SECTION)["host"]["region_end"] = "missing region end"
        errors = self.failures(registry=registry)
        self.assertTrue(any(FORMAT_SECTION in item and "host region bounds" in item for item in errors), errors)

    def test_ledger_family_drift_fails(self) -> None:
        ledger = copy.deepcopy(self.ledger)
        self.ledger_row(ledger, VIEW3D)["family"] = "dialog"
        errors = self.failures(ledger=ledger)
        self.assertTrue(any("ledger family" in item and "runtime-dialog-shell" in item for item in errors), errors)

    def test_uncontracted_runtime_family_row_fails(self) -> None:
        ledger = copy.deepcopy(self.ledger)
        extra = next(
            item
            for item in ledger["surfaces"]
            if item["surface"] not in VALIDATOR.EXPECTED_SURFACES
        )
        extra["family"] = "runtime-dialog-shell"
        extra["rewrite_class"] = "dialog-composition"
        errors = self.failures(ledger=ledger)
        self.assertTrue(
            any("runtime-dialog-shell surface set drifted" in item for item in errors), errors
        )

    def test_rewritten_row_must_cite_contract_marker(self) -> None:
        ledger = copy.deepcopy(self.ledger)
        row = self.ledger_row(ledger, VIEW3D)
        row["rewrite_status"] = "rewritten-material"
        row["rewrite_evidence"] = {
            "commit": "a" * 40,
            "contract": VALIDATOR.REGISTRY_PATH,
            "capture": {"sample_batch": "source-composition", "captured": False, "scene": None},
            "anatomy_markers": {
                "evidence_kind": "composition-code",
                "contract_marker": "wrong-marker",
            },
        }
        errors = self.failures(ledger=ledger)
        self.assertTrue(any("lost the composition marker" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
