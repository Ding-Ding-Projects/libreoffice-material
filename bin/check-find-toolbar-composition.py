#!/usr/bin/env python3
"""Fail-closed Material composition contract for the native Find toolbar."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping


REPOSITORY = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("qa/windows-ui-contract/find-toolbar-composition.json")
LEDGER_PATH = "qa/windows-ui-contract/material-rewrite-ledger.json"


class ValidationError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError(f"{path}: root must be an object")
    return value


def _without_cpp_comments(source: str) -> str:
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
                return source[start : index + 1]
    return None


def _ordered(context: str, body: str | None, markers: tuple[str, ...], errors: list[str]) -> None:
    if body is None:
        errors.append(f"{context}: function body missing")
        return
    cursor = -1
    for marker in markers:
        found = body.find(marker, cursor + 1)
        if found < 0:
            errors.append(f"{context}: missing or out-of-order {marker}")
            return
        cursor = found


def _properties(element: ET.Element) -> dict[str, str]:
    return {
        node.get("name", ""): (node.text or "").strip()
        for node in element.findall("property")
    }


def _direct_objects(element: ET.Element) -> list[ET.Element]:
    result: list[ET.Element] = []
    for child in element.findall("child"):
        obj = child.find("object")
        if obj is not None:
            result.append(obj)
    return result


def violations(
    contract: Mapping[str, Any], contents: Mapping[str, str]
) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if contract.get("contract") != "material-find-toolbar-composition":
        errors.append("contract marker drift")
    if contract.get("platform") != "windows":
        errors.append("platform must be windows")
    if contract.get("status") != "source-implemented":
        errors.append("status must be source-implemented")
    if contract.get("runtime_verified") is not False:
        errors.append("runtime_verified must remain false until an installed build is exercised")
    if (
        contract.get("surface") != "native:find-toolbar"
        or contract.get("owner") != "svx"
        or contract.get("inventory_id") != "WIN-INP-005"
    ):
        errors.append("native surface ownership drift")

    for entry in contract.get("source_files", []):
        if not isinstance(entry, Mapping):
            errors.append("source_files entries must be objects")
            continue
        path = entry.get("path")
        text = contents.get(path) if isinstance(path, str) else None
        if text is None:
            errors.append(f"source file missing: {path}")
            continue
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual != entry.get("sha256"):
            errors.append(f"{path}: sha256 drift")

    ui_path = str(contract.get("ui_file"))
    try:
        root = ET.fromstring(contents.get(ui_path, ""))
    except ET.ParseError as error:
        errors.append(f"find toolbar XML parse failed: {error}")
        root = None
    if root is not None:
        objects = {
            node.get("id"): node
            for node in root.iter("object")
            if node.get("id")
        }
        layout = contract.get("layout")
        if not isinstance(layout, Mapping):
            errors.append("layout must be an object")
        else:
            host = objects.get(layout.get("root_id"))
            if host is None or host.get("class") != layout.get("root_class"):
                errors.append("FindBox root class/id drift")
            else:
                props = _properties(host)
                if props.get("orientation") != layout.get("orientation"):
                    errors.append("FindBox must remain horizontal")
                if props.get("spacing") != str(layout.get("spacing")):
                    errors.append("FindBox spacing drift")
                children = [node.get("id") for node in _direct_objects(host)]
                if children != layout.get("direct_children"):
                    errors.append("find entry and builder must remain adjacent direct siblings")
        combo = objects.get(str(contract.get("entry_id")))
        if combo is None or combo.get("class") != "GtkComboBoxText":
            errors.append("editable Find combo missing")
        elif _properties(combo).get("has-entry") != "True":
            errors.append("Find combo must remain editable")
        button = objects.get(str(contract.get("builder_button_id")))
        if button is None or button.get("class") != "GtkButton":
            errors.append("adjacent regex builder button missing")
        else:
            props = _properties(button)
            for name, expected in (
                ("label", ".*"),
                ("visible", "True"),
                ("can-focus", "True"),
                ("receives-default", "False"),
            ):
                if props.get(name) != expected:
                    errors.append(f"builder {name} must be {expected}")
            accessible = next(
                (node for node in button.iter("object") if node.get("class") == "AtkObject"),
                None,
            )
            accessible_props = _properties(accessible) if accessible is not None else {}
            if not accessible_props.get("AtkObject::accessible-name"):
                errors.append("builder accessible name missing")
            if not accessible_props.get("AtkObject::accessible-description"):
                errors.append("builder accessible description missing")
        for label in root.iter("object"):
            if label.get("class") != "GtkLabel":
                continue
            props = _properties(label)
            if not props.get("label") and props.get("no-show-all") == "True":
                errors.append("empty hidden label workaround is forbidden")

    header_path = "svx/source/inc/findtextfield.hxx"
    source_path = "svx/source/tbxctrls/tbunosearchcontrollers.cxx"
    header = _without_cpp_comments(contents.get(header_path, ""))
    source = _without_cpp_comments(contents.get(source_path, ""))
    member_markers = (
        "std::unique_ptr<weld::ComboBox> m_xWidget;",
        "std::unique_ptr<weld::Button> m_xRegexBuilderButton;",
        "std::unique_ptr<sfx2::RegexSearchController> m_xRegexSearchController;",
    )
    member_positions = [header.find(marker) for marker in member_markers]
    if any(position < 0 for position in member_positions) or member_positions != sorted(member_positions):
        errors.append("controller lifetime members are missing or out of order")
    for marker in (
        "DECL_LINK(RegexSearchChangedHdl, weld::ComboBox&, void);",
        "void set_match_case(bool bMatchCase);",
        "bool get_search_options(i18nutil::SearchOptions2& rOptions) const;",
    ):
        if marker not in header:
            errors.append(f"header marker missing: {marker}")

    constructor = _function_body(source, "FindTextFieldControl::FindTextFieldControl(")
    _ordered(
        "controller-construction",
        constructor,
        (
            'weld_combo_box(u"find"_ustr)',
            'weld_button(u"find_regex_builder"_ustr)',
            "std::make_unique<sfx2::RegexSearchController>",
            "LINK(this, FindTextFieldControl, RegexSearchChangedHdl)",
            "SetGlobalFlagEnabled(false);",
            "SetCaseInsensitiveFlagEnabled(false);",
            "aState.Mode = sfx2::RegexSearchMode::Literal;",
            "aState.Flags.CaseInsensitive = true;",
            "m_xRegexSearchController->SetState(aState);",
        ),
        errors,
    )
    changed = _function_body(
        source,
        "IMPL_LINK_NOARG(FindTextFieldControl, RegexSearchChangedHdl",
    )
    _ordered(
        "owner-callback",
        changed,
        ("m_aChangeHdl.Call(*m_xWidget);",),
        errors,
    )
    connect = _function_body(source, "void FindTextFieldControl::connect_changed(")
    if connect is None or "m_aChangeHdl = rLink;" not in connect:
        errors.append("external toolbar callback storage missing")
    if connect is not None and "m_xWidget->connect_changed" in connect:
        errors.append("direct combo callback bypasses shared controller")
    dispose = _function_body(source, "void FindTextFieldControl::dispose()")
    _ordered(
        "controller-disposal",
        dispose,
        (
            "m_xRegexSearchController.reset();",
            "m_xRegexBuilderButton.reset();",
            "m_xWidget.reset();",
        ),
        errors,
    )
    options = _function_body(
        source, "bool FindTextFieldControl::get_search_options("
    )
    _ordered(
        "validated-options-handoff",
        options,
        (
            "m_xRegexSearchController->GetState()",
            "sfx2::RegexSearchService::Validate(rState).IsValid",
            "return false;",
            "rOptions = m_xRegexSearchController->GetSearchOptions();",
        ),
        errors,
    )
    case_sync = _function_body(source, "void FindTextFieldControl::set_match_case(")
    _ordered(
        "case-state-sync",
        case_sync,
        (
            "m_xRegexSearchController->GetState()",
            "aState.Flags.CaseInsensitive = !bMatchCase;",
            "m_xRegexSearchController->SetStateWithoutNotify(aState, false);",
        ),
        errors,
    )
    case_click = _function_body(
        source, "void SAL_CALL MatchCaseToolboxController::click()"
    )
    _ordered(
        "case-toolbar-authority",
        case_click,
        (
            "const bool bMatchCase = !bCurrent;",
            "m_xMatchCaseControl->set_active(bMatchCase);",
            "pFindControl->set_match_case(bMatchCase);",
        ),
        errors,
    )
    dispatch = _function_body(source, "void impl_executeSearch(")
    _ordered(
        "uno-dispatch",
        dispatch,
        (
            "pFindTextFieldControl->set_match_case(aMatchCase)",
            "pFindTextFieldControl->get_search_options(aSearchOptions)",
            "sFindText = aSearchOptions.searchString;",
            "TransliterationFlags nFlags = aSearchOptions.transliterateFlags;",
            "nFlags &= ~TransliterationFlags::IGNORE_CASE;",
            "if (!aMatchCase)",
            '"SearchItem.SearchString", css::uno::Any( sFindText )',
            '"SearchItem.SearchFlags", css::uno::Any( aSearchOptions.searchFlag )',
            "aFindAll ?SvxSearchCmd::FIND_ALL : SvxSearchCmd::FIND",
            "i18nutil::downgradeSearchAlgorithms2(aSearchOptions.AlgorithmType2)",
            '"SearchItem.AlgorithmType2", css::uno::Any( aSearchOptions.AlgorithmType2 )',
            "xDispatch->dispatch( aURL, aArgs );",
        ),
        errors,
    )
    if dispatch and (
        '"SearchItem.AlgorithmType2", css::uno::Any( sal_Int16(css::util::SearchAlgorithms2::ABSOLUTE)' in dispatch
    ):
        errors.append("UNO dispatch hard-codes literal search")

    dependency_by_path = {
        item.get("path"): item
        for item in contract.get("dependencies", [])
        if isinstance(item, Mapping)
    }
    for path, declaration in dependency_by_path.items():
        try:
            dependency = json.loads(contents.get(str(path), ""))
        except json.JSONDecodeError:
            errors.append(f"dependency is not valid JSON: {path}")
            continue
        if dependency.get("contract") != declaration.get("contract_marker"):
            errors.append(f"dependency contract marker drift: {path}")
        coverage_id = declaration.get("coverage_id")
        if coverage_id:
            candidates = dependency.get("shipping_fields", dependency.get("integrations", []))
            entry = next(
                (
                    item
                    for item in candidates
                    if isinstance(item, Mapping) and item.get("coverage_id") == coverage_id
                ),
                None,
            )
            if entry is None or entry.get("integration_status", entry.get("status")) != "source-integrated":
                errors.append(f"dependency lost source-integrated {coverage_id}: {path}")
        governed = declaration.get("governed_surface")
        if governed and not any(
            isinstance(item, Mapping) and item.get("surface") == governed
            for item in dependency.get("surfaces", [])
        ):
            errors.append(f"dependency lost governed surface {governed}: {path}")

    try:
        ledger = json.loads(contents.get(LEDGER_PATH, ""))
    except json.JSONDecodeError:
        errors.append("rewrite ledger is not valid JSON")
        ledger = {}
    rows = {
        row.get("surface"): row
        for row in ledger.get("surfaces", [])
        if isinstance(row, Mapping)
    }
    native = rows.get("native:find-toolbar")
    if not isinstance(native, Mapping):
        errors.append("native Find toolbar ledger row missing")
    else:
        if native.get("family") != "native-shell" or native.get("owner") != "svx":
            errors.append("native Find toolbar ledger ownership drift")
        status = native.get("rewrite_status")
        if status not in {"pending", "rewritten-material"}:
            errors.append("native Find toolbar ledger status invalid")
        if status == "rewritten-material":
            evidence = native.get("rewrite_evidence")
            markers = evidence.get("anatomy_markers") if isinstance(evidence, Mapping) else None
            if not isinstance(evidence, Mapping) or evidence.get("contract") != CONTRACT_PATH.as_posix():
                errors.append("rewritten native Find toolbar must cite its composition contract")
            if not isinstance(markers, Mapping) or markers.get("contract_marker") != contract.get("contract"):
                errors.append("rewritten native Find toolbar lost its contract marker")
    host = rows.get(ui_path)
    if not isinstance(host, Mapping) or host.get("family") != "host-composed-surface":
        errors.append("FindBox UI must be host-composed after removing the fake label")

    if set(contract.get("preserved_semantics", [])) != {
        "find-next",
        "find-previous",
        "find-all",
        "match-case-toolbar-authority",
        "match-diacritics-toolbar-authority",
        "formatted-search-toolbar-authority",
        "search-history",
        "escape-returns-focus-to-document",
    }:
        errors.append("preserved Find toolbar semantics drift")
    return errors


def load_repository(repo: Path = REPOSITORY) -> tuple[dict[str, Any], dict[str, str]]:
    contract = _read_json(repo / CONTRACT_PATH)
    paths = {LEDGER_PATH}
    for entry in contract.get("source_files", []):
        if isinstance(entry, Mapping) and isinstance(entry.get("path"), str):
            paths.add(entry["path"])
    for entry in contract.get("dependencies", []):
        if isinstance(entry, Mapping) and isinstance(entry.get("path"), str):
            paths.add(entry["path"])
    contents = {
        relative: (repo / relative).read_text(encoding="utf-8")
        for relative in paths
        if (repo / relative).is_file()
    }
    return contract, contents


def validate(repo: Path = REPOSITORY) -> None:
    contract, contents = load_repository(repo)
    errors = violations(contract, contents)
    if errors:
        raise ValidationError("\n".join(errors))


def main() -> int:
    try:
        validate()
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Find toolbar composition contract failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Find toolbar composition passed: adjacent accessible builder, validated ICU options, "
        "UNO algorithm handoff, native Match Case/Find All authority, and host composition are source-pinned; runtime UI unverified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
