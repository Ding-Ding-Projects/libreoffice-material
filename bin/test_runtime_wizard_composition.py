#!/usr/bin/env python3
"""Mutation tests for the runtime Material wizard composition contract."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-runtime-wizard-composition.py"
SPEC = importlib.util.spec_from_file_location("runtime_wizard_contract", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class RuntimeWizardCompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract, cls.contents = VALIDATOR.load_repository(REPOSITORY)

    def errors(self, *, contract=None, contents=None) -> list[str]:
        return VALIDATOR.violations(
            copy.deepcopy(self.contract if contract is None else contract),
            copy.deepcopy(self.contents if contents is None else contents),
        )

    def test_production_contract(self) -> None:
        self.assertEqual([], self.errors())

    def test_legacy_border_width_fails(self) -> None:
        contents = copy.deepcopy(self.contents)
        path = "vcl/uiconfig/ui/wizard.ui"
        contents[path] = contents[path].replace(
            '<property name="modal">True</property>',
            '<property name="border-width">6</property>\n    <property name="modal">True</property>',
        )
        self.assertTrue(any("border-width" in error for error in self.errors(contents=contents)))

    def test_missing_page_margin_fails(self) -> None:
        contents = copy.deepcopy(self.contents)
        path = "vcl/source/app/salvtables.cxx"
        contents[path] = contents[path].replace("xGrid->set_margin_bottom(*oSpacing);", "")
        self.assertTrue(any("margin_bottom" in error for error in self.errors(contents=contents)))

    def test_primary_action_drift_fails(self) -> None:
        contents = copy.deepcopy(self.contents)
        path = "vcl/source/control/roadmapwizard.cxx"
        contents[path] = contents[path].replace(
            "m_pNextPage->setAction(true);", "m_pNextPage->setAction(false);"
        )
        self.assertTrue(any("setAction" in error for error in self.errors(contents=contents)))

    def test_spacing_metric_drift_fails(self) -> None:
        contents = copy.deepcopy(self.contents)
        path = "vcl/uiconfig/theme_definitions/material/definition.xml"
        contents[path] = contents[path].replace(
            '<metric name="space-list-entry" value="12"/>',
            '<metric name="space-list-entry" value="13"/>',
        )
        self.assertTrue(any("spacing metric" in error for error in self.errors(contents=contents)))

    def test_runtime_claim_fails_closed(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in error for error in self.errors(contract=contract)))


if __name__ == "__main__":
    unittest.main()
