#!/usr/bin/env python3
"""Fail-closed source contract for the Material Writer canvas (WIN-WR-002)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "qa/windows-ui-contract/writer-canvas-composition.json"


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
    paths = {contract.get("definition_file")}
    for source in contract.get("sources", []) or []:
        if isinstance(source, dict):
            paths.add(source.get("path"))
    contents: dict[str, str] = {}
    for relative in paths:
        if isinstance(relative, str) and (repo / relative).is_file():
            contents[relative] = (repo / relative).read_text(encoding="utf-8")
    return contract, contents


def violations(contract: Mapping[str, Any], contents: Mapping[str, str]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != 1:
        errors.append("contract:schema_version:must be 1")
    if contract.get("contract") != "material-writer-canvas-composition":
        errors.append("contract:marker:unexpected value")
    if contract.get("platform") != "windows":
        errors.append("contract:platform:must be windows")
    if contract.get("status") != "source-implemented":
        errors.append("contract:status:must be source-implemented")
    if contract.get("runtime_verified") is not False:
        errors.append("contract:runtime_verified:must remain false")
    if contract.get("surface") != "native:writer-document-canvas":
        errors.append("contract:surface:unexpected value")
    if contract.get("owner") != "sw" or contract.get("inventory_id") != "WIN-WR-002":
        errors.append("contract:owner-or-inventory:drift")
    if contract.get("canvas_token") != "surface-container-low":
        errors.append("contract:canvas_token:must be surface-container-low")
    if contract.get("workspace_slot") != "@surface-container-low":
        errors.append("contract:workspace_slot:must resolve to @surface-container-low")

    definition_path = contract.get("definition_file")
    definition = contents.get(definition_path, "") if isinstance(definition_path, str) else ""
    try:
        root = ET.fromstring(definition)
    except ET.ParseError as error:
        errors.append(f"definition:xml:{error}")
        root = None
    if root is not None:
        palettes = root.findall("palette")
        if not palettes:
            errors.append("definition:palette:none found")
        for palette in palettes:
            scheme = palette.get("scheme") or "light"
            roles = {entry.get("name") for entry in palette.findall("color")}
            if contract.get("canvas_token") not in roles:
                errors.append(f"definition:palette:{scheme}:canvas token missing")
        style = root.find("style")
        workspace = style.find("workspaceColor") if style is not None else None
        if workspace is None or workspace.get("value") != contract.get("workspace_slot"):
            errors.append("definition:style:workspaceColor mapping drift")

    sources = contract.get("sources")
    if not isinstance(sources, list) or len(sources) != 3:
        errors.append("contract:sources:exactly three source entries required")
        sources = []
    for source in sources:
        if not isinstance(source, dict):
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

    view_path = "sw/source/core/view/viewsh.cxx"
    view_code = _without_comments(contents.get(view_path, ""))
    guard = _function_body(view_code, "bool IsMaterialWriterCanvasEnabled()")
    if not _ordered(
        guard,
        ["GetHighContrastMode()", "return false", "VCL_FILE_WIDGET_THEME", "material"],
    ):
        errors.append("viewsh:guard:high contrast must precede the exact Material gate")
    resolver = _function_body(view_code, "Color SwViewShell::GetCanvasBackgroundColor() const")
    if not _ordered(
        resolver,
        [
            "GetAppBackgroundColor()",
            "IsMaterialWriterCanvasEnabled()",
            "GetWindowColor().IsDark()",
            "MaterialTokens::fromCurrentTheme(bDark)",
            "isValid()",
            "findColor(\"surface-container-low\")",
        ],
    ):
        errors.append("viewsh:resolver:fallback/guard/scheme/token ordering drift")
    desktop = _function_body(view_code, "void SwViewShell::PaintDesktop(")
    if not _ordered(desktop, ["LibreOfficeKit::isActive()", "aRegion -= aPageRect", "PaintDesktop_(aRegion)"]):
        errors.append("viewsh:desktop:LOK exclusion/page subtraction/fill ordering drift")
    desktop_fill = _function_body(view_code, "void SwViewShell::PaintDesktop_(")
    if not _ordered(
        desktop_fill,
        ["!IsMaterialWriterCanvasEnabled()", "DrawAppBackgroundBitmap", "GetCanvasBackgroundColor()", "DrawRect"],
    ):
        errors.append("viewsh:desktop-fill:bitmap guard/token fill ordering drift")
    paint = _function_body(view_code, "void SwViewShell::Paint(vcl::RenderContext&")
    if not _ordered(paint, ["PaintDesktop(rRenderContext, aRect)", "GetLayout()->PaintSwFrame"]):
        errors.append("viewsh:paint:canvas must paint before document layout")

    paint_path = "sw/source/core/layout/paintfrm.cxx"
    paint_code = _without_comments(contents.get(paint_path, ""))
    if paint_code.count("pViewShell->GetCanvasBackgroundColor()") != 1:
        errors.append("paintfrm:shadow seam must consume the canvas color exactly once")
    if paint_code.count("lcl_paintBitmapExToRect(pOut, _pViewShell,") != 4:
        errors.append("paintfrm:all four page-shadow edges must receive the view shell")

    expected_preserved = {
        "page rectangles are subtracted before desktop fill",
        "document layout paints after desktop fill",
        "LibreOfficeKit tiled rendering skips desktop fill",
        "print and metafile output retain their existing exclusions",
        "high contrast and non-Material themes retain configured colors",
        "zoom, selection, caret, input coordinates, and document pixels are unchanged",
    }
    preserved = contract.get("preserved_paths")
    if not isinstance(preserved, list) or set(preserved) != expected_preserved:
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
        print(f"Writer canvas composition failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Writer canvas composition passed: the high-contrast-first Material helper resolves "
        "surface-container-low, fills only page-subtracted desktop regions, shares that color "
        "with page-shadow seams, and preserves document/tile/print/input paths; runtime unverified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
