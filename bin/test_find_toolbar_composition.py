#!/usr/bin/env python3
"""Mutation tests for the native Material Find toolbar composition."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-find-toolbar-composition.py"
SPEC = importlib.util.spec_from_file_location("find_toolbar_contract", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class FindToolbarCompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract, cls.contents = VALIDATOR.load_repository(REPOSITORY)

    def errors(self, *, contract=None, contents=None) -> list[str]:
        return VALIDATOR.violations(
            copy.deepcopy(self.contract if contract is None else contract),
            copy.deepcopy(self.contents if contents is None else contents),
        )

    def mutate_source(self, path: str, old: str, new: str) -> dict[str, str]:
        contents = copy.deepcopy(self.contents)
        self.assertIn(old, contents[path])
        contents[path] = contents[path].replace(old, new, 1)
        return contents

    def test_production_contract(self) -> None:
        self.assertEqual([], self.errors())

    def test_runtime_claim_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in error for error in self.errors(contract=contract)))

    def test_source_hash_drift_fails(self) -> None:
        contents = copy.deepcopy(self.contents)
        contents["svx/source/inc/findtextfield.hxx"] += "\n// mutation\n"
        self.assertTrue(any("sha256 drift" in error for error in self.errors(contents=contents)))

    def test_hidden_empty_label_fails(self) -> None:
        contents = self.mutate_source(
            "svx/uiconfig/ui/findbox.ui",
            "  </object>\n</interface>",
            '    <child><object class="GtkLabel" id="fake"><property name="no-show-all">True</property></object></child>\n  </object>\n</interface>',
        )
        self.assertTrue(any("empty hidden label" in error for error in self.errors(contents=contents)))

    def test_detached_builder_fails(self) -> None:
        contents = self.mutate_source(
            "svx/uiconfig/ui/findbox.ui",
            '<property name="position">1</property>',
            '<property name="position">9</property>',
        )
        self.assertTrue(any("sha256 drift" in error for error in self.errors(contents=contents)))

    def test_builder_accessible_name_fails(self) -> None:
        contents = self.mutate_source(
            "svx/uiconfig/ui/findbox.ui",
            '<property name="AtkObject::accessible-name" translatable="yes" context="findbox|find_regex_builder-atkobject">',
            '<property name="AtkObject::removed-name" translatable="yes" context="findbox|find_regex_builder-atkobject">',
        )
        self.assertTrue(any("accessible name missing" in error for error in self.errors(contents=contents)))

    def test_missing_invalid_pattern_guard_fails(self) -> None:
        contents = self.mutate_source(
            "svx/source/tbxctrls/tbunosearchcontrollers.cxx",
            "if (!sfx2::RegexSearchService::Validate(rState).IsValid)",
            "if (false)",
        )
        self.assertTrue(any("Validate" in error for error in self.errors(contents=contents)))

    def test_hard_coded_algorithm_fails(self) -> None:
        contents = self.mutate_source(
            "svx/source/tbxctrls/tbunosearchcontrollers.cxx",
            'css::uno::Any( aSearchOptions.AlgorithmType2 )',
            'css::uno::Any( sal_Int16(css::util::SearchAlgorithms2::ABSOLUTE) )',
        )
        self.assertTrue(any("hard-codes literal" in error or "AlgorithmType2" in error for error in self.errors(contents=contents)))

    def test_match_case_state_sync_fails(self) -> None:
        contents = self.mutate_source(
            "svx/source/tbxctrls/tbunosearchcontrollers.cxx",
            "pFindControl->set_match_case(bMatchCase);",
            "pFindControl->set_match_case(false);",
        )
        self.assertTrue(any("case-toolbar-authority" in error for error in self.errors(contents=contents)))

    def test_direct_changed_callback_fails(self) -> None:
        contents = self.mutate_source(
            "svx/source/tbxctrls/tbunosearchcontrollers.cxx",
            "m_aChangeHdl = rLink;",
            "m_aChangeHdl = rLink;\n    m_xWidget->connect_changed(rLink);",
        )
        self.assertTrue(any("bypasses shared controller" in error for error in self.errors(contents=contents)))

    def test_dependency_gap_regression_fails(self) -> None:
        contents = copy.deepcopy(self.contents)
        path = "qa/windows-ui-contract/search-field-coverage.json"
        registry = json.loads(contents[path])
        entry = next(item for item in registry["shipping_fields"] if item["coverage_id"] == "document.find-bar")
        entry["integration_status"] = "gap"
        contents[path] = json.dumps(registry)
        self.assertTrue(any("lost source-integrated" in error for error in self.errors(contents=contents)))


if __name__ == "__main__":
    unittest.main()
