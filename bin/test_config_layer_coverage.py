#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the config-layer coverage contract.

Each mutation weakens one guarantee -- an unregistered new command XML, a
registered file that vanished, a disappeared named contract/checker, a count
drift, an ungrounded or mis-attributed toolbar satisfied-claim, a demoted blanket
family, a cross-family duplicate, a satisfied/pending overlap, or a drifted
classifier -- and asserts the checker fails closed on it. A green baseline proves
the production tree currently passes, and the honest satisfied set (6 grounded
toolbar pins, all menus/statusbars satisfied at the chrome level) is pinned.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-config-layer-coverage.py"
SPEC = importlib.util.spec_from_file_location("check_config_layer_coverage", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

EXPECTED_TOOLBAR_PINS = {
    "chart2/uiconfig/toolbar/toolbar.xml": "chart-editor",
    "sc/uiconfig/scalc/toolbar/formatobjectbar.xml": "calc-chrome",
    "sc/uiconfig/scalc/toolbar/standardbar.xml": "calc-chrome",
    "sw/uiconfig/swriter/toolbar/changes.xml": "writer-review-composition",
    "sw/uiconfig/swriter/toolbar/standardbar.xml": "writer-chrome",
    "sw/uiconfig/swriter/toolbar/textobjectbar.xml": "writer-chrome",
}


class ConfigLayerCoverageContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = VALIDATOR.load_registry(REPOSITORY)
        self.live = VALIDATOR.enumerate_live(REPOSITORY)
        self.pins = VALIDATOR.derive_toolbar_pins(REPOSITORY)
        self.exists = lambda rel: (REPOSITORY / rel).is_file()

    def failures(self, *, registry=None, live=None, pins=None, exists=None) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry,
            self.live if live is None else live,
            self.pins if pins is None else pins,
            self.exists if exists is None else exists,
        )

    def assertFailsWith(self, needle: str, **kwargs) -> None:
        errors = self.failures(**kwargs)
        self.assertTrue(
            any(needle in error for error in errors),
            msg=f"expected an error containing {needle!r}; got {errors}",
        )

    def mutated(self) -> dict:
        return copy.deepcopy(self.registry)

    def mutated_live(self) -> dict:
        return {family: list(members) for family, members in self.live.items()}

    # -- baselines ---------------------------------------------------------
    def test_production_contract_passes(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    def test_registry_counts_match_live_tree(self) -> None:
        total = sum(len(members) for members in self.live.values())
        self.assertEqual(self.registry["counts"]["total"], total)

    def test_honest_toolbar_pins_are_grounded(self) -> None:
        # The satisfied toolbar set is exactly the 6 grounded chrome-contract pins.
        self.assertEqual(
            {path: meta[0] for path, meta in self.pins.items()},
            EXPECTED_TOOLBAR_PINS,
        )
        satisfied = {
            entry["file"]: entry["pinned_by"]
            for entry in self.registry["families"]["toolbar"]["satisfied"]
        }
        self.assertEqual(satisfied, EXPECTED_TOOLBAR_PINS)

    def test_menu_and_statusbar_families_fully_satisfied(self) -> None:
        for family in ("popupmenu", "menubar", "statusbar"):
            block = self.registry["families"][family]
            self.assertEqual(block["status"], "satisfied")
            self.assertEqual(block["count"], len(block["files"]))

    # -- file-set drift ----------------------------------------------------
    def test_new_command_xml_unregistered_fails(self) -> None:
        live = self.mutated_live()
        live["toolbar"].append("sc/uiconfig/scalc/toolbar/zz-phantom.xml")
        self.assertFailsWith("live command XML not registered", live=live)

    def test_registered_file_vanished_fails(self) -> None:
        live = self.mutated_live()
        live["menubar"].pop()
        self.assertFailsWith("registered command XML no longer in tree", live=live)

    def test_family_misfile_fails(self) -> None:
        registry = self.mutated()
        # move a toolbar path into the statusbar family list
        toolbar_path = registry["families"]["toolbar"]["pending"][0]
        registry["families"]["statusbar"]["files"].append(toolbar_path)
        self.assertFailsWith("mis-filed", registry=registry)

    def test_cross_family_duplicate_fails(self) -> None:
        registry = self.mutated()
        stat = registry["families"]["statusbar"]["files"][0]
        registry["families"]["menubar"]["files"].append(stat)
        self.assertFailsWith("duplicate:", registry=registry)

    # -- named-contract disappearance -------------------------------------
    def test_blanket_mechanism_contract_missing_fails(self) -> None:
        target = "qa/windows-ui-contract/menu-composition.json"
        exists = lambda rel: False if rel == target else self.exists(rel)
        self.assertFailsWith("named-contract", exists=exists)

    def test_toolbar_pin_checker_missing_fails(self) -> None:
        target = "bin/check-calc-chrome-contract.py"
        exists = lambda rel: False if rel == target else self.exists(rel)
        self.assertFailsWith("checker missing on disk", exists=exists)

    # -- counts ------------------------------------------------------------
    def test_total_count_drift_fails(self) -> None:
        registry = self.mutated()
        registry["counts"]["total"] = registry["counts"]["total"] + 1
        self.assertFailsWith("counts:total", registry=registry)

    def test_by_status_drift_fails(self) -> None:
        registry = self.mutated()
        registry["counts"]["by_status"]["satisfied"] += 1
        self.assertFailsWith("counts:by_status", registry=registry)

    def test_toolbar_satisfied_count_drift_fails(self) -> None:
        registry = self.mutated()
        registry["families"]["toolbar"]["satisfied_count"] = 99
        self.assertFailsWith("satisfied_count", registry=registry)

    # -- toolbar grounding -------------------------------------------------
    def test_ungrounded_satisfied_claim_fails(self) -> None:
        # The registry claims a toolbar is satisfied, but no contract pins it.
        pins = dict(self.pins)
        victim = next(iter(pins))
        del pins[victim]
        self.assertFailsWith("no named contract pins it", pins=pins)

    def test_unlisted_real_pin_fails(self) -> None:
        # A contract pins a toolbar the registry forgot to list satisfied.
        pins = dict(self.pins)
        pins["sw/uiconfig/swriter/toolbar/alignmentbar.xml"] = (
            "writer-chrome",
            "qa/windows-ui-contract/writer-chrome.json",
            "bin/check-writer-chrome-contract.py",
        )
        self.assertFailsWith("not listed satisfied", pins=pins)

    def test_misattributed_pin_fails(self) -> None:
        pins = dict(self.pins)
        victim = next(iter(pins))
        _, contract, checker = pins[victim]
        pins[victim] = ("wrong-contract", contract, checker)
        self.assertFailsWith("attribution", pins=pins)

    def test_satisfied_pending_overlap_fails(self) -> None:
        registry = self.mutated()
        sat_file = registry["families"]["toolbar"]["satisfied"][0]["file"]
        registry["families"]["toolbar"]["pending"].append(sat_file)
        self.assertFailsWith("both satisfied and pending", registry=registry)

    # -- blanket-family demotion + structural header -----------------------
    def test_blanket_family_demoted_fails(self) -> None:
        registry = self.mutated()
        registry["families"]["popupmenu"]["status"] = "pending"
        self.assertFailsWith("must be status=satisfied", registry=registry)

    def test_blanket_wrong_mechanism_fails(self) -> None:
        registry = self.mutated()
        registry["families"]["statusbar"]["mechanism"] = "menu-composition"
        self.assertFailsWith("mechanism must be statusbar-composition", registry=registry)

    def test_classifier_drift_fails(self) -> None:
        registry = self.mutated()
        registry["glob"]["classifier"] = "nonsense"
        self.assertFailsWith("classifier drifted", registry=registry)

    def test_runtime_verified_true_fails(self) -> None:
        registry = self.mutated()
        registry["runtime_verified"] = True
        self.assertFailsWith("runtime_verified", registry=registry)

    def test_wrong_contract_id_fails(self) -> None:
        registry = self.mutated()
        registry["contract"] = "something-else"
        self.assertFailsWith("registry:contract", registry=registry)


if __name__ == "__main__":
    unittest.main()
