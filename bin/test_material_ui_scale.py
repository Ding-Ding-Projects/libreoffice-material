#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material UI-scale contract.

Each mutation weakens exactly one guarantee -- a drifted schema type/default/bound, a
removed adjustment or widget id inside the frame, a lost label mnemonic, a one-directional
controller round-trip (read-only or write-only), a missing header member, or a promoted
stored-only / runtime_verified flag -- and asserts the checker fails closed. A green
baseline proves the production tree currently passes.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-material-ui-scale.py"
SPEC = importlib.util.spec_from_file_location("check_material_ui_scale", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class MaterialUiScaleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, self.contents = VALIDATOR.load_repository(REPOSITORY)
        self.SCHEMA = self.registry["schema_source"]
        self.UI = self.registry["ui_source"]
        self.CONTROLLER = self.registry["controller_source"]
        self.HEADER = self.registry["controller_header"]

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

    # -- schema ------------------------------------------------------------
    def test_schema_type_drift_fails(self) -> None:
        source = self.contents[self.SCHEMA].replace(
            '<prop oor:name="MaterialUiScale" oor:type="xs:short"',
            '<prop oor:name="MaterialUiScale" oor:type="xs:int"',
            1,
        )
        errors = self.failures(contents=self.with_content(self.SCHEMA, source))
        self.assertTrue(
            any("property:MaterialUiScale:schema is not oor:type" in e for e in errors), errors
        )

    def test_schema_default_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["property"]["default"] = "125"
        errors = self.failures(registry=registry)
        self.assertTrue(
            any("property:MaterialUiScale:schema default drifted" in e for e in errors), errors
        )

    def test_schema_min_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["property"]["min_inclusive"] = "0"
        errors = self.failures(registry=registry)
        self.assertTrue(
            any("property:MaterialUiScale:schema minInclusive drifted" in e for e in errors),
            errors,
        )

    def test_schema_max_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["property"]["max_inclusive"] = "500"
        errors = self.failures(registry=registry)
        self.assertTrue(
            any("property:MaterialUiScale:schema maxInclusive drifted" in e for e in errors),
            errors,
        )

    def test_schema_prop_removed_fails(self) -> None:
        source = self.contents[self.SCHEMA].replace(
            'oor:name="MaterialUiScale"', 'oor:name="Gone"', 1
        )
        errors = self.failures(contents=self.with_content(self.SCHEMA, source))
        self.assertTrue(
            any("property:MaterialUiScale:not found" in e for e in errors), errors
        )

    # -- widget ------------------------------------------------------------
    def test_adjustment_removed_fails(self) -> None:
        source = self.contents[self.UI].replace('id="uiscaleadjustment"', 'id="gone"', 1)
        errors = self.failures(contents=self.with_content(self.UI, source))
        self.assertTrue(any("widget:adjustment id='uiscaleadjustment' not found" in e for e in errors), errors)

    def test_adjustment_bound_drift_fails(self) -> None:
        source = self.contents[self.UI].replace(
            '<property name="upper">400</property>', '<property name="upper">999</property>', 1
        )
        errors = self.failures(contents=self.with_content(self.UI, source))
        self.assertTrue(any("widget:adjustment upper drifted" in e for e in errors), errors)

    def test_spin_removed_from_frame_fails(self) -> None:
        source = self.contents[self.UI].replace('id="uiscalespin"', 'id="uiscalespinZ"')
        errors = self.failures(contents=self.with_content(self.UI, source))
        self.assertTrue(
            any("widget:spin id='uiscalespin' not found inside" in e for e in errors), errors
        )

    def test_label_mnemonic_removed_fails(self) -> None:
        source = self.contents[self.UI].replace(
            '<property name="mnemonic-widget">uiscalespin</property>',
            '<property name="mnemonic-widget">materialaccent</property>',
            1,
        )
        errors = self.failures(contents=self.with_content(self.UI, source))
        self.assertTrue(
            any("does not mnemonic-widget the spin" in e for e in errors), errors
        )

    # -- controller round-trip --------------------------------------------
    def test_controller_read_removed_fails(self) -> None:
        source = self.contents[self.CONTROLLER].replace("m_xMaterialUiScale->set_value(", "m_xMaterialUiScale->skip_value(")
        errors = self.failures(contents=self.with_content(self.CONTROLLER, source))
        self.assertTrue(any("controller:READ marker" in e for e in errors), errors)

    def test_controller_write_removed_fails(self) -> None:
        source = self.contents[self.CONTROLLER].replace(
            "officecfg::Office::Common::Appearance::MaterialUiScale::set(",
            "officecfg::Office::Common::Appearance::MaterialUiScale::skip(",
            1,
        )
        errors = self.failures(contents=self.with_content(self.CONTROLLER, source))
        self.assertTrue(any("controller:WRITE marker" in e for e in errors), errors)

    def test_weld_binding_removed_fails(self) -> None:
        source = self.contents[self.CONTROLLER].replace(
            'weld_spin_button(u"uiscalespin"', 'weld_spin_button(u"gone"', 1
        )
        errors = self.failures(contents=self.with_content(self.CONTROLLER, source))
        self.assertTrue(any("controller:weld binding" in e for e in errors), errors)

    # -- header ------------------------------------------------------------
    def test_header_marker_missing_fails(self) -> None:
        source = self.contents[self.HEADER].replace("m_xMaterialUiScale", "m_xRenamed")
        errors = self.failures(contents=self.with_content(self.HEADER, source))
        self.assertTrue(any("header:marker 'm_xMaterialUiScale' missing" in e for e in errors), errors)

    # -- registry integrity (honest stored-only carve-out) -----------------
    def test_runtime_verified_true_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["runtime_verified"] = True
        errors = self.failures(registry=registry)
        self.assertTrue(any("runtime_verified:no runtime evidence" in e for e in errors), errors)

    def test_stored_only_false_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["stored_only"] = False
        errors = self.failures(registry=registry)
        self.assertTrue(
            any("stored_only:the UI-scale factor is not consumed" in e for e in errors), errors
        )

    def test_apply_stage_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["apply_stage"] = "live"
        errors = self.failures(registry=registry)
        self.assertTrue(any("registry:apply_stage:must be 'restart'" in e for e in errors), errors)

    def test_contract_name_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["contract"] = "something-else"
        errors = self.failures(registry=registry)
        self.assertTrue(any("registry:contract:" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
