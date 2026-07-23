#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the UNCONDITIONAL Material activation contract (Windows).

Per operator directive Material Design is the product: the Windows activation
carries no opt-out environment variable and no user override. Each mutation
perturbs one guarantee against an in-memory copy of the tree and asserts the
checker fails closed; a positive control proves the pristine tree passes. The
real repository is never mutated.

The fail-closed inversions are the heart of the new semantics: instead of
proving an opt-out is *present*, they prove that *reintroducing* one -- the
``LIBREOFFICE_MATERIAL_THEME`` opt-out token, a ``getenv`` override conditional
around either ``_putenv_s`` write, or a registry that stops declaring the
activation unconditional -- fails the contract.
"""

from __future__ import annotations

import copy
import importlib.util
import re
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-material-default-activation.py"
SPEC = importlib.util.spec_from_file_location(
    "check_material_default_activation", VALIDATOR_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

SOURCE = "desktop/source/app/sofficemain.cxx"
GATE = "vcl/source/gdi/salgdilayout.cxx"
MK = "vcl/Package_theme_definitions.mk"

# The whole unconditional-activation block: from its Windows guard through the
# matching #endif, terminated on the second (draw-switch) _putenv_s write so the
# non-greedy span cannot leak into the later UI-test #if defined _WIN32 region.
BLOCK_RE = re.compile(
    r"#ifdef _WIN32\n"
    r"    // This fork ships Material Design.*?"
    r'_putenv_s\("VCL_DRAW_WIDGETS_FROM_FILE", "1"\);\n'
    r"#endif\n",
    re.DOTALL,
)
FIRST_STATEMENT = "sal_detail_initialize(sal::detail::InitializeSoffice, nullptr);\n"

# A theme write line to hang the fail-closed source inversions off of.
THEME_PUTENV = '_putenv_s("VCL_FILE_WIDGET_THEME", "material");'
DRAW_PUTENV = '_putenv_s("VCL_DRAW_WIDGETS_FROM_FILE", "1");'


class MaterialDefaultActivationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, self.contents = VALIDATOR.load_repository(REPOSITORY)

    def failures(self, *, registry=None, contents=None) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry,
            self.contents if contents is None else contents,
        )

    def with_content(self, path: str, text: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents[path] = text
        return contents

    def without_content(self, path: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents.pop(path, None)
        return contents

    def mutate(self, path: str, old: str, new: str, count: int = 1) -> dict[str, str]:
        text = self.contents[path]
        replaced = text.replace(old, new) if count < 0 else text.replace(old, new, count)
        self.assertNotEqual(text, replaced, f"mutation anchor not found in {path}: {old!r}")
        return self.with_content(path, replaced)

    def registry_copy(self) -> dict:
        return copy.deepcopy(self.registry)

    # -- baseline ----------------------------------------------------------
    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    # -- the activation block ---------------------------------------------
    def test_removed_block_fails(self) -> None:
        src = self.contents[SOURCE]
        mutated = BLOCK_RE.sub("", src, count=1)
        self.assertNotEqual(src, mutated, "block anchor not found")
        errors = self.failures(contents=self.with_content(SOURCE, mutated))
        self.assertTrue(errors)
        self.assertTrue(any("_putenv_s" in e for e in errors), errors)

    def test_block_moved_after_first_statement_fails(self) -> None:
        src = self.contents[SOURCE]
        match = BLOCK_RE.search(src)
        self.assertIsNotNone(match, "block anchor not found")
        block = match.group(0)
        without = src[: match.start()] + src[match.end() :]
        moved = without.replace(FIRST_STATEMENT, FIRST_STATEMENT + block, 1)
        self.assertNotEqual(without, moved, "first-statement anchor not found")
        errors = self.failures(contents=self.with_content(SOURCE, moved))
        self.assertTrue(
            any("before the first statement" in e for e in errors), errors
        )

    def test_win32_guard_removed_fails(self) -> None:
        errors = self.failures(
            contents=self.mutate(
                SOURCE,
                "#ifdef _WIN32\n    // This fork ships Material",
                "#if 1\n    // This fork ships Material",
            )
        )
        self.assertTrue(any("guard" in e for e in errors), errors)

    def test_theme_putenv_value_drift_fails(self) -> None:
        # Target the code call, not the "material" mention in the block comment
        # (the checker strips comments, so a comment-only edit would be invisible).
        errors = self.failures(
            contents=self.mutate(
                SOURCE,
                '_putenv_s("VCL_FILE_WIDGET_THEME", "material")',
                '_putenv_s("VCL_FILE_WIDGET_THEME", "materiel")',
            )
        )
        self.assertTrue(
            any("VCL_FILE_WIDGET_THEME" in e and "_putenv_s" in e for e in errors), errors
        )

    def test_draw_putenv_value_drift_fails(self) -> None:
        errors = self.failures(
            contents=self.mutate(
                SOURCE,
                '_putenv_s("VCL_DRAW_WIDGETS_FROM_FILE", "1")',
                '_putenv_s("VCL_DRAW_WIDGETS_FROM_FILE", "2")',
                -1,
            )
        )
        self.assertTrue(
            any("VCL_DRAW_WIDGETS_FROM_FILE" in e and "_putenv_s" in e for e in errors),
            errors,
        )

    def test_missing_source_file_fails_closed(self) -> None:
        errors = self.failures(contents=self.without_content(SOURCE))
        self.assertTrue(any("file missing" in e for e in errors), errors)

    # -- fail-closed inversions: a reintroduced opt-out/override must FAIL --
    def test_reintroduced_opt_out_token_fails(self) -> None:
        # Wrap the theme write behind the old opt-out env var; the checker forbids
        # the LIBREOFFICE_MATERIAL_THEME token anywhere in the file.
        mutated = self.mutate(
            SOURCE,
            THEME_PUTENV,
            'if (getenv("LIBREOFFICE_MATERIAL_THEME") == nullptr)\n        '
            + THEME_PUTENV,
        )
        errors = self.failures(contents=mutated)
        self.assertTrue(
            any("forbidden marker" in e and "LIBREOFFICE_MATERIAL_THEME" in e
                for e in errors),
            errors,
        )

    def test_getenv_theme_override_conditional_fails(self) -> None:
        # A respect-existing override guard around the theme write is forbidden.
        mutated = self.mutate(
            SOURCE,
            THEME_PUTENV,
            'if (!getenv("VCL_FILE_WIDGET_THEME"))\n        ' + THEME_PUTENV,
        )
        errors = self.failures(contents=mutated)
        self.assertTrue(
            any("forbidden marker" in e and "VCL_FILE_WIDGET_THEME" in e
                for e in errors),
            errors,
        )

    def test_getenv_draw_override_conditional_fails(self) -> None:
        # A conditional around the draw-switch write is likewise forbidden.
        mutated = self.mutate(
            SOURCE,
            DRAW_PUTENV,
            'if (!getenv("VCL_DRAW_WIDGETS_FROM_FILE"))\n        ' + DRAW_PUTENV,
        )
        errors = self.failures(contents=mutated)
        self.assertTrue(
            any("forbidden marker" in e and "VCL_DRAW_WIDGETS_FROM_FILE" in e
                for e in errors),
            errors,
        )

    # -- asset cross-checks ------------------------------------------------
    def test_salgdilayout_gate_drift_fails(self) -> None:
        errors = self.failures(
            contents=self.mutate(
                GATE,
                'getenv("VCL_DRAW_WIDGETS_FROM_FILE")',
                'getenv("VCL_DEAD_SWITCH")',
            )
        )
        self.assertTrue(any("asset_cross_checks:gate" in e for e in errors), errors)

    def test_package_mk_drift_fails(self) -> None:
        errors = self.failures(
            contents=self.mutate(
                MK, "material/definition.xml", "material/definition-renamed.xml"
            )
        )
        self.assertTrue(any("asset_cross_checks:assets" in e for e in errors), errors)

    def test_gate_file_missing_fails_closed(self) -> None:
        errors = self.failures(contents=self.without_content(GATE))
        self.assertTrue(any("asset_cross_checks:gate" in e for e in errors), errors)

    # -- registry invariants ----------------------------------------------
    def test_runtime_verified_true_rejected(self) -> None:
        registry = self.registry_copy()
        registry["runtime_verified"] = True
        errors = self.failures(registry=registry)
        self.assertTrue(any("runtime_verified" in e for e in errors), errors)

    def test_wrong_contract_slug_fails(self) -> None:
        registry = self.registry_copy()
        registry["contract"] = "something-else"
        errors = self.failures(registry=registry)
        self.assertTrue(any("registry:contract" in e for e in errors), errors)

    def test_wrong_schema_version_fails(self) -> None:
        registry = self.registry_copy()
        registry["schema_version"] = 2
        errors = self.failures(registry=registry)
        self.assertTrue(any("schema_version" in e for e in errors), errors)

    def test_wrong_status_fails(self) -> None:
        registry = self.registry_copy()
        registry["status"] = "implemented"
        errors = self.failures(registry=registry)
        self.assertTrue(any("registry:status" in e for e in errors), errors)

    def test_carveout_status_promoted_fails(self) -> None:
        registry = self.registry_copy()
        registry["carveout"]["first_visual_verification"]["status"] = "implemented"
        errors = self.failures(registry=registry)
        self.assertTrue(any("carveout" in e for e in errors), errors)

    def test_registry_unconditional_false_fails(self) -> None:
        registry = self.registry_copy()
        registry["activation"]["unconditional"] = False
        errors = self.failures(registry=registry)
        self.assertTrue(any("unconditional" in e for e in errors), errors)

    def test_registry_unconditional_missing_fails(self) -> None:
        registry = self.registry_copy()
        registry["activation"].pop("unconditional", None)
        errors = self.failures(registry=registry)
        self.assertTrue(any("unconditional" in e for e in errors), errors)

    def test_registry_forbidden_markers_empty_fails(self) -> None:
        registry = self.registry_copy()
        registry["activation"]["forbidden_markers"] = []
        errors = self.failures(registry=registry)
        self.assertTrue(any("forbidden_markers" in e for e in errors), errors)

    def test_registry_forbidden_markers_missing_fails(self) -> None:
        registry = self.registry_copy()
        registry["activation"].pop("forbidden_markers", None)
        errors = self.failures(registry=registry)
        self.assertTrue(any("forbidden_markers" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
