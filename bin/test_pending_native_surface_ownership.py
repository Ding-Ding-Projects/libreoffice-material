#!/usr/bin/env python3
"""Mutation tests for pending native ownership."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-pending-native-surface-ownership.py"
SPEC = importlib.util.spec_from_file_location("pending_native_ownership", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class PendingNativeOwnershipTest(unittest.TestCase):
    def test_production_contract(self) -> None:
        VALIDATOR.validate(REPOSITORY)

    def test_expected_surface_set_is_complete(self) -> None:
        self.assertEqual(3, len(VALIDATOR.EXPECTED))
        self.assertNotIn("native:find-toolbar", VALIDATOR.EXPECTED)
        self.assertNotIn("native:msi-install-lifecycle-ui", VALIDATOR.EXPECTED)
        self.assertNotIn("vcl/uiconfig/ui/wizard.ui", VALIDATOR.EXPECTED)

    def test_missing_marker_fails_closed(self) -> None:
        original = VALIDATOR.EXPECTED
        try:
            VALIDATOR.EXPECTED = dict(original)
            VALIDATOR.EXPECTED["native:updater-lifecycle-ui"] = (
                "native-shell", "wrong-owner", "WIN-SYS-012"
            )
            errors = VALIDATOR.violations(REPOSITORY)
            self.assertTrue(any("owner drift" in error for error in errors), errors)
        finally:
            VALIDATOR.EXPECTED = original


if __name__ == "__main__":
    unittest.main()
