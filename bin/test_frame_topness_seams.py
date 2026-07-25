#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions proving the frame-topness seam checker fails closed.

Each mutation weakens the registry -- drop a known seam (drift-out), invent a seam that is
absent from the tree (drift-in), flip an entry to 'unaudited', corrupt a per-family or
grand total, or promote runtime_verified -- and asserts the checker rejects it. A green
baseline proves the production tree currently passes. The greps run against the real tree
via ``violations(registry, REPOSITORY)``; only the in-memory registry is mutated.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-frame-topness-seams.py"
SPEC = importlib.util.spec_from_file_location("check_frame_topness_seams", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class FrameTopnessSeamContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = VALIDATOR.load_registry(REPOSITORY)

    def failures(self, registry: dict | None = None) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry, REPOSITORY
        )

    def _family(self, registry: dict, api: str) -> dict:
        for family in registry["families"]:
            if family["api"] == api:
                return family
        raise AssertionError(f"family {api} not found")

    # -- baseline ----------------------------------------------------------
    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    # -- the required crash-on-null seams are actually inventoried ---------
    def test_vba_workwork_crash_risk_flagged(self) -> None:
        family = self._family(self.registry, "static_cast_WorkWindow")
        risky = [e for e in family["entries"] if e.get("crash_on_null_risk")]
        self.assertTrue(risky, "the sw/sc vbawindow static_cast<WorkWindow*> seams must be "
                        "flagged crash_on_null_risk")
        self.assertEqual(4, family["total"])

    # -- drift-out: a removed registry entry fails ------------------------
    def test_removed_seam_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        family = self._family(registry, "GetSystemWindow")
        dropped = family["entries"].pop(0)
        family["total"] -= dropped["count"]
        registry["grand_total_call_sites"] -= dropped["count"]
        errors = self.failures(registry)
        self.assertTrue(any("DRIFT (unregistered topness seam)" in e for e in errors), errors)

    def test_decremented_count_fails(self) -> None:
        # A seam that occurs 2x in the tree recorded as 1x must fail drift-in.
        registry = copy.deepcopy(self.registry)
        family = self._family(registry, "static_cast_WorkWindow")
        entry = next(e for e in family["entries"] if e["count"] == 2)
        entry["count"] = 1
        family["total"] -= 1
        registry["grand_total_call_sites"] -= 1
        errors = self.failures(registry)
        self.assertTrue(any("DRIFT (unregistered topness seam)" in e for e in errors), errors)

    # -- drift-in: a fake seam not in the tree fails ----------------------
    def test_fake_seam_not_in_tree_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        family = self._family(registry, "createTask")
        family["entries"].append({
            "file": "framework/source/services/desktop.cxx",
            "snippet": "xTarget = aCreator.createTask(SOME_FICTIONAL_TARGET, {});",
            "count": 1,
            "classification": "host-owned",
            "note": "fabricated seam that does not exist in the tree",
        })
        family["total"] += 1
        registry["grand_total_call_sites"] += 1
        errors = self.failures(registry)
        self.assertTrue(any("STALE registry entry" in e for e in errors), errors)

    # -- unaudited classification fails closed ----------------------------
    def test_unaudited_classification_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        family = self._family(registry, "GetSystemWindow")
        family["entries"][0]["classification"] = "unaudited"
        errors = self.failures(registry)
        self.assertTrue(any("classified 'unaudited'" in e for e in errors), errors)

    def test_unknown_classification_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        family = self._family(registry, "SetMenuBar")
        family["entries"][0]["classification"] = "probably-fine"
        errors = self.failures(registry)
        self.assertTrue(any("unknown classification" in e for e in errors), errors)

    # -- total pins --------------------------------------------------------
    def test_family_total_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        self._family(registry, "getTopSystemWindow")["total"] = 999
        errors = self.failures(registry)
        self.assertTrue(any("recorded total 999" in e for e in errors), errors)

    def test_grand_total_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["grand_total_call_sites"] = 1
        errors = self.failures(registry)
        self.assertTrue(any("grand_total_call_sites 1" in e for e in errors), errors)

    # -- registry integrity ------------------------------------------------
    def test_runtime_verified_true_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["runtime_verified"] = True
        errors = self.failures(registry)
        self.assertTrue(any("runtime_verified" in e for e in errors), errors)

    def test_contract_name_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["contract"] = "something-else"
        errors = self.failures(registry)
        self.assertIn("registry:contract:unexpected value", errors)

    def test_status_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["status"] = "runtime-verified"
        errors = self.failures(registry)
        self.assertIn("registry:status:must be static-inventory", errors)


if __name__ == "__main__":
    unittest.main()
