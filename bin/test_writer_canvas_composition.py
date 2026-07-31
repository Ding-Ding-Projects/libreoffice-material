#!/usr/bin/env python3
"""Mutation regressions for the Material Writer canvas contract."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-writer-canvas-composition.py"
SPEC = importlib.util.spec_from_file_location("check_writer_canvas_composition", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

DEFINITION = "vcl/uiconfig/theme_definitions/material/definition.xml"
HEADER = "sw/inc/viewsh.hxx"
VIEW = "sw/source/core/view/viewsh.cxx"
PAINT = "sw/source/core/layout/paintfrm.cxx"


class WriterCanvasCompositionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract, self.contents = VALIDATOR.load_repository(REPOSITORY)

    def failures(self, contract=None, contents=None) -> list[str]:
        return VALIDATOR.violations(
            self.contract if contract is None else contract,
            self.contents if contents is None else contents,
        )

    def changed(self, path: str, text: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents[path] = text
        return contents

    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)

    def test_contract_marker_drift_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["contract"] = "wrong"
        self.assertTrue(any("contract:marker" in e for e in self.failures(contract=contract)))

    def test_runtime_claim_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in e for e in self.failures(contract=contract)))

    def test_dark_palette_token_removed_fails(self) -> None:
        definition = self.contents[DEFINITION].replace(
            '<color name="surface-container-low" value="#1D1B20"/>', "", 1
        )
        self.assertTrue(
            any("canvas token missing" in e for e in self.failures(contents=self.changed(DEFINITION, definition)))
        )

    def test_high_contrast_order_drift_fails(self) -> None:
        source = self.contents[VIEW].replace(
            "if (rStyleSettings.GetHighContrastMode())\n        return false;",
            "if (false)\n        return false;",
            1,
        )
        self.assertTrue(any("viewsh:guard" in e for e in self.failures(contents=self.changed(VIEW, source))))

    def test_exact_material_gate_removed_fails(self) -> None:
        source = self.contents[VIEW].replace(
            'std::strcmp(pThemeName, "material") == 0', "pThemeName != nullptr", 1
        )
        self.assertTrue(any("missing marker" in e for e in self.failures(contents=self.changed(VIEW, source))))

    def test_canvas_token_consumer_removed_fails(self) -> None:
        source = self.contents[VIEW].replace(
            'findColor("surface-container-low")', 'findColor("surface")', 1
        )
        self.assertTrue(any("missing marker" in e for e in self.failures(contents=self.changed(VIEW, source))))

    def test_page_subtraction_removed_fails(self) -> None:
        source = self.contents[VIEW].replace("aRegion -= aPageRect", "aRegion.clear()", 1)
        self.assertTrue(any("page subtraction" in e or "missing marker" in e for e in self.failures(contents=self.changed(VIEW, source))))

    def test_bitmap_guard_removed_fails(self) -> None:
        source = self.contents[VIEW].replace(
            "if (!IsMaterialWriterCanvasEnabled()\n"
            "        && DrawAppBackgroundBitmap(GetOut(), rRegion.GetOrigin()))",
            "if (DrawAppBackgroundBitmap(GetOut(), rRegion.GetOrigin()))",
            1,
        )
        self.assertTrue(any("missing marker" in e or "desktop-fill" in e for e in self.failures(contents=self.changed(VIEW, source))))

    def test_document_paint_order_drift_fails(self) -> None:
        source = self.contents[VIEW].replace(
            "PaintDesktop(rRenderContext, aRect);",
            "GetLayout()->PaintSwFrame( rRenderContext, aRect );",
            1,
        )
        self.assertTrue(any("viewsh:paint" in e or "missing marker" in e for e in self.failures(contents=self.changed(VIEW, source))))

    def test_shadow_seam_consumer_removed_fails(self) -> None:
        source = self.contents[PAINT].replace(
            "pViewShell->GetCanvasBackgroundColor()",
            "SwViewOption::GetCurrentViewOptions().GetAppBackgroundColor()",
            1,
        )
        self.assertTrue(any("shadow seam" in e or "missing marker" in e for e in self.failures(contents=self.changed(PAINT, source))))

    def test_header_contract_removed_fails(self) -> None:
        source = self.contents[HEADER].replace("Color GetCanvasBackgroundColor() const;", "", 1)
        self.assertTrue(any("missing marker" in e for e in self.failures(contents=self.changed(HEADER, source))))

    def test_preserved_path_removed_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["preserved_paths"].pop()
        self.assertTrue(any("preserved_paths" in e for e in self.failures(contract=contract)))


if __name__ == "__main__":
    unittest.main()
