#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material token accessor fidelity contract."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-material-token-accessor.py"
SPEC = importlib.util.spec_from_file_location("check_material_token_accessor", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class MaterialTokenAccessorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contents = VALIDATOR.load_repository(REPOSITORY)

    def mutate(self, **overrides: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents.update(overrides)
        return contents

    def failures(self, contents: dict[str, str] | None = None) -> list[str]:
        return VALIDATOR.violations(self.contents if contents is None else contents)

    # -- baseline ----------------------------------------------------------
    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    # -- vocabulary drift --------------------------------------------------
    def test_missing_color_role_fails(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace('    "on-surface-variant",\n', "", 1)
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any(":gMaterialColorRoles:" in e for e in errors), errors)

    def test_extra_color_role_fails(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace(
            '    "visited-link",\n', '    "visited-link",\n    "invented-role",\n', 1
        )
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any("undeclared name(s) not in definition" in e for e in errors), errors)

    def test_array_size_mismatch_fails(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace(
            "std::array<std::string_view, 23>", "std::array<std::string_view, 24>", 1
        )
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any("declared std::array size" in e for e in errors), errors)

    def test_missing_metric_token_fails(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace('    "height-tab",\n', "", 1)
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any(":gMaterialMetricTokens:" in e for e in errors), errors)

    def test_missing_shape_token_fails(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace('"corner-pill",\n', "", 1)
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any(":gMaterialShapeTokens:" in e for e in errors), errors)

    def test_definition_drift_fails(self) -> None:
        # Adding a palette color to the definition without updating the accessor
        # must fail closed on both schemes.
        definition = self.contents[VALIDATOR.DEFINITION].replace(
            '<color name="visited-link" value="#7D5260"/>',
            '<color name="visited-link" value="#7D5260"/>\n'
            '        <color name="scrim" value="#000000"/>',
            1,
        )
        errors = self.failures(self.mutate(**{VALIDATOR.DEFINITION: definition}))
        self.assertTrue(any(":gMaterialColorRoles:" in e for e in errors), errors)

    # -- hex duplication ---------------------------------------------------
    def test_hardcoded_hex_fails(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace(
            "OString toOString(std::string_view rView)",
            "// baked #6750A4\nOString toOString(std::string_view rView)",
            1,
        )
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any(":no-hex:" in e for e in errors), errors)

    def test_hardcoded_hex_in_header_fails(self) -> None:
        header = self.contents[VALIDATOR.HEADER].replace(
            "class VCL_DLLPUBLIC MaterialTokens",
            "// #E8DEF8\nclass VCL_DLLPUBLIC MaterialTokens",
            1,
        )
        errors = self.failures(self.mutate(**{VALIDATOR.HEADER: header}))
        self.assertTrue(any(":no-hex:" in e for e in errors), errors)

    # -- reader-path sourcing ---------------------------------------------
    def test_reader_call_required(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace(".readTokenTables(", ".readSomethingElse(")
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any(":reader-path:reader-call" in e for e in errors), errors)

    def test_reader_reuse_required(self) -> None:
        # readTokenTables that no longer reuses readColorPalette is a divergent copy.
        reader = self.contents[VALIDATOR.READER_SOURCE].replace(
            "readColorPalette(aTokenWalker, aColorTokens)", "parseColorsInline(aTokenWalker)"
        )
        errors = self.failures(self.mutate(**{VALIDATOR.READER_SOURCE: reader}))
        self.assertTrue(any(":reuse:" in e for e in errors), errors)

    def test_reader_api_declaration_required(self) -> None:
        reader_h = self.contents[VALIDATOR.READER_HEADER].replace(
            "bool readTokenTables(", "bool readOtherTables("
        )
        errors = self.failures(self.mutate(**{VALIDATOR.READER_HEADER: reader_h}))
        self.assertTrue(any("readTokenTables not declared" in e for e in errors), errors)

    def test_theme_path_required(self) -> None:
        source = self.contents[VALIDATOR.SOURCE].replace("theme_definitions/material/", "theme/x/")
        errors = self.failures(self.mutate(**{VALIDATOR.SOURCE: source}))
        self.assertTrue(any(":reader-path:theme-path" in e for e in errors), errors)

    # -- export / registration --------------------------------------------
    def test_public_export_required(self) -> None:
        header = self.contents[VALIDATOR.HEADER].replace(
            "class VCL_DLLPUBLIC MaterialTokens", "class MaterialTokens"
        )
        errors = self.failures(self.mutate(**{VALIDATOR.HEADER: header}))
        self.assertTrue(any(":export:" in e for e in errors), errors)

    def test_makefile_registration_required(self) -> None:
        makefile = self.contents[VALIDATOR.MAKEFILE].replace(
            "vcl/source/gdi/MaterialTokens \\", "", 1
        )
        errors = self.failures(self.mutate(**{VALIDATOR.MAKEFILE: makefile}))
        self.assertTrue(any(":build:" in e for e in errors), errors)

    def test_missing_file_fails_closed(self) -> None:
        contents = dict(self.contents)
        del contents[VALIDATOR.SOURCE]
        errors = self.failures(contents)
        self.assertTrue(any(e.startswith("file:missing") for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
