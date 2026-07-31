#!/usr/bin/env python3
"""Mutation tests for the Material Windows Installer lifecycle composition."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-msi-lifecycle-composition.py"
SPEC = importlib.util.spec_from_file_location("msi_lifecycle_contract", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class MsiLifecycleCompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract, cls.texts, cls.binaries = VALIDATOR.load_repository(REPOSITORY)

    def errors(self, *, contract=None, texts=None, binaries=None) -> list[str]:
        return VALIDATOR.violations(
            copy.deepcopy(self.contract if contract is None else contract),
            copy.deepcopy(self.texts if texts is None else texts),
            copy.deepcopy(self.binaries if binaries is None else binaries),
        )

    def test_production_contract(self) -> None:
        self.assertEqual([], self.errors())

    def test_runtime_claim_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in error for error in self.errors(contract=contract)))

    def test_generated_asset_drift_fails(self) -> None:
        binaries = copy.deepcopy(self.binaries)
        binaries["Banner.bmp"] += b"mutation"
        self.assertTrue(any("Banner.bmp" in error for error in self.errors(binaries=binaries)))

    def test_bitmap_geometry_drift_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["assets"][0]["width"] = 631
        self.assertTrue(any("bitmap geometry" in error for error in self.errors(contract=contract)))

    def test_binary_mapping_drift_fails(self) -> None:
        texts = copy.deepcopy(self.texts)
        path = self.contract["tables"]["binary"]
        texts[path] = texts[path].replace("BannerBmp\tBanner.bmp", "BannerBmp\tOld.bmp")
        self.assertTrue(any("Binary.idt" in error for error in self.errors(texts=texts)))

    def test_default_font_drift_fails(self) -> None:
        texts = copy.deepcopy(self.texts)
        path = self.contract["tables"]["text_style"]
        texts[path] = texts[path].replace("DialogDefault\tSegoe UI\t9", "DialogDefault\tArial\t8")
        self.assertTrue(any("Segoe UI" in error for error in self.errors(texts=texts)))

    def test_lifecycle_default_drift_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["lifecycle_dialogs"][0]["default"] = "Cancel"
        self.assertTrue(any("default action drift" in error for error in self.errors(contract=contract)))

    def test_lifecycle_visual_drift_fails(self) -> None:
        texts = copy.deepcopy(self.texts)
        path = self.contract["tables"]["control"]
        texts[path] = texts[path].replace(
            "InstallWelcome\tImage\tBitmap\t0\t0\t122\t234\t1\t\tImageBmp",
            "InstallWelcome\tImage\tBitmap\t0\t0\t122\t234\t1\t\tOldBmp",
        )
        self.assertTrue(any("InstallWelcome" in error for error in self.errors(texts=texts)))

    def test_safe_decision_default_drift_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["decision_dialogs"][0]["safe_default"] = "Yes"
        self.assertTrue(any("safe default drift" in error for error in self.errors(contract=contract)))

    def test_material_token_drift_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["token_roles"].append("not-a-real-token")
        self.assertTrue(any("token role missing" in error for error in self.errors(contract=contract)))

    def test_rewritten_ledger_contract_drift_fails(self) -> None:
        texts = copy.deepcopy(self.texts)
        ledger = json.loads(texts[VALIDATOR.LEDGER_PATH])
        row = next(item for item in ledger["surfaces"] if item["surface"] == self.contract["surface"])
        row["rewrite_status"] = "rewritten-material"
        row["rewrite_evidence"] = {
            "contract": "qa/windows-ui-contract/wrong.json",
            "anatomy_markers": {"contract_marker": "wrong"},
        }
        texts[VALIDATOR.LEDGER_PATH] = json.dumps(ledger)
        self.assertTrue(any("must cite" in error for error in self.errors(texts=texts)))


if __name__ == "__main__":
    unittest.main()
