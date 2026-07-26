#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for build-free workflow fleet closure."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-build-free-gate-coverage.py"
SPEC = importlib.util.spec_from_file_location("check_build_free_gate_coverage", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class BuildFreeGateCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.eligible = VALIDATOR.discover_eligible_scripts(REPOSITORY)
        self.workflows = VALIDATOR.load_workflows(REPOSITORY)
        self.contract_path = ".github/workflows/windows-ui-contract.yml"

    def failures(
        self,
        *,
        eligible: set[str] | None = None,
        workflows: dict[str, str] | None = None,
    ) -> list[str]:
        return VALIDATOR.violations(
            self.eligible if eligible is None else eligible,
            self.workflows if workflows is None else workflows,
        )

    def mutate_workflow(self, old: str, new: str) -> dict[str, str]:
        workflows = dict(self.workflows)
        source = workflows[self.contract_path]
        self.assertIn(old, source)
        workflows[self.contract_path] = source.replace(old, new, 1)
        return workflows

    def test_production_fleet_is_closed(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    def test_removed_checker_invocation_fails(self) -> None:
        workflows = self.mutate_workflow(
            "run: python3 bin/check-config-layer-coverage.py",
            "run: echo checker-removed",
        )
        errors = self.failures(workflows=workflows)
        self.assertTrue(any("check-config-layer-coverage.py" in e for e in errors), errors)

    def test_removed_mutation_suite_invocation_fails(self) -> None:
        workflows = self.mutate_workflow(
            "run: python3 bin/test_check_ui_a11y_fatals.py",
            "run: echo suite-removed",
        )
        errors = self.failures(workflows=workflows)
        self.assertTrue(any("test_check_ui_a11y_fatals.py" in e for e in errors), errors)

    def test_comment_only_reference_does_not_count(self) -> None:
        workflows = self.mutate_workflow(
            "run: python3 bin/check-notification-overlay-contract.py",
            "run: echo checker-removed\n      # python3 bin/check-notification-overlay-contract.py",
        )
        errors = self.failures(workflows=workflows)
        self.assertTrue(
            any("check-notification-overlay-contract.py" in e for e in errors), errors
        )

    def test_new_unregistered_gate_fails(self) -> None:
        eligible = set(self.eligible)
        eligible.add("bin/check-new-unregistered-contract.py")
        errors = self.failures(eligible=eligible)
        self.assertTrue(any("check-new-unregistered-contract.py" in e for e in errors), errors)

    def test_removed_prototype_validator_fails(self) -> None:
        owner = next(
            path
            for path, source in self.workflows.items()
            if "node bin/validate-prototype.mjs" in source
        )
        workflows = dict(self.workflows)
        workflows[owner] = workflows[owner].replace(
            "node bin/validate-prototype.mjs", "echo prototype-validator-removed", 1
        )
        errors = self.failures(workflows=workflows)
        self.assertTrue(any("validate-prototype.mjs" in e for e in errors), errors)

    def test_unittest_module_invocations_count(self) -> None:
        referenced = VALIDATOR.referenced_scripts(self.workflows)
        self.assertIn("bin/test_material_theme_validator.py", referenced)
        self.assertIn("bin/test_startcenter_no_donate.py", referenced)

    def test_inherited_upstream_linters_stay_excluded(self) -> None:
        for name in VALIDATOR.UPSTREAM_CHECK_EXCLUSIONS:
            self.assertNotIn(f"bin/{name}", self.eligible)


if __name__ == "__main__":
    unittest.main()
