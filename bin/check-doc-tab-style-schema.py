#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed source contract for the Material document-tab style schema (Windows).

Stage 2 of the tabbed-UI feature is PERSISTENCE + VALIDATION only. It adds the
officecfg schema for document-tab styles (an ``Appearance/DocumentTabs`` group
and a ``Histories/DocumentTabStyles`` set, node-type ``DocumentTabStyle``) and a
clamp-on-read normalizer (``SfxDocTabStyle::Normalize`` in
``sfx2/source/appl/doctabstyle.cxx``). It adds NO tab strip and NO frame
changes.

``qa/windows-ui-contract/doc-tab-style-schema.json`` pins the two surfaces. This
checker re-derives every fact from the real tree and fails closed on drift:

* Schema declaration -- for each pinned property the ``Common.xcs`` declaration,
  read from the property's own group/template scope, must carry the expected
  ``oor:type``; the expected ``<value>`` default (or none, for a per-instance
  set property with no default); the exact closed ``<enumeration>`` set (no
  more, no fewer); and, where a clamp is declared, the exact
  ``minInclusive`` / ``maxInclusive`` bounds. A drifted type, a changed default,
  an added/removed enumeration, or a widened clamp fails closed.

* Fail-closed default -- ``TabsEnabled`` MUST default to ``false``. Any other
  default (the tabs-on regression) fails closed independently of the per-property
  default check.

* Normalizer parity -- the comment-stripped body of ``SfxDocTabStyle::Normalize``
  must contain exactly one branch per pinned property, keyed by the property name
  as a ``u"Name"`` string literal, and NO branch keyed to a name that is not a
  pinned property. A schema property with no normalizer branch, OR a normalizer
  branch with no schema property, fails closed -- the two sets must be equal.

It is source + wiring evidence only: ``runtime_verified`` is false throughout --
no native build, config round-trip, or runtime observation is claimed. The C++
is compile-plausibility only. The mutation suite in
``bin/test_doc_tab_style_schema.py`` exercises every branch.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPOSITORY / "qa/windows-ui-contract/doc-tab-style-schema.json"


class ValidationError(Exception):
    """Raised when the document-tab style contract is violated."""


# --- source loading --------------------------------------------------------


def load_contract(repo_root: Path = REPOSITORY) -> dict:
    with (repo_root / "qa/windows-ui-contract/doc-tab-style-schema.json").open(
        encoding="utf-8"
    ) as handle:
        return json.load(handle)


def load_repository(repo_root: Path = REPOSITORY) -> tuple[dict, dict[str, str]]:
    contract = load_contract(repo_root)
    contents: dict[str, str] = {}
    for key in ("schema_file", "normalizer_cxx", "normalizer_hxx"):
        rel = contract[key]
        contents[rel] = (repo_root / rel).read_text(encoding="utf-8")
    return contract, contents


# --- helpers ---------------------------------------------------------------


def _strip_cxx_comments(text: str) -> str:
    """Remove // and /* */ comments, preserving string/char literals."""

    out: list[str] = []
    i, n = 0, len(text)
    state = "code"
    quote = ""
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if c == "/" and nxt == "/":
                state = "line"
                i += 2
                continue
            if c == "/" and nxt == "*":
                state = "block"
                i += 2
                continue
            if c in ('"', "'"):
                state = "quote"
                quote = c
                out.append(c)
                i += 1
                continue
            out.append(c)
            i += 1
            continue
        if state == "line":
            if c == "\n":
                state = "code"
                out.append(c)
            i += 1
            continue
        if state == "block":
            if c == "\n":
                out.append("\n")
            if c == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue
        # quote
        out.append(c)
        if c == "\\":
            if i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            i += 1
            continue
        if c == quote:
            state = "code"
        i += 1
    return "".join(out)


def _group_scope(xcs: str, group_name: str) -> str | None:
    """Return the text of a <group oor:name="NAME"> ... </group> block.

    The document-tab groups/templates do not nest a child <group>, so the
    first </group> after the opening tag closes the block.
    """

    start = xcs.find(f'<group oor:name="{group_name}">')
    if start == -1:
        return None
    end = xcs.find("</group>", start)
    if end == -1:
        return None
    return xcs[start : end + len("</group>")]


def _prop_scope(scope: str, prop_name: str) -> str | None:
    """Return the <prop oor:name="NAME" ...> ... </prop> text within a scope."""

    start = scope.find(f'<prop oor:name="{prop_name}"')
    if start == -1:
        return None
    end = scope.find("</prop>", start)
    if end == -1:
        return None
    return scope[start : end + len("</prop>")]


def _declared_type(prop_text: str) -> str | None:
    match = re.search(r'oor:type="([^"]+)"', prop_text)
    return match.group(1) if match else None


def _declared_default(prop_text: str) -> str | None:
    match = re.search(r"<value>([^<]*)</value>", prop_text)
    return match.group(1) if match else None


def _declared_enum(prop_text: str) -> list[str]:
    return re.findall(r'<enumeration oor:value="([^"]*)"', prop_text)


def _declared_clamp(prop_text: str) -> dict[str, str] | None:
    lo = re.search(r'<minInclusive oor:value="([^"]*)"', prop_text)
    hi = re.search(r'<maxInclusive oor:value="([^"]*)"', prop_text)
    if lo is None and hi is None:
        return None
    return {"min": lo.group(1) if lo else None, "max": hi.group(1) if hi else None}


def _normalize_body(cxx: str, function: str) -> str | None:
    """Extract the brace-delimited body of the Normalize function."""

    # e.g. SfxDocTabStyle::Normalize
    idx = cxx.find(function)
    while idx != -1:
        # Skip the declaration in the header-style forward references; require a
        # following '{' before the next ';'.
        brace = cxx.find("{", idx)
        semic = cxx.find(";", idx)
        if brace != -1 and (semic == -1 or brace < semic):
            depth = 0
            i = brace
            while i < len(cxx):
                if cxx[i] == "{":
                    depth += 1
                elif cxx[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return cxx[brace : i + 1]
                i += 1
            return None
        idx = cxx.find(function, idx + len(function))
    return None


def _branch_keys(body: str) -> list[str]:
    """Every u"Word" literal used as a branch key in the Normalize body."""

    return re.findall(r'rsKey == u"([A-Za-z0-9]+)"', body)


# --- validation ------------------------------------------------------------


def violations(contract: dict, contents: dict[str, str]) -> list[str]:
    errors: list[str] = []

    xcs = contents[contract["schema_file"]]
    cxx_raw = contents[contract["normalizer_cxx"]]
    cxx = _strip_cxx_comments(cxx_raw)

    all_props: list[dict] = []
    schema_branches: set[str] = set()

    for group_name, group in contract["groups"].items():
        scope = _group_scope(xcs, group_name)
        if scope is None:
            errors.append(
                f"schema:{group_name} -- no <group oor:name=\"{group_name}\"> block "
                f"found in {contract['schema_file']}"
            )
            continue
        for prop in group["properties"]:
            all_props.append(prop)
            schema_branches.add(prop["normalizer_branch"])
            name = prop["name"]
            prop_text = _prop_scope(scope, name)
            if prop_text is None:
                errors.append(
                    f"schema:{group_name}/{name} -- property not declared in its group scope"
                )
                continue

            declared_type = _declared_type(prop_text)
            if declared_type != prop["type"]:
                errors.append(
                    f"schema:{group_name}/{name} -- type {declared_type!r} != "
                    f"expected {prop['type']!r}"
                )

            declared_default = _declared_default(prop_text)
            if declared_default != prop["default"]:
                errors.append(
                    f"schema:{group_name}/{name} -- default {declared_default!r} != "
                    f"expected {prop['default']!r}"
                )

            declared_enum = _declared_enum(prop_text)
            expected_enum = prop["enum"]
            if expected_enum is None:
                if declared_enum:
                    errors.append(
                        f"schema:{group_name}/{name} -- unexpected enumeration "
                        f"{declared_enum} (property is not a closed enum)"
                    )
            elif declared_enum != expected_enum:
                errors.append(
                    f"schema:{group_name}/{name} -- enumeration {declared_enum} != "
                    f"expected closed set {expected_enum}"
                )

            declared_clamp = _declared_clamp(prop_text)
            expected_clamp = prop["clamp"]
            if expected_clamp is None:
                if declared_clamp is not None:
                    errors.append(
                        f"schema:{group_name}/{name} -- unexpected clamp "
                        f"{declared_clamp} (no clamp range expected)"
                    )
            elif declared_clamp != expected_clamp:
                errors.append(
                    f"schema:{group_name}/{name} -- clamp {declared_clamp} != "
                    f"expected {expected_clamp}"
                )

    # Fail-closed default: TabsEnabled MUST be false.
    fcd = contract["fail_closed_default"]
    tabs_scope = _group_scope(xcs, "DocumentTabs")
    if tabs_scope is not None:
        prop_text = _prop_scope(tabs_scope, fcd["property"])
        declared = _declared_default(prop_text) if prop_text else None
        if declared != fcd["required_default"]:
            errors.append(
                f"fail-closed:{fcd['property']} -- default {declared!r} != required "
                f"{fcd['required_default']!r}; tabs must be OFF by default"
            )

    # Normalizer parity: branch key set == schema branch set (both directions).
    body = _normalize_body(cxx, contract["normalizer_function"].split("::")[-1])
    if body is None:
        errors.append(
            f"normalizer -- could not locate the body of "
            f"{contract['normalizer_function']} in {contract['normalizer_cxx']}"
        )
    else:
        actual = _branch_keys(body)
        actual_set = set(actual)
        # duplicate branch for one key is also drift
        if len(actual) != len(actual_set):
            dupes = sorted({k for k in actual if actual.count(k) > 1})
            errors.append(f"normalizer -- duplicate branch key(s): {dupes}")
        missing = sorted(schema_branches - actual_set)
        for name in missing:
            errors.append(
                f"normalizer -- schema property {name!r} has no clamp branch "
                f'(expected `rsKey == u"{name}"`)'
            )
        extra = sorted(actual_set - schema_branches)
        for name in extra:
            errors.append(
                f"normalizer -- clamp branch {name!r} has no matching schema property"
            )

    return errors


def validate_repository(repo_root: Path = REPOSITORY) -> None:
    contract, contents = load_repository(repo_root)
    errors = violations(contract, contents)
    if errors:
        raise ValidationError("\n".join(errors))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.repo_root.resolve()
    try:
        validate_repository(repo_root)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(f"Document-tab style schema contract failed:\n{error}", file=sys.stderr)
        return 1
    print(
        "Document-tab style schema contract passed: every Appearance/DocumentTabs and "
        "DocumentTabStyle property in Common.xcs carries the pinned type/default/enum/clamp, "
        "TabsEnabled defaults to false, and SfxDocTabStyle::Normalize has exactly one clamp "
        "branch per property (no orphan branch, no unguarded property). Static source "
        "cross-check only -- no build or runtime behaviour is claimed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
