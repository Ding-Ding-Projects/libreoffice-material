#!/usr/bin/env python3
"""Validate the Windows native text-query coverage registry.

The registry is both an implementation inventory and a tripwire.  Existing
shipping controls must resolve to exactly one text-capable widget, planned
controls must remain explicitly absent until implemented, and every UI control
that looks like a search/filter/query candidate must be classified.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


TEXT_WIDGET_CLASSES = frozenset(
    {"GtkComboBox", "GtkComboBoxText", "GtkEntry", "GtkSearchEntry"}
)
IDENTIFIER_TERMS = ("filter", "find", "lookup", "query", "search")
SEMANTIC_PROPERTIES = frozenset(
    {"AtkObject::accessible-name", "placeholder-text", "tooltip-text"}
)
FIND_ICON = "gtk-find"
IGNORED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".worktrees",
        "autom4te.cache",
        "build",
        "external",
        "extras",
        "helpcontent2",
        "icon-themes",
        "instdir",
        "solver",
        "translations",
        "workdir",
    }
)
ENTRY_GROUPS = ("shipping_fields", "planned_fields", "excluded_candidates")
SEARCH_TERM_RE = re.compile("|".join(re.escape(term) for term in IDENTIFIER_TERMS), re.I)


@dataclass(frozen=True, order=True)
class ControlKey:
    ui_file: str
    widget_id: str

    def display(self) -> str:
        return f"{self.ui_file}#{self.widget_id}"


@dataclass(frozen=True)
class CoverageStats:
    shipping_fields: int = 0
    planned_fields: int = 0
    excluded_candidates: int = 0
    discovered_candidates: int = 0
    scanner_discovered_shipping: int = 0


def _entry_key(entry: dict[str, Any]) -> ControlKey:
    return ControlKey(str(entry.get("ui_file", "")), str(entry.get("widget_id", "")))


def _property_map(obj: ET.Element) -> dict[str, str]:
    return {
        str(prop.get("name", "")): (prop.text or "").strip()
        for prop in obj.findall("./property")
    }


def _validate_relative_ui_path(raw_path: Any, context: str, errors: list[str]) -> str | None:
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"{context}: ui_file must be a non-empty string")
        return None
    if "\\" in raw_path:
        errors.append(f"{context}: ui_file must use forward slashes: {raw_path!r}")
        return None

    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts or path.suffix != ".ui":
        errors.append(f"{context}: ui_file is not a safe relative .ui path: {raw_path!r}")
        return None
    return raw_path


def _required_text(entry: dict[str, Any], key: str, context: str, errors: list[str]) -> None:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{context}: {key} must be a non-empty string")


def _validate_scanner_contract(registry: dict[str, Any], errors: list[str]) -> None:
    contract = registry.get("scanner_contract")
    if not isinstance(contract, dict):
        errors.append("scanner_contract must be an object")
        return

    expected = {
        "widget_classes": sorted(TEXT_WIDGET_CLASSES),
        "identifier_terms": sorted(IDENTIFIER_TERMS),
        "semantic_properties": sorted(SEMANTIC_PROPERTIES),
        "find_icon": FIND_ICON,
    }
    for key, expected_value in expected.items():
        actual = contract.get(key)
        if isinstance(expected_value, list) and isinstance(actual, list):
            actual = sorted(actual)
        if actual != expected_value:
            errors.append(
                f"scanner_contract.{key} must remain {expected_value!r}; got {actual!r}"
            )


def _load_ui_objects(
    repo_root: Path,
    key: ControlKey,
    cache: dict[str, tuple[ET.Element | None, str | None]],
) -> tuple[list[ET.Element], str | None]:
    if key.ui_file not in cache:
        source = repo_root.joinpath(*PurePosixPath(key.ui_file).parts)
        if not source.is_file():
            cache[key.ui_file] = (None, f"UI file does not exist: {key.ui_file}")
        else:
            try:
                cache[key.ui_file] = (ET.parse(source).getroot(), None)
            except ET.ParseError as exc:
                cache[key.ui_file] = (None, f"cannot parse {key.ui_file}: {exc}")

    root, parse_error = cache[key.ui_file]
    if root is None:
        return [], parse_error
    return [obj for obj in root.iter("object") if obj.get("id") == key.widget_id], None


def _validate_existing_control(
    repo_root: Path,
    key: ControlKey,
    context: str,
    cache: dict[str, tuple[ET.Element | None, str | None]],
    errors: list[str],
) -> None:
    matches, load_error = _load_ui_objects(repo_root, key, cache)
    if load_error:
        errors.append(f"{context}: {load_error}")
        return
    if not matches:
        errors.append(f"{context}: widget id does not exist: {key.display()}")
        return
    if len(matches) != 1:
        errors.append(
            f"{context}: widget id must occur exactly once, found {len(matches)}: {key.display()}"
        )
        return
    widget_class = matches[0].get("class", "")
    if widget_class not in TEXT_WIDGET_CLASSES:
        errors.append(
            f"{context}: {key.display()} has non-text widget class {widget_class!r}"
        )


def _validate_planned_control(
    repo_root: Path,
    entry: dict[str, Any],
    key: ControlKey,
    context: str,
    cache: dict[str, tuple[ET.Element | None, str | None]],
    errors: list[str],
) -> None:
    if entry.get("source_state") != "not-yet-present":
        errors.append(f"{context}: source_state must be 'not-yet-present'")
    matches, load_error = _load_ui_objects(repo_root, key, cache)
    if load_error:
        errors.append(f"{context}: {load_error}")
        return
    if matches:
        errors.append(
            f"{context}: planned widget now exists; move it to shipping_fields: {key.display()}"
        )


def _candidate_reasons(obj: ET.Element, labels: Iterable[str]) -> set[str]:
    reasons: set[str] = set()
    widget_id = obj.get("id", "")
    if SEARCH_TERM_RE.search(widget_id):
        reasons.add("widget-id")

    for label in labels:
        if SEARCH_TERM_RE.search(label):
            reasons.add("mnemonic-label")

    for prop in obj.iter("property"):
        name = prop.get("name", "")
        value = (prop.text or "").strip()
        if name in SEMANTIC_PROPERTIES and SEARCH_TERM_RE.search(value):
            reasons.add(name)
        if name == "primary-icon-stock" and value == FIND_ICON:
            reasons.add("find-icon")
    return reasons


def discover_candidate_controls(repo_root: Path) -> tuple[dict[ControlKey, set[str]], list[str]]:
    candidates: dict[ControlKey, set[str]] = {}
    errors: list[str] = []

    for source in sorted(repo_root.rglob("*.ui")):
        try:
            relative = source.relative_to(repo_root)
        except ValueError:
            continue
        if any(part in IGNORED_DIRECTORY_NAMES for part in relative.parts):
            continue

        ui_file = relative.as_posix()
        try:
            root = ET.parse(source).getroot()
        except ET.ParseError as exc:
            errors.append(f"candidate scan cannot parse {ui_file}: {exc}")
            continue

        labels_by_target: dict[str, list[str]] = {}
        for obj in root.iter("object"):
            properties = _property_map(obj)
            target = properties.get("mnemonic-widget", "")
            if target:
                labels_by_target.setdefault(target, []).append(properties.get("label", ""))

        for obj in root.iter("object"):
            widget_id = obj.get("id", "")
            if not widget_id or obj.get("class") not in TEXT_WIDGET_CLASSES:
                continue
            reasons = _candidate_reasons(obj, labels_by_target.get(widget_id, ()))
            if reasons:
                candidates[ControlKey(ui_file, widget_id)] = reasons

    return candidates, errors


def validate_registry_data(
    repo_root: Path, registry: dict[str, Any]
) -> tuple[list[str], CoverageStats]:
    errors: list[str] = []

    if registry.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if registry.get("contract") != "windows-native-text-query-coverage":
        errors.append("contract must be 'windows-native-text-query-coverage'")
    if registry.get("platform") != "windows":
        errors.append("platform must be 'windows'")
    _validate_scanner_contract(registry, errors)

    groups: dict[str, list[dict[str, Any]]] = {}
    for group_name in ENTRY_GROUPS:
        raw_group = registry.get(group_name)
        if not isinstance(raw_group, list):
            errors.append(f"{group_name} must be an array")
            groups[group_name] = []
            continue
        groups[group_name] = []
        for index, raw_entry in enumerate(raw_group):
            if not isinstance(raw_entry, dict):
                errors.append(f"{group_name}[{index}] must be an object")
                continue
            groups[group_name].append(raw_entry)

    counts = registry.get("expected_counts")
    if not isinstance(counts, dict):
        errors.append("expected_counts must be an object")
        counts = {}
    for group_name in ENTRY_GROUPS:
        expected = counts.get(group_name)
        if not isinstance(expected, int) or expected < 0:
            errors.append(f"expected_counts.{group_name} must be a non-negative integer")
        elif expected != len(groups[group_name]):
            errors.append(
                f"expected_counts.{group_name} is {expected}, but registry contains "
                f"{len(groups[group_name])} entries"
            )

    seen_controls: dict[ControlKey, str] = {}
    seen_coverage_ids: dict[str, str] = {}
    ui_cache: dict[str, tuple[ET.Element | None, str | None]] = {}
    keys_by_group: dict[str, set[ControlKey]] = {name: set() for name in ENTRY_GROUPS}

    for group_name in ENTRY_GROUPS:
        for index, entry in enumerate(groups[group_name]):
            context = f"{group_name}[{index}]"
            required = ["coverage_id", "ui_file", "widget_id"]
            if group_name == "shipping_fields":
                required.extend(["surface", "query_scope", "regex_builder"])
            elif group_name == "planned_fields":
                required.extend(
                    ["surface", "query_scope", "regex_builder", "planned_layout", "source_state"]
                )
            else:
                required.extend(["category", "reason"])
            for key_name in required:
                _required_text(entry, key_name, context, errors)

            ui_file = _validate_relative_ui_path(entry.get("ui_file"), context, errors)
            widget_id = entry.get("widget_id")
            if ui_file is None or not isinstance(widget_id, str) or not widget_id:
                continue

            key = ControlKey(ui_file, widget_id)
            keys_by_group[group_name].add(key)
            if key in seen_controls:
                errors.append(
                    f"{context}: duplicate control coverage for {key.display()}; "
                    f"already classified by {seen_controls[key]}"
                )
            else:
                seen_controls[key] = context

            coverage_id = entry.get("coverage_id")
            if isinstance(coverage_id, str) and coverage_id:
                if coverage_id in seen_coverage_ids:
                    errors.append(
                        f"{context}: duplicate coverage_id {coverage_id!r}; "
                        f"already used by {seen_coverage_ids[coverage_id]}"
                    )
                else:
                    seen_coverage_ids[coverage_id] = context

            if group_name == "planned_fields":
                _validate_planned_control(
                    repo_root, entry, key, context, ui_cache, errors
                )
            else:
                _validate_existing_control(repo_root, key, context, ui_cache, errors)

    candidates, scan_errors = discover_candidate_controls(repo_root)
    errors.extend(scan_errors)
    classified_candidates = (
        keys_by_group["shipping_fields"] | keys_by_group["excluded_candidates"]
    )

    for key in sorted(set(candidates) - classified_candidates):
        reasons = ", ".join(sorted(candidates[key]))
        errors.append(
            f"unclassified search-control candidate: {key.display()} (signals: {reasons})"
        )

    for key in sorted(keys_by_group["excluded_candidates"] - set(candidates)):
        errors.append(
            f"excluded candidate no longer matches the scanner; remove or reclassify it: {key.display()}"
        )

    stats = CoverageStats(
        shipping_fields=len(groups["shipping_fields"]),
        planned_fields=len(groups["planned_fields"]),
        excluded_candidates=len(groups["excluded_candidates"]),
        discovered_candidates=len(candidates),
        scanner_discovered_shipping=len(keys_by_group["shipping_fields"] & set(candidates)),
    )
    return errors, stats


def validate_registry(
    repo_root: Path, registry_path: Path
) -> tuple[list[str], CoverageStats]:
    try:
        raw_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"cannot read registry {registry_path}: {exc}"], CoverageStats()
    except json.JSONDecodeError as exc:
        return [f"cannot parse registry {registry_path}: {exc}"], CoverageStats()
    if not isinstance(raw_registry, dict):
        return ["registry root must be an object"], CoverageStats()
    return validate_registry_data(repo_root.resolve(), raw_registry)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help="LibreOffice source root (defaults to this script's repository)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("qa/windows-ui-contract/search-field-coverage.json"),
        help="registry path, relative to --root unless absolute",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.root.resolve()
    registry_path = args.registry
    if not registry_path.is_absolute():
        registry_path = repo_root / registry_path

    errors, stats = validate_registry(repo_root, registry_path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"Search-field coverage validation failed with {len(errors)} error(s).",
            file=sys.stderr,
        )
        return 1

    manually_audited = stats.shipping_fields - stats.scanner_discovered_shipping
    print(
        "Search-field coverage validated: "
        f"{stats.shipping_fields} shipping, "
        f"{stats.planned_fields} planned, "
        f"{stats.excluded_candidates} explicit exclusions, "
        f"{stats.discovered_candidates} scanner candidates "
        f"({stats.scanner_discovered_shipping} shipping + "
        f"{stats.excluded_candidates} excluded), "
        f"{manually_audited} additional audited shipping controls."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
