#!/usr/bin/env python3
"""Fail-closed source contract for the runtime-composed Material wizard shell."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping


REPOSITORY = Path(__file__).resolve().parents[1]
CONTRACT_PATH = Path("qa/windows-ui-contract/runtime-wizard-composition.json")


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
                return source[opening : index + 1]
    return None


def _ordered_markers(context: str, body: str | None, markers: list[Any], errors: list[str]) -> None:
    if body is None:
        errors.append(f"{context}: function body missing")
        return
    cursor = -1
    for marker in markers:
        if not isinstance(marker, str) or not marker:
            errors.append(f"{context}: marker must be non-empty text")
            continue
        found = body.find(marker, cursor + 1)
        if found < 0:
            errors.append(f"{context}: missing or out-of-order marker {marker!r}")
            return
        cursor = found


def violations(
    contract: Mapping[str, Any], contents: Mapping[str, str]
) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if contract.get("contract") != "material-runtime-wizard-composition":
        errors.append("contract marker drift")
    if contract.get("platform") != "windows":
        errors.append("platform must be windows")
    if contract.get("status") != "source-implemented":
        errors.append("status must be source-implemented")
    if contract.get("runtime_verified") is not False:
        errors.append("runtime_verified must remain false until an installed build is exercised")
    if contract.get("surface") != "vcl/uiconfig/ui/wizard.ui":
        errors.append("surface path drift")

    activation = contract.get("theme_activation")
    if not isinstance(activation, Mapping):
        errors.append("theme_activation must be an object")
    else:
        if activation.get("environment_variable") != "VCL_FILE_WIDGET_THEME":
            errors.append("theme activation variable drift")
        if activation.get("value") != "material":
            errors.append("theme activation value drift")
        if activation.get("high_contrast_precedence") is not True:
            errors.append("forced-colors precedence must stay enabled")

    shell = contract.get("shell")
    ui_text = contents.get(str(contract.get("surface")), "")
    try:
        root = ET.fromstring(ui_text)
    except ET.ParseError as error:
        errors.append(f"wizard XML parse failed: {error}")
        root = None
    if not isinstance(shell, Mapping):
        errors.append("shell must be an object")
    elif root is not None:
        assistant = next(
            (
                item
                for item in root.iter("object")
                if item.get("id") == shell.get("root_id")
            ),
            None,
        )
        if assistant is None or assistant.get("class") != shell.get("root_class"):
            errors.append("wizard root class/id drift")
        else:
            properties = {
                prop.get("name"): (prop.text or "").strip()
                for prop in assistant.findall("property")
            }
            if properties.get("modal", "false").lower() != "true":
                errors.append("wizard must remain modal")
            for forbidden in shell.get("forbidden_properties", []):
                if forbidden in properties:
                    errors.append(f"wizard retains forbidden legacy property {forbidden}")
            if "title" in properties:
                errors.append("wizard title is runtime-owned and must not be invented statically")

    page = contract.get("runtime_page_host")
    if not isinstance(page, Mapping):
        errors.append("runtime_page_host must be an object")
    else:
        metric_text = contents.get(str(page.get("metric_source")), "")
        try:
            definition = ET.fromstring(metric_text)
        except ET.ParseError as error:
            errors.append(f"Material definition XML parse failed: {error}")
            definition = None
        if definition is not None:
            metric = next(
                (
                    node
                    for node in definition.findall("./metrics/metric")
                    if node.get("name") == page.get("metric")
                ),
                None,
            )
            expected = str(page.get("metric_value"))
            if metric is None or metric.get("value") != expected:
                errors.append(
                    f"wizard spacing metric must resolve to {page.get('metric')}={expected}"
                )
        page_source = _without_cpp_comments(contents.get(str(page.get("source")), ""))
        helper = _function_body(page_source, "lcl_materialWizardPageSpacing()")
        _ordered_markers(
            "page-spacing-helper",
            helper,
            [
                "GetHighContrastMode()",
                "std::getenv(\"VCL_FILE_WIDGET_THEME\")",
                "std::string_view(pThemeName) != \"material\"",
                "vcl::MaterialTokens::fromCurrentTheme(false)",
                "findMetric(\"space-list-entry\")",
            ],
            errors,
        )
        body = _function_body(page_source, str(page.get("function")))
        _ordered_markers(
            "runtime-page-host", body, list(page.get("required_markers", [])), errors
        )

    actions = contract.get("forward_actions")
    if not isinstance(actions, Mapping):
        errors.append("forward_actions must be an object")
    else:
        action_source = _without_cpp_comments(
            contents.get(str(actions.get("source")), "")
        )
        helper = _function_body(action_source, "lcl_isMaterialWizardTheme()")
        _ordered_markers(
            "forward-action-helper",
            helper,
            [
                "GetHighContrastMode()",
                "std::getenv(\"VCL_FILE_WIDGET_THEME\")",
                "std::string_view(pThemeName) == \"material\"",
            ],
            errors,
        )
        body = _function_body(action_source, str(actions.get("function")))
        _ordered_markers(
            "forward-actions", body, list(actions.get("required_markers", [])), errors
        )
        if body is not None and body.count("setAction(true);") != 2:
            errors.append("exactly Next and Finish must be Material primary actions")

    semantics = contract.get("preserved_semantics")
    if not isinstance(semantics, list) or len(set(semantics)) != 6:
        errors.append("preserved_semantics must pin the six runtime behavior guarantees")
    return errors


def load_repository(repo: Path = REPOSITORY) -> tuple[dict[str, Any], dict[str, str]]:
    contract = _read_json(repo / CONTRACT_PATH)
    paths = {str(contract.get("surface", ""))}
    for key in ("runtime_page_host", "forward_actions"):
        section = contract.get(key)
        if isinstance(section, Mapping):
            for field in ("source", "metric_source"):
                value = section.get(field)
                if isinstance(value, str):
                    paths.add(value)
    contents = {
        relative: (repo / relative).read_text(encoding="utf-8")
        for relative in paths
        if relative and (repo / relative).is_file()
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
        print(f"Runtime wizard composition contract failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Runtime wizard composition passed: modal runtime shell, token-derived 12px page grid, "
        "Next/Finish primary actions, and forced-colors precedence are source-pinned; runtime UI unverified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
