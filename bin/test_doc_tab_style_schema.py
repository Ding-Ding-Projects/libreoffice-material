#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the Material document-tab style schema contract.

Each test proves an inversion of the contract fails closed: the pristine tree
passes, and every mutation (drifted type/default/enum/clamp, TabsEnabled turned
on by default, a dropped normalizer branch, or an orphan normalizer branch)
turns the checker red.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-doc-tab-style-schema.py"
SPEC = importlib.util.spec_from_file_location(
    "check_doc_tab_style_schema", VALIDATOR_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

SCHEMA = "officecfg/registry/schema/org/openoffice/Office/Common.xcs"
CXX = "sfx2/source/appl/doctabstyle.cxx"


class DocTabStyleSchemaContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract, self.contents = VALIDATOR.load_repository(REPOSITORY)

    def failures(
        self, *, contract: dict | None = None, contents: dict[str, str] | None = None
    ) -> list[str]:
        return VALIDATOR.violations(
            self.contract if contract is None else contract,
            self.contents if contents is None else contents,
        )

    def with_content(self, path: str, text: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents[path] = text
        return contents

    def assert_mutation_flagged(self, contents: dict[str, str], token: str) -> None:
        failures = self.failures(contents=contents)
        self.assertTrue(failures, "expected the mutation to fail closed")
        self.assertTrue(
            any(token in f for f in failures),
            f"expected a failure mentioning {token!r}, got:\n" + "\n".join(failures),
        )

    # -- baseline -----------------------------------------------------------

    def test_pristine_tree_passes(self) -> None:
        self.assertEqual(self.failures(), [])

    # -- schema drift -------------------------------------------------------

    def test_font_size_type_drift_fails(self) -> None:
        text = self.contents[SCHEMA].replace(
            '<prop oor:name="FontSize" oor:type="xs:short"',
            '<prop oor:name="FontSize" oor:type="xs:int"',
            1,
        )
        self.assert_mutation_flagged(self.with_content(SCHEMA, text), "FontSize")

    def test_tabsenabled_default_true_fails_closed(self) -> None:
        # Flip TabsEnabled default false -> true (the tabs-on regression).
        marker = '<prop oor:name="TabsEnabled" oor:type="xs:boolean" oor:nillable="false">'
        start = self.contents[SCHEMA].find(marker)
        end = self.contents[SCHEMA].find("</prop>", start)
        block = self.contents[SCHEMA][start:end]
        mutated_block = block.replace("<value>false</value>", "<value>true</value>", 1)
        text = self.contents[SCHEMA][:start] + mutated_block + self.contents[SCHEMA][end:]
        self.assert_mutation_flagged(self.with_content(SCHEMA, text), "fail-closed")

    def test_font_size_clamp_widened_fails(self) -> None:
        text = self.contents[SCHEMA].replace(
            '<maxInclusive oor:value="32">',
            '<maxInclusive oor:value="999">',
            1,
        )
        self.assert_mutation_flagged(self.with_content(SCHEMA, text), "FontSize")

    def test_tabwidth_enum_added_fails(self) -> None:
        # Add an illegal 4th enumeration to the closed TabWidth set.
        scope_start = self.contents[SCHEMA].find('<prop oor:name="TabWidth"')
        scope_end = self.contents[SCHEMA].find("</prop>", scope_start)
        block = self.contents[SCHEMA][scope_start:scope_end]
        mutated = block.replace(
            "</constraints>",
            '  <enumeration oor:value="3">\n            <info>\n              <desc>Bogus</desc>\n            </info>\n          </enumeration>\n        </constraints>',
            1,
        )
        text = (
            self.contents[SCHEMA][:scope_start]
            + mutated
            + self.contents[SCHEMA][scope_end:]
        )
        self.assert_mutation_flagged(self.with_content(SCHEMA, text), "TabWidth")

    def test_order_default_drift_fails(self) -> None:
        scope_start = self.contents[SCHEMA].find('<prop oor:name="Order"')
        scope_end = self.contents[SCHEMA].find("</prop>", scope_start)
        block = self.contents[SCHEMA][scope_start:scope_end]
        mutated = block.replace("<value>0</value>", "<value>5</value>", 1)
        text = (
            self.contents[SCHEMA][:scope_start]
            + mutated
            + self.contents[SCHEMA][scope_end:]
        )
        self.assert_mutation_flagged(self.with_content(SCHEMA, text), "Order")

    # -- normalizer parity --------------------------------------------------

    def test_missing_normalizer_branch_fails(self) -> None:
        # Drop the FontFamily branch key from the normalizer.
        text = self.contents[CXX].replace('rsKey == u"FontFamily"', 'rsKey == u"Dropped"')
        self.assert_mutation_flagged(self.with_content(CXX, text), "FontFamily")

    def test_orphan_normalizer_branch_fails(self) -> None:
        # Add a branch for a key that is not a schema property.
        injection = '    if (rsKey == u"Ghost")\n    {\n        return { false, OUString() };\n    }\n'
        anchor = "    // --- Appearance/DocumentTabs group"
        text = self.contents[CXX].replace(anchor, injection + anchor, 1)
        self.assert_mutation_flagged(self.with_content(CXX, text), "Ghost")

    def test_property_removed_from_schema_but_kept_in_normalizer_fails(self) -> None:
        # Removing a property from the contract while the branch survives means
        # the normalizer has an orphan branch relative to the (mutated) schema.
        contract = copy.deepcopy(self.contract)
        contract["groups"]["DocumentTabStyle"]["properties"] = [
            p
            for p in contract["groups"]["DocumentTabStyle"]["properties"]
            if p["name"] != "Underline"
        ]
        failures = self.failures(contract=contract)
        self.assertTrue(any("Underline" in f for f in failures), failures)


if __name__ == "__main__":
    unittest.main()
