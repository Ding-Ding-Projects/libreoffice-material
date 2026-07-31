#!/usr/bin/env python3
"""Mutation regressions for the Material updater lifecycle contract."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-updater-lifecycle-composition.py"
SPEC = importlib.util.spec_from_file_location("check_updater_lifecycle_composition", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)

UI = "extensions/source/update/ui/updatecheckui.cxx"
CONTROLLER = "extensions/source/update/check/updatecheck.cxx"
HANDLER = "extensions/source/update/check/updatehdl.cxx"
STRINGS = "extensions/inc/strings.hrc"
MAKEFILE = "extensions/Library_updatecheckui.mk"
PRODUCERS = "qa/windows-ui-contract/notification-producer-policy.json"


class UpdaterLifecycleCompositionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract, self.contents = VALIDATOR.load_repository(REPOSITORY)

    def failures(self, contract=None, contents=None) -> list[str]:
        return VALIDATOR.violations(
            self.contract if contract is None else contract,
            self.contents if contents is None else contents,
        )

    def changed(self, path: str, text: str) -> dict[str, str]:
        contents = dict(self.contents)
        contents[path] = text
        return contents

    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)

    def test_contract_marker_drift_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["contract"] = "wrong"
        self.assertTrue(any("contract:marker" in error for error in self.failures(contract=contract)))

    def test_runtime_claim_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["runtime_verified"] = True
        self.assertTrue(any("runtime_verified" in error for error in self.failures(contract=contract)))

    def test_invented_release_code_name_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["release_code_name"]["invented"] = True
        self.assertTrue(any("release_code_name" in error for error in self.failures(contract=contract)))

    def test_state_map_loss_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        del contract["states"]["error-downloading"]
        self.assertTrue(any("contract:states" in error for error in self.failures(contract=contract)))

    def test_quiet_no_update_policy_drift_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["emission_policy"]["no_update"] = "emit a success card"
        self.assertTrue(
            any("emission_policy" in error for error in self.failures(contract=contract))
        )

    def test_severity_policy_drift_fails(self) -> None:
        source = self.contents[UI].replace(
            "return sfx2::NotificationSeverity::Success;",
            "return sfx2::NotificationSeverity::Information;",
            1,
        )
        self.assertTrue(any("severity" in error for error in self.failures(contents=self.changed(UI, source))))

    def test_main_thread_handoff_removed_fails(self) -> None:
        source = self.contents[UI].replace(
            "Application::PostUserEvent(LINK(nullptr, UpdateCheckUI, NotifyLifecycleHdl)",
            "Application::PostUserEvent(Link<void*, void>()",
            1,
        )
        self.assertTrue(any("handoff" in error or "missing marker" in error for error in self.failures(contents=self.changed(UI, source))))

    def test_legacy_bubble_reenabled_fails(self) -> None:
        source = self.contents[UI].replace(
            "maBubbleManager.SetShowBubble(false);",
            "maBubbleManager.SetShowBubble(bShowBubble);",
            1,
        )
        self.assertTrue(any("legacy bubble" in error or "missing marker" in error for error in self.failures(contents=self.changed(UI, source))))

    def test_lifecycle_state_handoff_removed_fails(self) -> None:
        source = self.contents[CONTROLLER].replace(
            "xMenuBarUI->setPropertyValue(PROPERTY_LIFECYCLE_STATE,",
            "xMenuBarUI->setPropertyValue(PROPERTY_TITLE,",
            1,
        )
        self.assertTrue(any("controller:menu" in error or "missing marker" in error for error in self.failures(contents=self.changed(CONTROLLER, source))))

    def test_version_set_after_notification_fails(self) -> None:
        source = self.contents[CONTROLLER].replace(
            "aUpdateHandler->setNextVersion(aUpdateInfo.Version);\n"
            "    handleMenuBarUI(aUpdateHandler, xMenuBarUI, eState, suppressBubble);",
            "handleMenuBarUI(aUpdateHandler, xMenuBarUI, eState, suppressBubble);\n"
            "    aUpdateHandler->setNextVersion(aUpdateInfo.Version);",
            1,
        )
        self.assertTrue(any("set-state" in error for error in self.failures(contents=self.changed(CONTROLLER, source))))

    def test_same_state_dedupe_removed_fails(self) -> None:
        source = self.contents[CONTROLLER].replace(
            "if ( eState == m_eUpdateState )",
            "if ( false )",
            1,
        )
        self.assertTrue(any("set-state" in error or "missing marker" in error for error in self.failures(contents=self.changed(CONTROLLER, source))))

    def test_check_error_notification_disabled_fails(self) -> None:
        source = self.contents[CONTROLLER].replace(
            "(UPDATESTATE_CHECKING != eState)\n    )",
            "(UPDATESTATE_CHECKING != eState) &&\n        (UPDATESTATE_ERROR_CHECKING != eState)\n    )",
            1,
        )
        self.assertTrue(any("checking errors" in error for error in self.failures(contents=self.changed(CONTROLLER, source))))

    def test_version_copy_removed_fails(self) -> None:
        source = self.contents[STRINGS].replace("%NEXTVERSION", "%PRODUCTVERSION")
        self.assertTrue(any("strings:version" in error for error in self.failures(contents=self.changed(STRINGS, source))))

    def test_progress_copy_removed_fails(self) -> None:
        source = self.contents[STRINGS].replace("%PERCENT%", "the last checkpoint")
        self.assertTrue(any("strings:progress" in error for error in self.failures(contents=self.changed(STRINGS, source))))

    def test_retry_copy_removed_fails(self) -> None:
        source = self.contents[STRINGS].replace("retry automatically", "stop without retry")
        self.assertTrue(any("strings:retry" in error for error in self.failures(contents=self.changed(STRINGS, source))))

    def test_rollback_owner_copy_removed_fails(self) -> None:
        source = self.contents[STRINGS].replace(
            "Windows Installer reports completion or rollback status",
            "Installation status is available elsewhere",
            1,
        )
        self.assertTrue(any("strings:rollback" in error for error in self.failures(contents=self.changed(STRINGS, source))))

    def test_default_no_removed_fails(self) -> None:
        source = self.contents[HANDLER].replace(
            "awt::VclWindowPeerAttribute::DEF_NO",
            "awt::VclWindowPeerAttribute::DEF_YES",
            1,
        )
        self.assertTrue(any("default-No" in error or "missing marker" in error for error in self.failures(contents=self.changed(HANDLER, source))))

    def test_prelaunch_verification_removed_fails(self) -> None:
        source = self.contents[CONTROLLER].replace(
            "verifyUpdateFile(aInstallerURL, aSource)",
            "verifyUpdateFile(OUString(), aSource)",
            1,
        )
        self.assertTrue(any("install" in error or "missing marker" in error for error in self.failures(contents=self.changed(CONTROLLER, source))))

    def test_restart_suppression_removed_fails(self) -> None:
        source = self.contents[CONTROLLER].replace(
            'u"REBOOT=ReallySuppress"_ustr',
            'u"REBOOT=Force"_ustr',
            1,
        )
        self.assertTrue(any("command" in error or "missing marker" in error for error in self.failures(contents=self.changed(CONTROLLER, source))))

    def test_sfx_link_removed_fails(self) -> None:
        source = self.contents[MAKEFILE].replace("\tsfx \\\n", "", 1)
        self.assertTrue(any("makefile" in error or "missing marker" in error for error in self.failures(contents=self.changed(MAKEFILE, source))))

    def test_registered_producer_removed_fails(self) -> None:
        source = self.contents[PRODUCERS].replace(
            '"id": "updater-lifecycle-status"',
            '"id": "updater-lifecycle-disabled"',
            1,
        )
        self.assertTrue(any("producer-policy" in error or "missing marker" in error for error in self.failures(contents=self.changed(PRODUCERS, source))))


if __name__ == "__main__":
    unittest.main()
