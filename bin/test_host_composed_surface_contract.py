#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the host-composed Material surface contract."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-host-composed-surface-contract.py"
SPEC = importlib.util.spec_from_file_location("host_composed_surface_contract", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class HostComposedSurfaceContractTest(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.registry,
            self.ledger,
            self.audit,
            self.contents,
        ) = VALIDATOR.load_repository(REPOSITORY)

    def failures(
        self,
        *,
        registry: dict | None = None,
        ledger: dict | None = None,
        audit: dict | None = None,
        contents: dict[str, str] | None = None,
    ) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry,
            self.ledger if ledger is None else ledger,
            self.audit if audit is None else audit,
            self.contents if contents is None else contents,
            repo_root=REPOSITORY,
        )

    def contract_row(self, registry: dict, surface: str | None = None) -> dict:
        if surface is None:
            return registry["surfaces"][0]
        return next(row for row in registry["surfaces"] if row["surface"] == surface)

    def ledger_row(self, ledger: dict, surface: str) -> dict:
        return next(row for row in ledger["surfaces"] if row["surface"] == surface)

    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    def test_generated_contract_is_current(self) -> None:
        completed = subprocess.run(
            [sys.executable, "bin/generate-host-composed-surface-contract.py", "--check"],
            cwd=REPOSITORY,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_exact_surface_set_is_locked(self) -> None:
        self.assertEqual(194, len(self.registry["surfaces"]))
        self.assertEqual(
            VALIDATOR.EXPECTED_SURFACE_SET_SHA256,
            self.registry["surface_set_sha256"],
        )

    def test_runtime_claim_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in item for item in self.failures(registry=registry)))

    def test_surface_set_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["surfaces"][0]["surface"] = "cui/uiconfig/ui/not-real.ui"
        errors = self.failures(registry=registry)
        self.assertTrue(any("surface set digest drifted" in item for item in errors), errors)

    def test_source_digest_drift_fails(self) -> None:
        row = self.contract_row(self.registry)
        surface = row["surface"]
        contents = dict(self.contents)
        contents[surface] += "\n<!-- mutation -->\n"
        errors = self.failures(contents=contents)
        self.assertTrue(any(surface in item and "source_sha256 drifted" in item for item in errors), errors)

    def test_predicate_failure_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        row = self.contract_row(registry)
        row["ordinary_predicate_failure"] = "invented failure"
        errors = self.failures(registry=registry)
        self.assertTrue(any(row["surface"] in item and "predicate failure drifted" in item for item in errors), errors)

    def test_marker_snapshot_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        row = self.contract_row(registry)
        row["marker_snapshot"] = {}
        errors = self.failures(registry=registry)
        self.assertTrue(any(row["surface"] in item and "marker snapshot drifted" in item for item in errors), errors)

    def test_renderer_dependency_marker_drift_fails(self) -> None:
        path = "qa/windows-ui-contract/material-default-activation.json"
        data = json.loads(self.contents[path])
        data["contract"] = "wrong"
        contents = dict(self.contents)
        contents[path] = json.dumps(data)
        errors = self.failures(contents=contents)
        self.assertTrue(any(path in item and "lost contract marker" in item for item in errors), errors)

    def test_ledger_family_drift_fails(self) -> None:
        ledger = copy.deepcopy(self.ledger)
        surface = self.registry["surfaces"][0]["surface"]
        self.ledger_row(ledger, surface)["family"] = "panel-fragment"
        errors = self.failures(ledger=ledger)
        self.assertTrue(any(surface in item and "host-composed-surface" in item for item in errors), errors)

    def test_rewritten_row_requires_exact_composition_evidence(self) -> None:
        ledger = copy.deepcopy(self.ledger)
        contract_row = self.registry["surfaces"][0]
        surface = contract_row["surface"]
        row = self.ledger_row(ledger, surface)
        row["rewrite_status"] = "rewritten-material"
        row["rewrite_evidence"] = {
            "commit": "a" * 40,
            "contract": VALIDATOR.REGISTRY_PATH,
            "capture": {"scene": None, "sample_batch": "source-composition", "captured": False},
            "anatomy_markers": {
                "contract_marker": "wrong",
                "evidence_kind": VALIDATOR.EVIDENCE_KIND,
                "source_sha256": contract_row["source_sha256"],
                "legacy_family": contract_row["legacy_family"],
            },
        }
        errors = self.failures(ledger=ledger)
        self.assertTrue(any(surface in item and "lost the contract marker" in item for item in errors), errors)

    def test_blocked_audit_provenance_drift_fails(self) -> None:
        registry = copy.deepcopy(self.registry)
        row = next(
            item
            for item in registry["surfaces"]
            if item["audit"]["status"] == "blocked-confirmed"
        )
        audit = copy.deepcopy(self.audit)
        prior = next(item for item in audit["surfaces"] if item["surface"] == row["surface"])
        prior["verifier_verdict"] = "unverified"
        errors = self.failures(registry=registry, audit=audit)
        self.assertTrue(any(row["surface"] in item and "audit provenance vanished" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
