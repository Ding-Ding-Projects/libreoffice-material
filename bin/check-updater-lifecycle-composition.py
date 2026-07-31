#!/usr/bin/env python3
"""Fail-closed source contract for the Material updater lifecycle (WIN-SYS-012)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "qa/windows-ui-contract/updater-lifecycle-composition.json"

EXPECTED_STATES = {
    "checking": "Information",
    "error-checking": "Error",
    "no-update": "Information",
    "update-available": "Information",
    "manual-download": "Information",
    "auto-start": "Information",
    "downloading": "Information",
    "download-paused": "Warning",
    "error-downloading": "Error",
    "download-available": "Success",
    "extension-update": "Information",
}

EXPECTED_ENUM_STATES = {
    "UPDATESTATE_CHECKING": "checking",
    "UPDATESTATE_ERROR_CHECKING": "error-checking",
    "UPDATESTATE_NO_UPDATE_AVAIL": "no-update",
    "UPDATESTATE_UPDATE_AVAIL": "update-available",
    "UPDATESTATE_UPDATE_NO_DOWNLOAD": "manual-download",
    "UPDATESTATE_AUTO_START": "auto-start",
    "UPDATESTATE_DOWNLOADING": "downloading",
    "UPDATESTATE_DOWNLOAD_PAUSED": "download-paused",
    "UPDATESTATE_ERROR_DOWNLOADING": "error-downloading",
    "UPDATESTATE_DOWNLOAD_AVAIL": "download-available",
    "UPDATESTATE_EXT_UPD_AVAIL": "extension-update",
}

EXPECTED_PRESERVED = {
    "update icon remains the details and action entry point",
    "same-state progress callbacks do not create notification spam",
    "install consent remains modal and defaults to No",
    "download bytes are reverified before protected non-overwriting staging",
    "the staged MSI remains write-delete locked across launch",
    "Windows Installer stays interactive and owns completion and rollback status",
    "restart and Restart Manager shutdown requests remain suppressed",
    "no release code name is invented without a bundled verified catalog",
}

EXPECTED_EMISSION_POLICY = {
    "trigger": "BubbleVisible=true while the update dialog is hidden or minimized",
    "checking": "silent automatic path",
    "no_update": "silent and hides the update icon",
    "same_state_progress": "suppressed",
    "note": (
        "All eleven states have stable names and severities, but the existing updater suppression "
        "policy intentionally emits cards only for actionable or exceptional transitions. A routine "
        "check and a routine no-update result remain quiet."
    ),
}


class ValidationError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _without_comments(source: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", source, flags=re.DOTALL)


def _function_body(source: str, signature: str) -> str | None:
    start = source.find(signature)
    if start < 0:
        return None
    opening = source.find("{", start + len(signature))
    if opening < 0:
        return None
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    return None


def _ordered(body: str | None, markers: Sequence[str]) -> bool:
    if body is None:
        return False
    cursor = -1
    for marker in markers:
        cursor = body.find(marker, cursor + 1)
        if cursor < 0:
            return False
    return True


def load_repository(repo: Path = REPOSITORY) -> tuple[dict[str, Any], dict[str, str]]:
    contract = _json(repo / CONTRACT_PATH)
    contents: dict[str, str] = {}
    for source in contract.get("sources", []) or []:
        if not isinstance(source, dict):
            continue
        relative = source.get("path")
        if isinstance(relative, str) and (repo / relative).is_file():
            contents[relative] = (repo / relative).read_text(encoding="utf-8")
    return contract, contents


def violations(contract: Mapping[str, Any], contents: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != 1:
        errors.append("contract:schema_version:must be 1")
    if contract.get("contract") != "material-updater-lifecycle-composition":
        errors.append("contract:marker:unexpected value")
    if contract.get("platform") != "windows" or contract.get("owner") != "extensions":
        errors.append("contract:platform-or-owner:drift")
    if contract.get("surface") != "native:updater-lifecycle-ui":
        errors.append("contract:surface:unexpected value")
    if contract.get("inventory_id") != "WIN-SYS-012":
        errors.append("contract:inventory:unexpected value")
    if contract.get("status") != "source-implemented":
        errors.append("contract:status:must be source-implemented")
    if contract.get("runtime_verified") is not False:
        errors.append("contract:runtime_verified:must remain false")
    if contract.get("notification_source") != "libreoffice.update":
        errors.append("contract:notification_source:must use the approved updater source")
    if contract.get("lifecycle_state_property") != "LifecycleState":
        errors.append("contract:lifecycle_state_property:drift")
    if contract.get("states") != EXPECTED_STATES:
        errors.append("contract:states:complete lifecycle/severity map required")
    if contract.get("emission_policy") != EXPECTED_EMISSION_POLICY:
        errors.append("contract:emission_policy:quiet checking/no-update and dedupe policy required")

    code_name = contract.get("release_code_name")
    if not isinstance(code_name, Mapping) or code_name.get("status") != "unavailable-no-bundled-catalog":
        errors.append("contract:release_code_name:unavailable catalog status required")
    elif code_name.get("fallback") != "version-only" or code_name.get("invented") is not False:
        errors.append("contract:release_code_name:must fall back to exact version without invention")

    decision = contract.get("install_decision")
    if not isinstance(decision, Mapping):
        errors.append("contract:install_decision:missing")
    else:
        if decision.get("modal") is not True or decision.get("default") != "No":
            errors.append("contract:install_decision:must remain modal default-No")
        if decision.get("requires_verified_staged_msi") is not True:
            errors.append("contract:install_decision:verified staging required")
        if decision.get("restart_suppression") != [
            "REBOOT=ReallySuppress",
            "MSIRESTARTMANAGERCONTROL=DisableShutdown",
        ]:
            errors.append("contract:install_decision:restart suppression drift")

    sources = contract.get("sources")
    if not isinstance(sources, list) or len(sources) != 7:
        errors.append("contract:sources:exactly seven source entries required")
        sources = []
    for source in sources:
        if not isinstance(source, Mapping):
            errors.append("contract:sources:entry must be an object")
            continue
        path = source.get("path")
        text = contents.get(path) if isinstance(path, str) else None
        if text is None:
            errors.append(f"source:{path}:missing")
            continue
        code = _without_comments(text)
        for marker in source.get("required_markers", []) or []:
            if not isinstance(marker, str) or marker not in code:
                errors.append(f"source:{path}:missing marker {marker!r}")

    ui_path = "extensions/source/update/ui/updatecheckui.cxx"
    ui_code = _without_comments(contents.get(ui_path, ""))
    severity = _function_body(ui_code, "sfx2::NotificationSeverity GetLifecycleSeverity(")
    if not _ordered(
        severity,
        [
            "LIFECYCLE_ERROR_CHECKING",
            "LIFECYCLE_ERROR_DOWNLOADING",
            "NotificationSeverity::Error",
            "LIFECYCLE_DOWNLOAD_PAUSED",
            "NotificationSeverity::Warning",
            "LIFECYCLE_DOWNLOAD_AVAILABLE",
            "NotificationSeverity::Success",
            "NotificationSeverity::Information",
        ],
    ):
        errors.append("ui:severity:state-to-severity policy drift")
    queue = _function_body(ui_code, "void UpdateCheckUI::QueueLifecycleNotification()")
    if not _ordered(queue, ["GetBubbleTitle()", "PostUserEvent", "NotifyLifecycleHdl", "release()"]):
        errors.append("ui:queue:worker-to-main lifecycle handoff drift")
    handler = _function_body(ui_code, "IMPL_STATIC_LINK(UpdateCheckUI, NotifyLifecycleHdl")
    if not _ordered(handler, ["unique_ptr", "NotificationRouter::NotifyInfo", '"libreoffice.update"_ostr']):
        errors.append("ui:handler:approved non-blocking notification route drift")
    setter = _function_body(ui_code, "void UpdateCheckUI::setPropertyValue(")
    if not _ordered(
        setter,
        [
            "PROPERTY_SHOW_BUBBLE",
            "mbBubbleVisible = bShowBubble",
            "SetShowBubble(false)",
            "if (bShowBubble)",
            "QueueLifecycleNotification()",
            "PROPERTY_LIFECYCLE_STATE",
        ],
    ):
        errors.append("ui:setter:shared notification / state property ordering drift")
    if setter is not None and "SetShowBubble(bShowBubble)" in setter:
        errors.append("ui:setter:legacy bubble must not duplicate the shared notification")
    click = _function_body(ui_code, "IMPL_LINK_NOARG(UpdateCheckUI, ClickHdl")
    if click is None or "NotificationRouter::NotifyInfo" not in click or "CreateMessageDialog" in click:
        errors.append("ui:click-error:no-browser error must remain non-blocking")

    controller_path = "extensions/source/update/check/updatecheck.cxx"
    controller_code = _without_comments(contents.get(controller_path, ""))
    state_body = _function_body(controller_code, "OUString GetUpdateLifecycleState(UpdateState eState)")
    found_states = dict(
        re.findall(r'case\s+(UPDATESTATE_[A-Z_]+):\s*return u"([^"]+)"_ustr;', state_body or "")
    )
    if found_states != EXPECTED_ENUM_STATES:
        errors.append("controller:states:enum-to-stable-name map drift")
    menu = _function_body(controller_code, "void UpdateCheck::handleMenuBarUI(")
    if not _ordered(
        menu,
        [
            "PROPERTY_LIFECYCLE_STATE",
            "GetUpdateLifecycleState(eState)",
            "PROPERTY_TITLE",
            "getBubbleTitle(eState)",
            "PROPERTY_TEXT",
            "getBubbleText(eState)",
            "PROPERTY_SHOW_BUBBLE",
        ],
    ):
        errors.append("controller:menu:state/title/body/visibility ordering drift")
    if menu is not None:
        if "if( UPDATESTATE_NO_UPDATE_AVAIL == eState )" not in menu:
            errors.append("controller:menu:no-update must remain silent")
        if "PROPERTY_SHOW_MENUICON, uno::Any(false)" not in menu:
            errors.append("controller:menu:no-update must hide the update icon")
        if "! rUpdateHandler->isVisible() || rUpdateHandler->isMinimized()" not in menu:
            errors.append("controller:menu:dialog visibility suppression drift")
    state = _function_body(controller_code, "void UpdateCheck::setUIState(")
    if not _ordered(
        state,
        [
            "if ( eState == m_eUpdateState )",
            "suppressBubble = true",
            "setDescription(aUpdateInfo.Description)",
            "setNextVersion(aUpdateInfo.Version)",
            "handleMenuBarUI",
            "setState(eState)",
        ],
    ):
        errors.append("controller:set-state:dedupe/version/UI ordering drift")
    if state is not None and "UPDATESTATE_ERROR_CHECKING != eState" in state:
        errors.append("controller:set-state:automatic checking errors must be notification-capable")
    install = _function_body(controller_code, "void UpdateCheck::install()")
    if not _ordered(
        install,
        [
            "verifyUpdateFile(aInstallerURL, aSource)",
            "stageVerifiedWindowsInstaller(aInstallerURL, aSource",
            "buildWindowsInstallerCommand",
            "osl_executeProcess",
            "m_pInstallerLock = pInstallerLock",
        ],
    ):
        errors.append("controller:install:verify/stage/launch/lock ordering drift")
    command = _function_body(controller_code, "WindowsInstallerCommand buildWindowsInstallerCommand(")
    if command is None:
        errors.append("controller:command:missing")
    else:
        for marker in (
            'u"/i"_ustr',
            "REBOOT=ReallySuppress",
            "MSIRESTARTMANAGERCONTROL=DisableShutdown",
        ):
            if marker not in command:
                errors.append(f"controller:command:missing {marker}")
        if any(forbidden in command.lower() for forbidden in ("reinstall", 'u"/q', "passive")):
            errors.append("controller:command:interactive major-update vector drift")
    if controller_code.count("nRetryInterval[]") != 2:
        errors.append("controller:retry:checking and download backoff schedules required")

    handler_path = "extensions/source/update/check/updatehdl.cxx"
    handler_code = _without_comments(contents.get(handler_path, ""))
    bubble_text = _function_body(handler_code, "OUString UpdateHandler::getBubbleText(")
    bubble_title = _function_body(handler_code, "OUString UpdateHandler::getBubbleTitle(")
    if not _ordered(bubble_text, ["UPDATESTATE_ERROR_CHECKING", "msCheckingRetry"]):
        errors.append("handler:bubble-text:checking retry path drift")
    if not _ordered(bubble_title, ["UPDATESTATE_ERROR_CHECKING", "msCheckingError"]):
        errors.append("handler:bubble-title:checking error path drift")
    update_state = _function_body(handler_code, "void UpdateHandler::updateState(")
    for marker in (
        "case UPDATESTATE_DOWNLOADING:",
        "case UPDATESTATE_DOWNLOAD_PAUSED:",
        "case UPDATESTATE_ERROR_DOWNLOADING:",
        "PROGRESS_CTRL",
        "m_pProgressBar->SetValue(mnPercent)",
    ):
        if update_state is None or marker not in update_state:
            errors.append(f"handler:progress:missing {marker}")
    action = _function_body(handler_code, "void SAL_CALL UpdateHandler::actionPerformed(")
    if not _ordered(
        action,
        ["UPDATESTATE_DOWNLOAD_AVAIL", "showWarning(substVariables(msInstallConfirm))", "install()"],
    ):
        errors.append("handler:install-consent:modal gate ordering drift")
    warning = _function_body(handler_code, "bool UpdateHandler::showWarning( const OUString &rWarningText ) const")
    if not _ordered(
        warning,
        ["VclWindowPeerAttribute::YES_NO", "VclWindowPeerAttribute::DEF_NO", "WindowClass_MODALTOP", "execute()", "RET_YES"],
    ):
        errors.append("handler:install-consent:default-No modal decision drift")

    strings = contents.get("extensions/inc/strings.hrc", "")
    if strings.count("%NEXTVERSION") < 7:
        errors.append("strings:version:all app-update lifecycle cards must name the exact version")
    if strings.count("%PERCENT%") < 2:
        errors.append("strings:progress:paused and error cards must carry current percent")
    if strings.count("retry automatically") < 2:
        errors.append("strings:retry:checking and download errors must state automatic retry")
    if "Windows Installer reports completion or rollback status" not in strings:
        errors.append("strings:rollback:installer ownership must be stated")

    makefile = contents.get("extensions/Library_updatecheckui.mk", "")
    if not re.search(r"gb_Library_use_libraries,updatecheckui,\\\s*\n\s*sfx\s+\\", makefile):
        errors.append("makefile:updatecheckui:missing sfx notification-router link")

    try:
        producer_policy = json.loads(
            contents.get("qa/windows-ui-contract/notification-producer-policy.json", "")
        )
    except json.JSONDecodeError:
        producer_policy = {}
        errors.append("producer-policy:invalid JSON")
    producers = {
        item.get("id"): item
        for item in producer_policy.get("producers", [])
        if isinstance(item, Mapping)
    }
    producer = producers.get("updater-lifecycle-status")
    if not isinstance(producer, Mapping):
        errors.append("producer-policy:updater lifecycle producer missing")
    else:
        if producer.get("source") != "libreoffice.update" or producer.get("informational_only") is not True:
            errors.append("producer-policy:updater source/modality drift")
        if set(producer.get("severity", [])) != {"Information", "Success", "Warning", "Error"}:
            errors.append("producer-policy:updater severity set drift")

    preserved = contract.get("preserved_paths")
    if not isinstance(preserved, list) or set(preserved) != EXPECTED_PRESERVED:
        errors.append("contract:preserved_paths:complete safety boundary required")
    return errors


def validate_repository(repo: Path = REPOSITORY) -> None:
    contract, contents = load_repository(repo)
    errors = violations(contract, contents)
    if errors:
        raise ValidationError("\n".join(errors))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        validate_repository(args.repo_root.resolve())
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Updater lifecycle composition failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Updater lifecycle composition passed: eleven stable states are mapped and eligible "
        "action/error transitions route versioned progress/retry status through the shared "
        "notification stack while routine checking/no-update paths stay quiet and default-No verified MSI consent, "
        "protected staging, interactive launch, and restart suppression remain intact; runtime unverified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
