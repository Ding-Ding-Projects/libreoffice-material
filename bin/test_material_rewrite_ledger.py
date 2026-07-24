#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material-rewrite burn-down ledger.

Each test perturbs a copy of the production ledger and asserts the fail-closed
gate rejects it: status regression, digest mismatch, family misclassification,
phantom/dropped row, and anatomy/predicate tampering (static and composition).
The production ledger must pass untouched.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-material-rewrite-ledger.py"
LEDGER_PATH = REPOSITORY / "qa/windows-ui-contract/material-rewrite-ledger.json"

_SPEC = importlib.util.spec_from_file_location("check_material_rewrite_ledger", VALIDATOR_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
CK = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = CK
_SPEC.loader.exec_module(CK)


class LedgerMutationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ledger = CK.read_ledger(LEDGER_PATH)
        cls._registry, cls.digest, cls.attribution = CK.fresh_closure(REPOSITORY)

    # -- helpers -----------------------------------------------------------
    def fresh(self):
        lg = copy.deepcopy(self.ledger)
        return lg, CK._ledger_rows(lg)

    def a_row(self, status=None, family=None):
        for row in self.ledger["surfaces"]:
            if status is not None and row["rewrite_status"] != status:
                continue
            if family is not None and row["family"] != family:
                continue
            return row["surface"]
        raise AssertionError(f"no row with status={status} family={family}")

    def rewritten_static_surface(self):
        for row in self.ledger["surfaces"]:
            if row["rewrite_status"] == CK.REWRITTEN and CK.evidence_kind_for(
                row["family"]
            ) == CK.STATIC_UI:
                return row["surface"]
        raise AssertionError("no rewritten static-ui row")

    def rewritten_composition_surface(self):
        for row in self.ledger["surfaces"]:
            if row["rewrite_status"] == CK.REWRITTEN and CK.evidence_kind_for(
                row["family"]
            ) == CK.COMPOSITION_CODE:
                return row["surface"]
        raise AssertionError("no rewritten composition-code row")

    def write_temp(self, ledger) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="mrl_")) / "material-rewrite-ledger.json"
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(CK.serialize_ledger(ledger))
        return tmp

    # -- production baseline ----------------------------------------------
    def test_production_passes(self) -> None:
        CK.validate(REPOSITORY, LEDGER_PATH)  # must not raise

    def test_production_family_counts(self) -> None:
        by_family = self.ledger["coverage"]["by_family"]
        expected = {
            "dialog": 521, "message-dialog": 76, "options-page": 40,
            "panel-fragment": 451, "menu": 70, "popover": 47,
            "sidebar-panel": 54, "wizard-assistant": 1, "native-shell": 10,
        }
        for fam, count in expected.items():
            self.assertEqual(by_family[fam]["total"], count, fam)
        self.assertEqual(self.ledger["coverage"]["total_surfaces"], 1270)

    # -- C3 status regression ---------------------------------------------
    def test_status_regression_rejected(self) -> None:
        _lg, rows = self.fresh()
        pending_surface = self.a_row(status=CK.PENDING)
        baseline = {"surfaces": [{"surface": pending_surface, "rewrite_status": CK.REWRITTEN}]}
        failures, warnings = [], []
        CK._validate_status_regression(rows, baseline, failures, warnings)
        self.assertTrue(any("C3 status regression" in f and pending_surface in f for f in failures), failures)

    def test_status_regression_waiver_downgrades_to_warning(self) -> None:
        lg, rows = self.fresh()
        pending_surface = self.a_row(status=CK.PENDING)
        rows[pending_surface]["regression_waiver"] = {"reason": "surface deleted upstream", "commit": "a" * 40}
        baseline = {"surfaces": [{"surface": pending_surface, "rewrite_status": CK.REWRITTEN}]}
        failures, warnings = [], []
        CK._validate_status_regression(rows, baseline, failures, warnings)
        self.assertEqual([], failures)
        self.assertTrue(any("C3 WARN" in w for w in warnings), warnings)

    def test_status_regression_full_validate_rejected(self) -> None:
        # integration: a committed-like baseline higher than the mutated ledger
        lg, rows = self.fresh()
        target = self.rewritten_composition_surface()
        rows[target]["rewrite_status"] = CK.PENDING
        rows[target]["rewrite_evidence"] = CK._null_evidence()
        lg["coverage"] = CK.compute_coverage(lg["surfaces"])
        tmp = self.write_temp(lg)
        # baseline injected via monkeypatch of the git-show loader
        original = CK.load_committed_baseline
        CK.load_committed_baseline = lambda repo, path: self.ledger
        try:
            with self.assertRaises(CK.ValidationError) as ctx:
                CK.validate(REPOSITORY, tmp)
            self.assertIn("C3 status regression", str(ctx.exception))
        finally:
            CK.load_committed_baseline = original

    # -- C1 digest / parity -----------------------------------------------
    def test_digest_mismatch_rejected(self) -> None:
        lg, _rows = self.fresh()
        lg["closure_registry_digest"] = "sha256:" + "0" * 64
        tmp = self.write_temp(lg)
        with self.assertRaises(CK.ValidationError) as ctx:
            CK.validate(REPOSITORY, tmp)
        self.assertIn("closure_registry_digest", str(ctx.exception))

    def test_phantom_row_rejected(self) -> None:
        _lg, rows = self.fresh()
        rows["made/up/surface.ui"] = {"surface": "made/up/surface.ui", "owner": "made", "inventory_id": "unassigned"}
        failures = []
        CK._validate_closure_parity(rows, self.attribution, failures)
        self.assertTrue(any("C1" in f and "not in the closure" in f for f in failures), failures)

    def test_dropped_row_rejected(self) -> None:
        _lg, rows = self.fresh()
        dropped = self.a_row(status=CK.PENDING)
        del rows[dropped]
        failures = []
        CK._validate_closure_parity(rows, self.attribution, failures)
        self.assertTrue(any("C1" in f and "missing from the ledger" in f for f in failures), failures)

    # -- C2 attribution ----------------------------------------------------
    def test_attribution_drift_rejected(self) -> None:
        _lg, rows = self.fresh()
        surface = self.a_row(status=CK.PENDING)
        rows[surface]["owner"] = "not-the-owner"
        failures = []
        CK._validate_attribution(rows, self.attribution, failures)
        self.assertTrue(any("C2 attribution" in f and surface in f for f in failures), failures)

    # -- C6 classifier -----------------------------------------------------
    def test_family_misclassification_rejected(self) -> None:
        _lg, rows = self.fresh()
        surface = self.a_row(family="dialog")
        rows[surface]["family"] = "menu"
        rows[surface]["rewrite_class"] = "menu-composition"
        failures = []
        CK._validate_classifier(REPOSITORY, rows, self.attribution, {}, failures)
        self.assertTrue(any("C6 classifier" in f and surface in f for f in failures), failures)

    # -- C4 anatomy persistence (static-ui) --------------------------------
    def test_static_snapshot_tampering_rejected(self) -> None:
        _lg, rows = self.fresh()
        surface = self.rewritten_static_surface()
        rows[surface]["rewrite_evidence"]["anatomy_markers"]["title_present"] = False
        failures = []
        CK._validate_anatomy_persistence(REPOSITORY, rows, {}, failures)
        self.assertTrue(any("C4 anatomy" in f and "markers changed" in f for f in failures), failures)

    def test_static_predicate_function_rejects_bad_footer(self) -> None:
        surface = self.rewritten_static_surface()
        markers = copy.deepcopy(
            next(r for r in self.ledger["surfaces"] if r["surface"] == surface)[
                "rewrite_evidence"
            ]["anatomy_markers"]
        )
        # break the destructive-variant safety: make the destructive action the Enter default
        markers["default_response"] = markers["primary_response"]
        ok, why = CK.static_predicate(CK.FAMILY_MESSAGE, markers)
        self.assertFalse(ok, why)

    # -- C4 anatomy persistence (composition-code) -------------------------
    def test_composition_marker_tampering_rejected(self) -> None:
        _lg, rows = self.fresh()
        surface = self.rewritten_composition_surface()
        rows[surface]["rewrite_evidence"]["anatomy_markers"]["contract_marker"] = "wrong-token"
        failures = []
        CK._validate_anatomy_persistence(REPOSITORY, rows, {}, failures)
        self.assertTrue(any("C4 composition" in f and "vanished" in f for f in failures), failures)

    def test_composition_missing_contract_rejected(self) -> None:
        _lg, rows = self.fresh()
        surface = self.rewritten_composition_surface()
        rows[surface]["rewrite_evidence"]["contract"] = "qa/windows-ui-contract/does-not-exist.json"
        failures = []
        CK._validate_anatomy_persistence(REPOSITORY, rows, {}, failures)
        self.assertTrue(any("C4 composition" in f and "does not exist" in f for f in failures), failures)

    # -- C5 evidence shape -------------------------------------------------
    def test_pending_with_evidence_rejected(self) -> None:
        surface = self.a_row(status=CK.PENDING)
        row = {"surface": surface, "rewrite_status": CK.PENDING,
               "rewrite_evidence": {"commit": "b" * 40, "contract": None, "capture": None, "anatomy_markers": {}}}
        failures = []
        CK._validate_evidence_shape(row, surface, failures)
        self.assertTrue(any("C5 evidence" in f for f in failures), failures)

    def test_rewritten_without_contract_rejected(self) -> None:
        surface = self.rewritten_composition_surface()
        row = copy.deepcopy(next(r for r in self.ledger["surfaces"] if r["surface"] == surface))
        row["rewrite_evidence"]["contract"] = None
        failures = []
        CK._validate_evidence_shape(row, surface, failures)
        self.assertTrue(any("C5 evidence" in f and "owning contract" in f for f in failures), failures)

    # -- C7 coverage -------------------------------------------------------
    def test_coverage_drift_rejected(self) -> None:
        lg, rows = self.fresh()
        lg["coverage"]["rewritten_material"] = 999
        failures = []
        CK._validate_coverage(lg, rows, failures)
        self.assertTrue(any("C7 coverage" in f for f in failures), failures)

    # -- acceptance-table tampering ---------------------------------------
    def test_family_defs_tampering_rejected(self) -> None:
        lg, _rows = self.fresh()
        # relax the message-dialog acceptance table (drop a required marker)
        lg["family_defs"]["message-dialog"]["required_markers"] = []
        failures = []
        CK._validate_acceptance_table(lg, failures)
        self.assertTrue(any("family_defs" in f for f in failures), failures)

    def test_command_surface_config_tampering_rejected(self) -> None:
        lg, _rows = self.fresh()
        lg["command_surface_config"]["counts"]["toolbar"] = 0
        failures = []
        CK._validate_acceptance_table(lg, failures)
        self.assertTrue(any("command_surface_config" in f for f in failures), failures)

    # -- soft wave budget guard (WARN-only) -------------------------------
    def test_wave_budget_over_cap_warns_not_fails(self) -> None:
        _lg, rows = self.fresh()
        # baseline had zero native-shell rewritten; production has 4 > cap 2
        baseline = {"surfaces": []}
        warnings: list[str] = []
        CK._warn_wave_budget(rows, baseline, warnings)
        self.assertTrue(any("wave budget" in w and "native-shell" in w for w in warnings), warnings)

    def test_wave_budget_skipped_without_baseline(self) -> None:
        _lg, rows = self.fresh()
        warnings: list[str] = []
        CK._warn_wave_budget(rows, None, warnings)
        self.assertEqual([], warnings)

    # -- regenerate progress-loss guard -----------------------------------
    def test_regenerate_refuses_silent_progress_loss(self) -> None:
        existing = copy.deepcopy(self.ledger)
        existing["surfaces"].append({
            "surface": "gone/uiconfig/ui/vanished.ui",
            "owner": "gone", "inventory_id": "unassigned",
            "family": "dialog", "rewrite_class": "dialog-anatomy",
            "rewrite_status": "rewritten-material",
            "rewrite_evidence": {"commit": "c" * 40, "contract": "x", "capture": {}, "anatomy_markers": {"a": 1}},
        })
        with self.assertRaises(CK.ValidationError) as ctx:
            CK.build_ledger(REPOSITORY, existing)
        self.assertIn("vanished.ui", str(ctx.exception))

    def test_regenerate_allow_status_loss_drops_row(self) -> None:
        existing = copy.deepcopy(self.ledger)
        existing["surfaces"].append({
            "surface": "gone/uiconfig/ui/vanished.ui",
            "owner": "gone", "inventory_id": "unassigned",
            "family": "dialog", "rewrite_class": "dialog-anatomy",
            "rewrite_status": "rewritten-material",
            "rewrite_evidence": {"commit": "c" * 40, "contract": "x", "capture": {}, "anatomy_markers": {"a": 1}},
        })
        rebuilt = CK.build_ledger(REPOSITORY, existing, allow_status_loss=True)
        self.assertNotIn("gone/uiconfig/ui/vanished.ui", CK._ledger_rows(rebuilt))

    # -- regenerate determinism -------------------------------------------
    def test_regenerate_is_idempotent_and_preserves_status(self) -> None:
        rebuilt = CK.build_ledger(REPOSITORY, self.ledger)
        self.assertEqual(CK.serialize_ledger(rebuilt), CK.serialize_ledger(self.ledger))
        # the 5 seeded rewritten statuses survive a structural regenerate
        rebuilt_rows = CK._ledger_rows(rebuilt)
        rewritten = [s for s, r in rebuilt_rows.items() if r["rewrite_status"] == CK.REWRITTEN]
        self.assertEqual(len(rewritten), self.ledger["coverage"]["rewritten_material"])


if __name__ == "__main__":
    unittest.main()
