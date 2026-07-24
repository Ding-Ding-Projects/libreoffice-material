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


# A synthetic, fully Material-conforming dialog .ui: Help|Cancel|OK footer with
# OK the can-default/has-default primary, a >=10 spacing button box, a content
# grid with spacing+margins, and an ellipsize=end mnemonic-bound label. Dropping
# any single required marker must knock the surface back to pending.
CONFORMING_DIALOG_UI = """<?xml version="1.0" encoding="UTF-8"?>
<interface domain="test">
  <requires lib="gtk+" version="3.24"/>
  <object class="GtkDialog" id="TestDialog">
    <property name="title" translatable="yes">Test Dialog</property>
    <property name="modal">True</property>
    <child internal-child="vbox">
      <object class="GtkBox" id="dialog-vbox1">
        <property name="orientation">vertical</property>
        <property name="spacing">12</property>
        <child internal-child="action_area">
          <object class="GtkButtonBox" id="dialog-action_area1">
            <property name="layout-style">end</property>
            <property name="spacing">12</property>
            <child>
              <object class="GtkButton" id="ok">
                <property name="label" translatable="yes">_OK</property>
                <property name="can-default">True</property>
                <property name="has-default">True</property>
                <property name="use-underline">True</property>
              </object>
            </child>
            <child>
              <object class="GtkButton" id="cancel">
                <property name="label" translatable="yes">_Cancel</property>
              </object>
            </child>
            <child>
              <object class="GtkButton" id="help">
                <property name="label" translatable="yes">_Help</property>
              </object>
              <packing>
                <property name="secondary">True</property>
              </packing>
            </child>
          </object>
        </child>
        <child>
          <object class="GtkGrid" id="grid1">
            <property name="row-spacing">12</property>
            <property name="margin-start">6</property>
            <property name="margin-end">6</property>
            <property name="margin-top">6</property>
            <property name="margin-bottom">6</property>
            <child>
              <object class="GtkLabel" id="lbl">
                <property name="label" translatable="yes">_Name:</property>
                <property name="use-underline">True</property>
                <property name="mnemonic-widget">entry</property>
                <property name="ellipsize">end</property>
              </object>
            </child>
            <child>
              <object class="GtkEntry" id="entry"/>
            </child>
          </object>
        </child>
      </object>
    </child>
    <action-widgets>
      <action-widget response="-11">help</action-widget>
      <action-widget response="-6">cancel</action-widget>
      <action-widget response="-5">ok</action-widget>
    </action-widgets>
  </object>
</interface>
"""


# A synthetic Material popover: a GtkPopover whose content container declares
# BOTH Material spacing and margins, and with NO legacy border-width override
# anywhere. This is the anatomy the rewrite introduces (container padding the
# theme cannot supply) after dropping the stock border-width chrome, so it must
# evaluate rewritten-material.
CONFORMING_POPOVER_UI = """<?xml version="1.0" encoding="UTF-8"?>
<interface domain="test">
  <requires lib="gtk+" version="3.24"/>
  <object class="GtkPopover" id="TestPopover">
    <property name="can-focus">False</property>
    <property name="no-show-all">True</property>
    <property name="constrain-to">none</property>
    <child>
      <object class="GtkBox" id="container">
        <property name="visible">True</property>
        <property name="can-focus">False</property>
        <property name="orientation">vertical</property>
        <property name="spacing">6</property>
        <property name="margin-start">6</property>
        <property name="margin-end">6</property>
        <property name="margin-top">6</property>
        <property name="margin-bottom">6</property>
        <child>
          <object class="GtkLabel" id="lbl">
            <property name="visible">True</property>
            <property name="label" translatable="yes">Preset</property>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>
"""

# The same popover still carrying the legacy border-width override the rewrite
# is supposed to remove (the exact stock chrome the reviewer flagged). Even with
# a Material container it must fall back to pending: border-width present.
BORDER_POPOVER_UI = CONFORMING_POPOVER_UI.replace(
    '    <property name="constrain-to">none</property>\n',
    '    <property name="constrain-to">none</property>\n'
    '    <property name="border-width">4</property>\n',
)

# A popover byte-identical in spirit to a stock one: a decorative icon-name on a
# child but NO Material spacing/margins on the container. The old menu predicate
# credited this on the icon-name alone; the popover predicate must not.
STOCK_POPOVER_UI = """<?xml version="1.0" encoding="UTF-8"?>
<interface domain="test">
  <requires lib="gtk+" version="3.24"/>
  <object class="GtkImage" id="preset_icon">
    <property name="icon-name">cmd/sc_square_unfilled.png</property>
  </object>
  <object class="GtkPopover" id="StockPopover">
    <property name="can-focus">False</property>
    <property name="no-show-all">True</property>
    <property name="border-width">4</property>
    <property name="constrain-to">none</property>
    <child>
      <object class="GtkBox" id="container">
        <property name="visible">True</property>
        <property name="can-focus">False</property>
        <property name="orientation">vertical</property>
        <child>
          <object class="GtkButton" id="preset_button">
            <property name="visible">True</property>
            <property name="image">preset_icon</property>
            <property name="action-name">.uno:InsertPreset</property>
          </object>
        </child>
      </object>
    </child>
  </object>
</interface>
"""

# A stock context menu: real .uno: action-names on its items but byte-identical
# to upstream. Menus are a composition-cross-referenced family now, so static
# --evaluate must never credit this on the pre-existing action-names alone.
STOCK_MENU_UI = """<?xml version="1.0" encoding="UTF-8"?>
<interface domain="test">
  <requires lib="gtk+" version="3.24"/>
  <object class="GtkMenu" id="menu">
    <property name="visible">True</property>
    <property name="can-focus">False</property>
    <child>
      <object class="GtkMenuItem" id="cut">
        <property name="visible">True</property>
        <property name="action-name">.uno:Cut</property>
        <property name="label" translatable="yes">Cu_t</property>
        <property name="use-underline">True</property>
      </object>
    </child>
    <child>
      <object class="GtkMenuItem" id="copy">
        <property name="visible">True</property>
        <property name="action-name">.uno:Copy</property>
        <property name="label" translatable="yes">_Copy</property>
        <property name="use-underline">True</property>
      </object>
    </child>
  </object>
</interface>
"""


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
        # a structural (statuses-preserved) regenerate keeps every rewritten row
        rebuilt_rows = CK._ledger_rows(rebuilt)
        rewritten = [s for s, r in rebuilt_rows.items() if r["rewrite_status"] == CK.REWRITTEN]
        self.assertEqual(len(rewritten), self.ledger["coverage"]["rewritten_material"])

    # -- static --evaluate crediting --------------------------------------
    def _write_ui(self, xml: str) -> tuple[Path, str]:
        root = Path(tempfile.mkdtemp(prefix="mrl_ui_"))
        surface = "sub/test.ui"
        (root / "sub").mkdir(parents=True, exist_ok=True)
        (root / surface).write_text(xml, encoding="utf-8")
        return root, surface

    def test_evaluate_credits_conforming_dialog(self) -> None:
        repo, surface = self._write_ui(CONFORMING_DIALOG_UI)
        status, evidence = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_DIALOG, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.REWRITTEN)
        self.assertEqual(evidence["commit"], "a" * 40)
        self.assertTrue(evidence["contract"])
        self.assertEqual(evidence["capture"]["captured"], False)
        self.assertTrue(evidence["anatomy_markers"])
        # the stored snapshot equals a fresh re-derivation (what C4 later demands)
        root = CK._parse_root(repo, surface)
        fresh = CK.derive_static_markers(CK.FAMILY_DIALOG, root)
        self.assertEqual(evidence["anatomy_markers"], fresh)
        ok, why = CK.static_predicate(CK.FAMILY_DIALOG, fresh)
        self.assertTrue(ok, why)

    def test_evaluate_pending_when_can_default_removed(self) -> None:
        # drop the primary can-default/has-default marker -> predicate fails
        broken = CONFORMING_DIALOG_UI.replace(
            'name="can-default">True', 'name="can-default">False'
        ).replace('name="has-default">True', 'name="has-default">False')
        repo, surface = self._write_ui(broken)
        status, evidence = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_DIALOG, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.PENDING)
        self.assertEqual(evidence, CK._null_evidence())

    def test_evaluate_pending_when_ellipsize_deleted(self) -> None:
        broken = CONFORMING_DIALOG_UI.replace(
            '<property name="ellipsize">end</property>\n', ""
        )
        repo, surface = self._write_ui(broken)
        status, _ = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_DIALOG, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.PENDING)

    def test_evaluate_pending_when_action_order_scrambled(self) -> None:
        # move OK out of the last (primary) slot -> footer anatomy fails
        broken = CONFORMING_DIALOG_UI.replace(
            '      <action-widget response="-11">help</action-widget>\n'
            '      <action-widget response="-6">cancel</action-widget>\n'
            '      <action-widget response="-5">ok</action-widget>\n',
            '      <action-widget response="-11">help</action-widget>\n'
            '      <action-widget response="-5">ok</action-widget>\n'
            '      <action-widget response="-6">cancel</action-widget>\n',
        )
        self.assertNotEqual(broken, CONFORMING_DIALOG_UI)
        repo, surface = self._write_ui(broken)
        status, _ = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_DIALOG, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.PENDING)

    def test_evaluate_preserves_composition_contract_path(self) -> None:
        # composition families are never statically recomputed: evaluate returns
        # the campaign-owned status/evidence verbatim, and never auto-credits.
        prior_ev = {
            "commit": "c" * 40, "contract": "qa/windows-ui-contract/x.json",
            "capture": {"scene": "s"}, "anatomy_markers": {"contract_marker": "t"},
        }
        status, evidence = CK.evaluate_surface_status(
            REPOSITORY, "native:some-shell", CK.FAMILY_NATIVE, {},
            CK.REWRITTEN, prior_ev, "a" * 40,
        )
        self.assertEqual(status, CK.REWRITTEN)
        self.assertEqual(evidence, prior_ev)
        status2, evidence2 = CK.evaluate_surface_status(
            REPOSITORY, "native:some-shell", CK.FAMILY_NATIVE, {},
            CK.PENDING, CK._null_evidence(), "a" * 40,
        )
        self.assertEqual(status2, CK.PENDING)
        self.assertEqual(evidence2, CK._null_evidence())

    def test_evaluate_never_drops_prior_rewritten(self) -> None:
        # fail-closed: a now-failing static surface that was rewritten keeps the
        # status here (the honest failure surfaces at C4, not as a silent drop).
        broken = CONFORMING_DIALOG_UI.replace(
            'name="can-default">True', 'name="can-default">False'
        ).replace('name="has-default">True', 'name="has-default">False')
        repo, surface = self._write_ui(broken)
        prior_ev = {
            "commit": "c" * 40, "contract": "x",
            "capture": {"scene": "s"}, "anatomy_markers": {"a": 1},
        }
        status, evidence = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_DIALOG, {}, CK.REWRITTEN, prior_ev, "a" * 40
        )
        self.assertEqual(status, CK.REWRITTEN)
        self.assertEqual(evidence, prior_ev)

    def test_evaluate_reproduces_committed_ledger(self) -> None:
        # re-running --evaluate from the committed tree is a no-op: the earned
        # rewritten set is reproducible and the commit stamps are stable.
        rebuilt = CK.build_ledger(REPOSITORY, self.ledger, evaluate=True)
        self.assertEqual(CK.serialize_ledger(rebuilt), CK.serialize_ledger(self.ledger))

    def test_every_rewritten_static_surface_earns_it(self) -> None:
        # honesty bar, line-by-line: every rewritten-material static-ui surface in
        # the production ledger genuinely satisfies its full family predicate.
        credited = 0
        for row in self.ledger["surfaces"]:
            if row["rewrite_status"] != CK.REWRITTEN:
                continue
            fam = row["family"]
            if CK.evidence_kind_for(fam) != CK.STATIC_UI:
                continue
            credited += 1
            root = CK._parse_root(REPOSITORY, row["surface"])
            markers = CK.derive_static_markers(fam, root)
            ok, why = CK.static_predicate(fam, markers)
            self.assertTrue(ok, f"{row['surface']} credited but fails predicate: {why}")
        # the number is earned, not the old 5-row seed
        self.assertGreater(self.ledger["coverage"]["rewritten_material"], 5)
        self.assertGreater(credited, 5)

    # -- popover static evaluation (container anatomy + no legacy chrome) ---
    def test_evaluate_credits_conforming_popover(self) -> None:
        repo, surface = self._write_ui(CONFORMING_POPOVER_UI)
        status, evidence = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_POPOVER, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.REWRITTEN)
        self.assertEqual(evidence["commit"], "a" * 40)
        self.assertTrue(evidence["contract"])
        self.assertEqual(evidence["capture"]["captured"], False)
        self.assertTrue(evidence["anatomy_markers"])
        # the stored snapshot equals a fresh re-derivation (what C4 later demands)
        root = CK._parse_root(repo, surface)
        fresh = CK.derive_static_markers(CK.FAMILY_POPOVER, root)
        self.assertEqual(evidence["anatomy_markers"], fresh)
        ok, why = CK.static_predicate(CK.FAMILY_POPOVER, fresh)
        self.assertTrue(ok, why)

    def test_evaluate_pending_when_popover_carries_border_width(self) -> None:
        # a border-width-carrying popover is stock chrome, not Material -> pending
        repo, surface = self._write_ui(BORDER_POPOVER_UI)
        status, evidence = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_POPOVER, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.PENDING)
        self.assertEqual(evidence, CK._null_evidence())
        markers = CK.derive_static_markers(CK.FAMILY_POPOVER, CK._parse_root(repo, surface))
        self.assertTrue(markers["has_legacy_border"])
        ok, why = CK.predicate_popover(markers)
        self.assertFalse(ok, why)
        self.assertIn("border-width", why)

    def test_evaluate_pending_when_popover_container_has_no_spacing(self) -> None:
        # decorative icon-name + .uno action but no container spacing/margins:
        # exactly the case the old predicate_menu wrongly credited.
        repo, surface = self._write_ui(STOCK_POPOVER_UI)
        status, _ = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_POPOVER, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.PENDING)

    def test_popover_predicate_requires_both_prongs(self) -> None:
        # spacing+margins AND no border-width -> pass; drop either prong -> fail
        root_dir, surface = self._write_ui(CONFORMING_POPOVER_UI)
        material = CK.derive_static_markers(
            CK.FAMILY_POPOVER, CK._parse_root(root_dir, surface)
        )
        ok, _ = CK.predicate_popover(material)
        self.assertTrue(ok)
        no_margin = dict(material, container_has_margin=False)
        self.assertFalse(CK.predicate_popover(no_margin)[0])
        no_spacing = dict(material, container_has_spacing=False)
        self.assertFalse(CK.predicate_popover(no_spacing)[0])
        with_border = dict(material, has_legacy_border=True)
        self.assertFalse(CK.predicate_popover(with_border)[0])

    def test_every_credited_popover_is_genuinely_material(self) -> None:
        # honesty bar for the family the reviewer flagged: every credited popover
        # shows real container anatomy AND carries no legacy border-width.
        for row in self.ledger["surfaces"]:
            if row["family"] != "popover" or row["rewrite_status"] != CK.REWRITTEN:
                continue
            markers = CK.derive_popover_markers(CK._parse_root(REPOSITORY, row["surface"]))
            self.assertFalse(markers["has_legacy_border"], row["surface"])
            self.assertTrue(markers["container_has_spacing"], row["surface"])
            self.assertTrue(markers["container_has_margin"], row["surface"])
            ok, why = CK.predicate_popover(markers)
            self.assertTrue(ok, f"{row['surface']}: {why}")

    # -- menu is a composition family (never statically auto-credited) ------
    def test_menu_family_is_composition_code(self) -> None:
        self.assertEqual(CK.evidence_kind_for(CK.FAMILY_MENU), CK.COMPOSITION_CODE)

    def test_stock_menu_evaluates_pending(self) -> None:
        # a stock-identical menu with pre-existing .uno action-names must stay
        # pending: menus ride the menu-composition contract, not a static parse.
        repo, surface = self._write_ui(STOCK_MENU_UI)
        status, evidence = CK.evaluate_surface_status(
            repo, surface, CK.FAMILY_MENU, {}, CK.PENDING, CK._null_evidence(), "a" * 40
        )
        self.assertEqual(status, CK.PENDING)
        self.assertEqual(evidence, CK._null_evidence())

    def test_production_credits_no_menu(self) -> None:
        # the byte-identical spellmenu over-credit is gone: zero menus credited.
        self.assertEqual(self.ledger["coverage"]["by_family"]["menu"][CK.REWRITTEN], 0)


if __name__ == "__main__":
    unittest.main()
