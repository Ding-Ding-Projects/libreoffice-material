#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for the WIN-SYS-016 registered UI inventory closure.

Every way the ledger can drift from a fresh enumeration must fail closed:
added, removed, or renamed ``.ui`` surfaces, a newly unassigned surface beyond
the checked-in baseline, an unknown inventory ID, a duplicated surface, and a
hand-edited mapping.

The mapping-table and registry-file guards are exercised branch by branch too:
a prefix rule without a trailing slash or duplicated, a native surface that is
mis-keyed, duplicated, missing an owner or note, or naming an unknown row, a
native key colliding with a ``.ui`` key, and a registry file that is
unreadable, not JSON, not an object, or structurally malformed.
"""

from __future__ import annotations

import copy
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-windows-ui-registry-closure.py"
REGISTRY_PATH = REPOSITORY / "qa/windows-ui-contract/ui-registry.json"

SPEC = importlib.util.spec_from_file_location(
    "check_windows_ui_registry_closure", VALIDATOR_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class WindowsUiRegistryClosureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.valid_ids = VALIDATOR.parse_valid_inventory_ids(
            REPOSITORY / "docs/WINDOWS_UI_INVENTORY.md"
        )
        self.expected = VALIDATOR.build_registry(REPOSITORY, self.valid_ids)

    # -- production ledger and invariants -----------------------------------

    def test_checked_in_registry_matches_fresh_enumeration(self) -> None:
        registry = VALIDATOR.validate_contract(REPOSITORY, REGISTRY_PATH)
        counts = registry["counts"]
        self.assertEqual(
            counts["assigned"] + counts["unassigned"], counts["total_surfaces"]
        )
        self.assertEqual(
            counts["ui_surfaces"] + counts["native_surfaces"],
            counts["total_surfaces"],
        )
        self.assertEqual(counts["native_surfaces"], len(VALIDATOR.NATIVE_SURFACES))
        # A sanity floor: the tree contains well over a thousand .ui surfaces.
        self.assertGreaterEqual(counts["ui_surfaces"], 1000)

    def test_every_mapped_surface_uses_a_real_inventory_row(self) -> None:
        for surface in self.expected["surfaces"] + self.expected["native_surfaces"]:
            inventory_id = surface["inventory_id"]
            if inventory_id != VALIDATOR.UNASSIGNED:
                self.assertIn(inventory_id, self.valid_ids)

    def test_every_surface_has_exactly_one_owner(self) -> None:
        for surface in self.expected["surfaces"] + self.expected["native_surfaces"]:
            self.assertTrue(surface["owner"])
            self.assertIsInstance(surface["owner"], str)

    def test_notification_surfaces_are_registered_together(self) -> None:
        ids = {
            surface["surface"]: surface["inventory_id"]
            for surface in self.expected["surfaces"]
            + self.expected["native_surfaces"]
        }
        for notification in (
            "sfx2/uiconfig/ui/notificationcard.ui",
            "sfx2/uiconfig/ui/notificationmanager.ui",
            "sfx2/uiconfig/ui/notificationstack.ui",
            "native:notification-overlay-window",
        ):
            self.assertEqual(ids.get(notification), "WIN-SHL-003")

    def test_generation_is_deterministic(self) -> None:
        again = VALIDATOR.build_registry(REPOSITORY, self.valid_ids)
        self.assertEqual(
            VALIDATOR.serialize_registry(self.expected),
            VALIDATOR.serialize_registry(again),
        )

    # -- owner and inventory mapping ----------------------------------------

    def test_owner_is_the_first_path_segment(self) -> None:
        self.assertEqual(
            "sfx2",
            VALIDATOR.owner_for_ui_path("sfx2/uiconfig/ui/startcenter.ui"),
        )

    def test_override_wins_over_prefix(self) -> None:
        inventory_id, mapped_by = VALIDATOR.inventory_for_ui_path(
            "sfx2/uiconfig/ui/startcenter.ui"
        )
        self.assertEqual(("WIN-SC-001", "override"), (inventory_id, mapped_by))

    def test_longest_prefix_wins(self) -> None:
        inventory_id, mapped_by = VALIDATOR.inventory_for_ui_path(
            "sd/uiconfig/simpress/ui/whatever.ui"
        )
        self.assertEqual(("WIN-IM-001", "prefix"), (inventory_id, mapped_by))

    def test_unmapped_surface_is_unassigned(self) -> None:
        inventory_id, mapped_by = VALIDATOR.inventory_for_ui_path(
            "cui/uiconfig/ui/somethingunmapped.ui"
        )
        self.assertEqual((VALIDATOR.UNASSIGNED, "unassigned"), (inventory_id, mapped_by))

    # -- drift: added / removed / renamed / hand-edited ---------------------

    def _assigned_key(self) -> str:
        for surface in self.expected["surfaces"]:
            if surface["inventory_id"] != VALIDATOR.UNASSIGNED:
                return surface["surface"]
        raise AssertionError("no assigned surface in the ledger")

    def _unassigned_key(self) -> str:
        for surface in self.expected["surfaces"]:
            if surface["inventory_id"] == VALIDATOR.UNASSIGNED:
                return surface["surface"]
        raise AssertionError("no unassigned surface in the ledger")

    def test_added_ui_surface_fails_closed(self) -> None:
        # Source gains a .ui the checked-in registry does not list.
        key = self._assigned_key()
        actual = copy.deepcopy(self.expected)
        actual["surfaces"] = [
            s for s in actual["surfaces"] if s["surface"] != key
        ]
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "missing from registry"
        ):
            VALIDATOR.compare_registry(self.expected, actual)

    def test_removed_ui_surface_fails_closed(self) -> None:
        # Registry lists a surface the source no longer provides.
        actual = copy.deepcopy(self.expected)
        actual["surfaces"].append(
            {
                "kind": "ui-file",
                "surface": "zzz/uiconfig/ui/ghost.ui",
                "owner": "zzz",
                "inventory_id": VALIDATOR.UNASSIGNED,
                "mapped_by": "unassigned",
            }
        )
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "no matching source surface"
        ):
            VALIDATOR.compare_registry(self.expected, actual)

    def test_renamed_ui_surface_fails_closed(self) -> None:
        key = self._assigned_key()
        actual = copy.deepcopy(self.expected)
        for surface in actual["surfaces"]:
            if surface["surface"] == key:
                surface["surface"] = key.replace(".ui", "-renamed.ui")
                break
        with self.assertRaises(VALIDATOR.ValidationError) as caught:
            VALIDATOR.compare_registry(self.expected, actual)
        message = str(caught.exception)
        self.assertIn("missing from registry", message)
        self.assertIn("no matching source surface", message)

    def test_new_unassigned_surface_beyond_baseline_fails_closed(self) -> None:
        # A fresh unassigned surface that the checked-in baseline never recorded.
        key = self._unassigned_key()
        actual = copy.deepcopy(self.expected)
        actual["surfaces"] = [
            s for s in actual["surfaces"] if s["surface"] != key
        ]
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError,
            "new unassigned ui-file surface.*beyond the checked-in baseline",
        ):
            VALIDATOR.compare_registry(self.expected, actual)

    def test_hand_edited_inventory_id_fails_closed(self) -> None:
        key = self._assigned_key()
        actual = copy.deepcopy(self.expected)
        for surface in actual["surfaces"]:
            if surface["surface"] == key:
                surface["inventory_id"] = "WIN-SYS-016"
                break
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "drifted from its generated mapping"
        ):
            VALIDATOR.compare_registry(self.expected, actual)

    def test_hand_edited_owner_fails_closed(self) -> None:
        key = self._assigned_key()
        actual = copy.deepcopy(self.expected)
        for surface in actual["surfaces"]:
            if surface["surface"] == key:
                surface["owner"] = "not-the-real-module"
                break
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "drifted from its generated mapping"
        ):
            VALIDATOR.compare_registry(self.expected, actual)

    def test_hand_edited_counts_fail_closed(self) -> None:
        actual = copy.deepcopy(self.expected)
        actual["counts"]["unassigned"] = 0
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "counts.*drifted"
        ):
            VALIDATOR.compare_registry(self.expected, actual)

    # -- unknown inventory ID -----------------------------------------------

    def test_unknown_inventory_id_in_mapping_fails_closed(self) -> None:
        # Drop a genuinely-used row from the valid set: the mapping now points
        # at an ID the inventory document does not define.
        crippled = frozenset(self.valid_ids - {"WIN-SC-001"})
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "unknown inventory ID 'WIN-SC-001'"
        ):
            VALIDATOR.validate_mapping_tables(crippled)

    def test_build_registry_rejects_unknown_inventory_id(self) -> None:
        crippled = frozenset(self.valid_ids - {"WIN-WR-001"})
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "unknown inventory ID"
        ):
            VALIDATOR.build_registry(REPOSITORY, crippled)

    # -- prefix-rule table integrity ----------------------------------------

    def test_prefix_rule_without_trailing_slash_fails_closed(self) -> None:
        # A prefix that does not end with '/' would match on a partial segment.
        bad = (("sw", "WIN-WR-001"),)
        with mock.patch.object(VALIDATOR, "PREFIX_RULES", bad):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "must end with '/'"
            ):
                VALIDATOR.validate_mapping_tables(self.valid_ids)

    def test_duplicate_prefix_rule_fails_closed(self) -> None:
        bad = (("sw/", "WIN-WR-001"), ("sw/", "WIN-WR-001"))
        with mock.patch.object(VALIDATOR, "PREFIX_RULES", bad):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "duplicate prefix rule"
            ):
                VALIDATOR.validate_mapping_tables(self.valid_ids)

    # -- duplicate surface / owner ------------------------------------------

    def test_duplicate_surface_fails_closed(self) -> None:
        duplicate = self.expected["surfaces"][0]
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "duplicate surface entry"
        ):
            VALIDATOR._check_unique_surfaces([duplicate, dict(duplicate)])

    def test_duplicate_surface_in_registry_fails_closed(self) -> None:
        actual = copy.deepcopy(self.expected)
        actual["surfaces"].append(copy.deepcopy(actual["surfaces"][0]))
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "duplicate surface entry in registry"
        ):
            VALIDATOR.compare_registry(self.expected, actual)

    # -- native surface discipline ------------------------------------------

    def test_native_surface_key_must_be_prefixed(self) -> None:
        bad = ({"surface": "start-center", "owner": "sfx2",
                "inventory_id": "WIN-SC-005", "note": "x"},)
        with mock.patch.object(VALIDATOR, "NATIVE_SURFACES", bad):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "must use a 'native:' key"
            ):
                VALIDATOR.validate_mapping_tables(self.valid_ids)

    def test_native_surface_requires_owner_and_note(self) -> None:
        bad = ({"surface": "native:x", "owner": "", "inventory_id": "WIN-SC-005",
                "note": "x"},)
        with mock.patch.object(VALIDATOR, "NATIVE_SURFACES", bad):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "has no owner"
            ):
                VALIDATOR.validate_mapping_tables(self.valid_ids)

    def test_native_surface_missing_note_fails_closed(self) -> None:
        # Owner is present, so the note branch is the one that must reject.
        bad = ({"surface": "native:x", "owner": "sfx2",
                "inventory_id": "WIN-SC-005", "note": ""},)
        with mock.patch.object(VALIDATOR, "NATIVE_SURFACES", bad):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "has no note"
            ):
                VALIDATOR.validate_mapping_tables(self.valid_ids)

    def test_native_surface_unknown_inventory_id_fails_closed(self) -> None:
        bad = ({"surface": "native:x", "owner": "sfx2",
                "inventory_id": "WIN-NOPE-999", "note": "n"},)
        with mock.patch.object(VALIDATOR, "NATIVE_SURFACES", bad):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError,
                "native surface 'native:x' names unknown inventory ID",
            ):
                VALIDATOR.validate_mapping_tables(self.valid_ids)

    def test_duplicate_native_surface_fails_closed(self) -> None:
        entry = {"surface": "native:x", "owner": "sfx2",
                 "inventory_id": "WIN-SC-005", "note": "n"}
        bad = (dict(entry), dict(entry))
        with mock.patch.object(VALIDATOR, "NATIVE_SURFACES", bad):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "duplicate native surface"
            ):
                VALIDATOR.validate_mapping_tables(self.valid_ids)

    def test_native_key_colliding_with_ui_surface_fails_closed(self) -> None:
        # A native key that (defensively) equals a .ui surface key must fail the
        # closure. The key must start with 'native:' to clear the mapping-table
        # guard, so the collision is forced through a stubbed .ui enumeration.
        native = ({"surface": "native:collide", "owner": "sfx2",
                   "inventory_id": "WIN-SC-005", "note": "n"},)
        fake_ui = [{"kind": "ui-file", "surface": "native:collide",
                    "owner": "native", "inventory_id": VALIDATOR.UNASSIGNED,
                    "mapped_by": "unassigned"}]
        with mock.patch.object(VALIDATOR, "NATIVE_SURFACES", native), \
                mock.patch.object(
                    VALIDATOR, "build_ui_surfaces", return_value=fake_ui
                ):
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError,
                "native surface key collides with a .ui surface",
            ):
                VALIDATOR.build_registry(REPOSITORY, self.valid_ids)

    # -- registry file structure guards -------------------------------------

    def test_read_registry_unreadable_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "does-not-exist.json"
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "cannot read registry"
            ):
                VALIDATOR.read_registry(missing)

    def test_read_registry_invalid_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{not valid json", encoding="utf-8")
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "is not valid JSON"
            ):
                VALIDATOR.read_registry(path)

    def test_read_registry_non_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "list.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "must be a JSON object"
            ):
                VALIDATOR.read_registry(path)

    def test_surface_index_rejects_non_list(self) -> None:
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "surfaces section must be a list"
        ):
            VALIDATOR._surface_index("not-a-list")

    def test_surface_index_rejects_malformed_entry(self) -> None:
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "surface entry is malformed"
        ):
            VALIDATOR._surface_index([{"no_surface_key": 1}])

    def test_surface_index_rejects_non_string_key(self) -> None:
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "surface key must be a string"
        ):
            VALIDATOR._surface_index([{"surface": 123}])

    def test_validate_surface_ids_rejects_unknown_id(self) -> None:
        # Direct coverage of the defensive per-surface ID check. Surfaces built
        # from the mapping tables are pre-validated by validate_mapping_tables,
        # so this guards a future caller that assembles surfaces another way.
        surfaces = [{"surface": "x/y.ui", "inventory_id": "WIN-NOPE-999"}]
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "maps to unknown inventory ID"
        ):
            VALIDATOR._validate_surface_ids(surfaces, self.valid_ids)

    def test_validate_surface_ids_skips_unassigned(self) -> None:
        surfaces = [{"surface": "x/y.ui", "inventory_id": VALIDATOR.UNASSIGNED}]
        VALIDATOR._validate_surface_ids(surfaces, self.valid_ids)

    # -- inventory-document parsing -----------------------------------------

    def test_inventory_ids_include_the_registry_row(self) -> None:
        self.assertIn("WIN-SYS-016", self.valid_ids)
        self.assertGreater(len(self.valid_ids), 100)

    def test_empty_inventory_document_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            doc = Path(directory) / "empty.md"
            doc.write_text("# no rows here\n", encoding="utf-8")
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, "no WIN- inventory rows"
            ):
                VALIDATOR.parse_valid_inventory_ids(doc)

    # -- git-walk discipline ------------------------------------------------

    def test_worktree_deletion_is_absent_from_enumeration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            deleted = root / "gone.ui"
            deleted.write_text("<interface/>", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", "--", "gone.ui"], check=True
            )
            deleted.unlink()
            self.assertEqual([], VALIDATOR.repository_ui_paths(root))


if __name__ == "__main__":
    unittest.main()
