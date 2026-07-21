#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Regression tests for the exhaustive Windows dialog policy contract."""

from __future__ import annotations

import csv
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-windows-dialog-notification-contract.py"
REGISTRY_PATH = REPOSITORY / "qa/windows-ui-contract/dialog-notification-policy.csv"

SPEC = importlib.util.spec_from_file_location(
    "check_windows_dialog_notification_contract", VALIDATOR_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def entry(
    key: object,
    *,
    policy: str = VALIDATOR.NOTIFICATION_POLICY,
    profile: str = VALIDATOR.DEFAULT_NOTIFICATION_PROFILE,
    reason: str = "",
) -> object:
    return VALIDATOR.ContractEntry(key, policy, profile, reason)


class WindowsDialogNotificationContractTest(unittest.TestCase):
    def write_registry(self, rows: list[dict[str, str]]) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "registry.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=VALIDATOR.CSV_FIELDS, lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    @staticmethod
    def row(**overrides: str) -> dict[str, str]:
        values = {
            "ui_path": "module/uiconfig/ui/example.ui",
            "object_id": "ExampleDialog",
            "widget_class": "GtkDialog",
            "policy": VALIDATOR.NOTIFICATION_POLICY,
            "notification_profile": "default",
            "exclusion_reason": "",
        }
        values.update(overrides)
        return values

    def test_production_contract_covers_every_dialog_root(self) -> None:
        report = VALIDATOR.validate_contract(REPOSITORY, REGISTRY_PATH)
        # The wave that added the shared Material destructive-confirmation dialog raised the total to
        # 598 roots. The registry now mirrors the router's KeepModal policy: only acknowledgment-only
        # message boxes route to the notification form, everything else is native-exclusion.
        self.assertEqual(598, report.total)
        self.assertEqual(
            {"GtkDialog": 521, "GtkMessageDialog": 76, "GtkAssistant": 1},
            dict(report.classes),
        )
        self.assertEqual(
            {VALIDATOR.NOTIFICATION_POLICY: 9, VALIDATOR.EXCLUSION_POLICY: 589},
            dict(report.policies),
        )
        self.assertEqual({"default": 9}, dict(report.profiles))
        # The exclusion set must dominate: the notification form is the narrow, affirmatively
        # informational slice, never the default.
        self.assertGreater(
            report.policies[VALIDATOR.EXCLUSION_POLICY],
            report.policies[VALIDATOR.NOTIFICATION_POLICY],
        )

    def test_discovery_selects_only_top_level_dialog_classes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dialog = root / "dialog.ui"
            message = root / "message.ui"
            ignored = root / "ignored.ui"
            dialog.write_text(
                '<interface><object class="GtkDialog" id="Dialog"/></interface>',
                encoding="utf-8",
            )
            message.write_text(
                '<interface><object class="GtkMessageDialog" id="Message"/></interface>',
                encoding="utf-8",
            )
            ignored.write_text(
                '<interface><object class="GtkWindow" id="Window">'
                '<child><object class="GtkDialog" id="Nested"/></child>'
                '</object></interface>',
                encoding="utf-8",
            )
            discovered = VALIDATOR.discover_dialogs(
                root, [dialog, message, ignored]
            )
        self.assertEqual(
            [
                VALIDATOR.DialogKey("dialog.ui", "Dialog", "GtkDialog"),
                VALIDATOR.DialogKey(
                    "message.ui", "Message", "GtkMessageDialog"
                ),
            ],
            discovered,
        )

    def test_worktree_deletion_is_absent_during_registry_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "--quiet", str(root)], check=True)
            deleted = root / "deleted.ui"
            deleted.write_text(
                '<interface><object class="GtkDialog" id="Deleted"/></interface>',
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "-C", str(root), "add", "--", "deleted.ui"], check=True
            )
            deleted.unlink()
            self.assertEqual([], VALIDATOR.repository_ui_paths(root))

    def test_rejects_source_addition_missing_from_registry(self) -> None:
        key = VALIDATOR.DialogKey("module/uiconfig/ui/new.ui", "New", "GtkDialog")
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "source dialog.*missing from policy registry"
        ):
            VALIDATOR.compare_contract([key], [])

    def test_rejects_registry_omission_or_deleted_source(self) -> None:
        key = VALIDATOR.DialogKey("module/uiconfig/ui/old.ui", "Old", "GtkDialog")
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "registry entry.*without matching source dialog"
        ):
            VALIDATOR.compare_contract([], [entry(key)])

    def test_widget_class_change_is_contract_drift(self) -> None:
        old = VALIDATOR.DialogKey(
            "module/uiconfig/ui/example.ui", "Example", "GtkDialog"
        )
        new = VALIDATOR.DialogKey(
            "module/uiconfig/ui/example.ui", "Example", "GtkMessageDialog"
        )
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "missing from policy registry"
        ):
            VALIDATOR.compare_contract([new], [entry(old)])

    def test_rejects_duplicate_registry_locator(self) -> None:
        rows = [self.row(), self.row(widget_class="GtkMessageDialog")]
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "duplicate registry dialog locator"
        ):
            VALIDATOR.read_registry(self.write_registry(rows))

    def test_notification_policy_requires_explicit_profile(self) -> None:
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError,
            "notification policy requires a slug-like notification_profile",
        ):
            VALIDATOR.read_registry(
                self.write_registry([self.row(notification_profile="")])
            )

    def test_exclusion_requires_reason_and_forbids_profile(self) -> None:
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "native exclusion requires an exclusion_reason"
        ):
            VALIDATOR.read_registry(
                self.write_registry(
                    [
                        self.row(
                            policy=VALIDATOR.EXCLUSION_POLICY,
                            notification_profile="",
                        )
                    ]
                )
            )
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError,
            "native exclusion cannot have a notification_profile",
        ):
            VALIDATOR.read_registry(
                self.write_registry(
                    [
                        self.row(
                            policy=VALIDATOR.EXCLUSION_POLICY,
                            exclusion_reason="Platform picker owned by Windows",
                        )
                    ]
                )
            )

    def test_rejects_unknown_or_implicit_policy(self) -> None:
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "unsupported explicit policy"
        ):
            VALIDATOR.read_registry(self.write_registry([self.row(policy="")]))

    def test_update_defaults_new_dialog_and_preserves_reviewed_exclusion(self) -> None:
        existing_key = VALIDATOR.DialogKey(
            "module/uiconfig/ui/existing.ui", "Existing", "GtkAssistant"
        )
        new_key = VALIDATOR.DialogKey(
            "module/uiconfig/ui/new.ui", "New", "GtkDialog"
        )
        existing = entry(
            existing_key,
            policy=VALIDATOR.EXCLUSION_POLICY,
            profile="",
            reason="Native shell owns this flow",
        )
        merged = VALIDATOR.merge_entries([new_key, existing_key], [existing])
        by_key = {item.key: item for item in merged}
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, by_key[existing_key].policy)
        self.assertEqual(
            VALIDATOR.NOTIFICATION_POLICY, by_key[new_key].policy
        )
        self.assertEqual("default", by_key[new_key].notification_profile)

    def test_registry_must_be_deterministically_sorted(self) -> None:
        rows = [
            self.row(ui_path="z/uiconfig/ui/z.ui", object_id="Z"),
            self.row(ui_path="a/uiconfig/ui/a.ui", object_id="A"),
        ]
        with self.assertRaisesRegex(
            VALIDATOR.ValidationError, "registry rows must be sorted"
        ):
            VALIDATOR.read_registry(self.write_registry(rows))


class RoutingClassifierTest(unittest.TestCase):
    """The classifier mirrors sfx2::NotificationRouter::Classify: input / destructive / credential /
    security stay modal; only acknowledgment-only message boxes route to the notification form."""

    def classify(self, widget_class: str, inner: str, *, ui_path="m/uiconfig/ui/x.ui", oid="X"):
        xml = f'<interface><object class="{widget_class}" id="{oid}">{inner}</object></interface>'
        return VALIDATOR.classify_ui_text(ui_path, oid, widget_class, xml)

    def test_input_entry_keeps_modal(self) -> None:
        policy, reason = self.classify(
            "GtkDialog", '<child><object class="GtkEntry" id="e"/></child>'
        )
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)
        self.assertIn("collects input", reason)

    def test_treeview_input_keeps_modal(self) -> None:
        policy, _ = self.classify(
            "GtkDialog", '<child><object class="GtkTreeView" id="t"/></child>'
        )
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)

    def test_password_entry_is_credential(self) -> None:
        policy, reason = self.classify(
            "GtkDialog",
            '<child><object class="GtkEntry" id="pw">'
            '<property name="visibility">False</property></object></child>',
        )
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)
        self.assertIn("credentials", reason)

    def test_destructive_token_keeps_modal(self) -> None:
        policy, reason = self.classify(
            "GtkMessageDialog", "", ui_path="m/uiconfig/ui/deletestuff.ui", oid="DeleteDialog"
        )
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)
        self.assertIn("destructive", reason)

    def test_security_token_keeps_modal(self) -> None:
        policy, reason = self.classify(
            "GtkDialog", "", ui_path="m/uiconfig/ui/macrosecurity.ui", oid="SecurityDialog"
        )
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)
        self.assertIn("security", reason)

    def test_acknowledgment_only_message_routes_to_notification(self) -> None:
        policy, reason = self.classify(
            "GtkMessageDialog", '<property name="buttons">ok</property>'
        )
        self.assertEqual(VALIDATOR.NOTIFICATION_POLICY, policy)
        self.assertEqual("", reason)

    def test_close_only_message_routes_to_notification(self) -> None:
        policy, _ = self.classify(
            "GtkMessageDialog", '<property name="buttons">close</property>'
        )
        self.assertEqual(VALIDATOR.NOTIFICATION_POLICY, policy)

    def test_yes_no_message_stays_modal(self) -> None:
        policy, reason = self.classify(
            "GtkMessageDialog", '<property name="buttons">yes-no</property>'
        )
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)
        self.assertIn("decision", reason)

    def test_runtime_supplied_buttons_stay_modal(self) -> None:
        # No 'buttons' property and no action-widgets: the button set is built at the C++ call site,
        # so the dialog cannot be cleared as informational. Fail safe -> keep modal.
        policy, _ = self.classify("GtkMessageDialog", "")
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)

    def test_plain_gtkdialog_shell_stays_modal(self) -> None:
        policy, reason = self.classify("GtkDialog", "")
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)
        self.assertIn("interactive", reason)

    def test_ok_cancel_message_stays_modal(self) -> None:
        policy, _ = self.classify(
            "GtkMessageDialog", '<property name="buttons">ok-cancel</property>'
        )
        self.assertEqual(VALIDATOR.EXCLUSION_POLICY, policy)

    def test_ack_action_widgets_route_to_notification(self) -> None:
        # Explicit ok/help action-widgets are an acknowledgment, help is not a decision.
        xml = (
            '<interface><object class="GtkMessageDialog" id="X">'
            "<action-widgets>"
            '<action-widget response="-5">ok</action-widget>'
            '<action-widget response="-11">help</action-widget>'
            "</action-widgets></object></interface>"
        )
        policy, _ = VALIDATOR.classify_ui_text("m/uiconfig/ui/x.ui", "X", "GtkMessageDialog", xml)
        self.assertEqual(VALIDATOR.NOTIFICATION_POLICY, policy)


if __name__ == "__main__":
    unittest.main()
