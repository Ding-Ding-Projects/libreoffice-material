#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Fail-closed source contract for the Material document-tab STRIP (Windows).

Stage 3 of the tabbed-UI feature delivers ``SfxDocumentTabBar`` -- a
``svtools::TabBar`` subclass that renders one tab per open document, rides the
already-shipped Material TabBar paint path (the ``calc-sheet-tabs`` anatomy) and,
on tab activation, RAISES that document's existing top-level window via the exact
frame-activation path the Window menu uses. It drives the existing
one-window-per-document model; it does NOT host multiple documents in one window.

``qa/windows-ui-contract/document-tab-strip.json`` pins the source shape. This
checker re-derives every fact from the real tree and fails closed on drift:

* TabBar subclass -- the header declares ``SfxDocumentTabBar`` as a subclass of
  ``TabBar`` and overrides ``Paint``; the impl calls ``TabBar::Paint`` (it rides
  the base Material paint rather than inventing pixels).

* Material paint ride -- the impl resolves overlay tokens from
  ``vcl::MaterialTokens`` over ``definition.xml``, gated on
  ``VCL_FILE_WIDGET_THEME`` and NOT high contrast, exactly like ScTabControl; the
  overlay function walks the stored per-tab colours and never consults the
  selection state (``IsPageSelected`` / ``GetCurPageId``).

* Style-sourced rendering -- every rendered attribute comes from the stage-2
  ``SfxDocTabStyle`` through ``SfxDocTabStyle::Normalize``; no hardcoded colour.

* TabsEnabled guard -- the static ``Create`` factory returns ``nullptr`` unless
  ``officecfg::Office::Common::DocumentTabs::TabsEnabled::get()`` is true, so the
  strip cannot construct when tabs are off; ``TabsEnabled`` still defaults
  ``false`` in ``Common.xcs``.

* Frame-raise reuse -- ``RaiseFrameForPage`` reuses the Window-menu pair
  (``VCLUnoHelper::GetWindow(xFrame->getContainerWindow())`` +
  ``GrabFocus`` + ``ToTop(ToTopFlags::RestoreWhenMin)``) and contains NONE of the
  topness-violating primitives (``GetSystemWindow``, ``static_cast<WorkWindow``,
  ``SetMenuBar`` ...). The reference function still exists in framework.

* Production owner/layout -- every normal SfxFrame owns and disposes the strip,
  creates it after its WorkWindow exists, and reserves its preferred height.

* Synchronisation/safety -- open, close, title, active-frame and configuration
  changes refresh strips; disposed UNO frames are skipped; the owning frame is
  restored as active after a cross-window raise.

* Appearance editor/rendering -- the context-menu weld editor creates the first
  dynamic-set entry, losslessly round-trips CSS hex and FontSize, and the shared
  TabBar paint path consumes per-page typography and text colour.

* Build registration -- both the .cxx and the .ui are registered in their .mk.

It is source + wiring evidence only: ``runtime_verified`` is false throughout --
no native build, tab pixels, or window switching is claimed. The mutation suite
in ``bin/test_document_tab_strip.py`` exercises every branch.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
CONTRACT_REL = "qa/windows-ui-contract/document-tab-strip.json"


class ValidationError(Exception):
    """Raised when the document-tab strip contract is violated."""


# --- source loading --------------------------------------------------------


def load_contract(repo_root: Path = REPOSITORY) -> dict:
    with (repo_root / CONTRACT_REL).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_repository(repo_root: Path = REPOSITORY) -> tuple[dict, dict[str, str]]:
    contract = load_contract(repo_root)
    contents: dict[str, str] = {}
    file_keys = (
        "strip_hxx",
        "strip_cxx",
        "appearance_ui",
        "library_mk",
        "uiconfig_mk",
        "frame_hxx",
        "frame_impl_hxx",
        "frame_cxx",
        "frame2_cxx",
        "viewframe_cxx",
        "viewframe2_cxx",
        "tabbar_hxx",
        "tabbar_cxx",
    )
    for key in file_keys:
        rel = contract[key]
        contents[rel] = (repo_root / rel).read_text(encoding="utf-8")
    # The reference source for the reused frame-raise API.
    ref = contract["reused_frame_raise_api"]["reference_source"]
    contents[ref] = (repo_root / ref).read_text(encoding="utf-8")
    # The officecfg schema for the fail-closed default.
    schema = contract["tabs_enabled_guard"]["schema_file"]
    contents[schema] = (repo_root / schema).read_text(encoding="utf-8")
    return contract, contents


# --- helpers ---------------------------------------------------------------


def _function_body(text: str, function: str) -> str | None:
    """Extract the brace-delimited body of the first definition of a function."""

    # Mask comments without changing offsets. LibreOffice commonly places long
    # documentation blocks between a function signature and its opening brace;
    # comment semicolons/braces must not look like declarations or bodies.
    source = re.sub(
        r"//[^\n]*|/\*.*?\*/",
        lambda match: " " * len(match.group(0)),
        text,
        flags=re.DOTALL,
    )
    idx = source.find(function)
    while idx != -1:
        brace = source.find("{", idx)
        semic = source.find(";", idx)
        if brace != -1 and (semic == -1 or brace < semic):
            depth = 0
            i = brace
            while i < len(source):
                if source[i] == "{":
                    depth += 1
                elif source[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return text[brace : i + 1]
                i += 1
            return None
        idx = source.find(function, idx + len(function))
    return None


def _schema_default(xcs: str, prop_name: str) -> str | None:
    start = xcs.find(f'<prop oor:name="{prop_name}"')
    if start == -1:
        return None
    end = xcs.find("</prop>", start)
    if end == -1:
        return None
    block = xcs[start:end]
    a = block.find("<value>")
    if a == -1:
        return None
    b = block.find("</value>", a)
    return block[a + len("<value>") : b]


# --- validation ------------------------------------------------------------


def violations(contract: dict, contents: dict[str, str]) -> list[str]:
    errors: list[str] = []

    hxx = contents[contract["strip_hxx"]]
    cxx = contents[contract["strip_cxx"]]
    ui = contents[contract["appearance_ui"]]
    lib_mk = contents[contract["library_mk"]]
    ui_mk = contents[contract["uiconfig_mk"]]
    frame_hxx = contents[contract["frame_hxx"]]
    frame_impl_hxx = contents[contract["frame_impl_hxx"]]
    frame_cxx = contents[contract["frame_cxx"]]
    frame2_cxx = contents[contract["frame2_cxx"]]
    viewframe_cxx = contents[contract["viewframe_cxx"]]
    viewframe2_cxx = contents[contract["viewframe2_cxx"]]
    tabbar_hxx = contents[contract["tabbar_hxx"]]
    tabbar_cxx = contents[contract["tabbar_cxx"]]

    # runtime_verified must stay false: this is build-free source evidence only.
    if contract.get("runtime_verified") is not False:
        errors.append(
            "contract:runtime_verified -- must be false (no runtime behaviour is claimed)"
        )

    # --- TabBar subclass ---------------------------------------------------
    sub = contract["tabbar_subclass"]
    for marker in sub["hxx_must_contain"]:
        if marker not in hxx:
            errors.append(f"subclass:hxx -- missing marker {marker!r}")
    if sub["cxx_base_paint_call"] not in cxx:
        errors.append(
            f"subclass:cxx -- missing base paint call {sub['cxx_base_paint_call']!r} "
            "(the strip must ride the base Material TabBar paint)"
        )

    # --- Material paint ride ----------------------------------------------
    paint = contract["material_paint_ride"]
    if paint["include"] not in cxx:
        errors.append(f"material:cxx -- missing include {paint['include']!r}")
    if paint["env_guard"] not in cxx:
        errors.append(f"material:cxx -- missing env guard {paint['env_guard']!r}")
    if paint["high_contrast_guard"] not in cxx:
        errors.append(
            f"material:cxx -- missing high-contrast guard {paint['high_contrast_guard']!r}"
        )
    for marker in paint["markers"]:
        if marker not in cxx:
            errors.append(f"material:cxx -- missing token/overlay marker {marker!r}")

    overlay = paint["overlay_independence"]
    body = _function_body(cxx, overlay["function"])
    if body is None:
        errors.append(
            f"material:overlay -- function {overlay['function']!r} not found"
        )
    else:
        for marker in overlay["must_contain"]:
            if marker not in body:
                errors.append(
                    f"material:overlay -- {overlay['function']} missing {marker!r}"
                )
        for marker in overlay["must_not_contain"]:
            if marker in body:
                errors.append(
                    f"material:overlay -- {overlay['function']} must not consult "
                    f"selection state {marker!r} (the accent must be selection-independent)"
                )

    # --- style-sourced rendering ------------------------------------------
    style = contract["style_sourced_rendering"]
    if style["include"] not in cxx:
        errors.append(f"style:cxx -- missing include {style['include']!r}")
    for marker in style["markers"]:
        if marker not in cxx:
            errors.append(f"style:cxx -- missing style marker {marker!r}")
    for marker in style["must_not_contain_hardcoded"]:
        if marker in cxx:
            errors.append(
                f"style:cxx -- hardcoded colour literal {marker!r} present "
                "(every rendered attribute must come from SfxDocTabStyle)"
            )

    # --- TabsEnabled guard -------------------------------------------------
    guard = contract["tabs_enabled_guard"]
    for marker in guard["markers"]:
        if marker not in cxx:
            errors.append(f"guard:cxx -- missing guard marker {marker!r}")
    # The factory must return nullptr on the disabled branch: the guard markers
    # 'if (!IsTabsEnabled())' and 'return nullptr;' both being present is checked
    # above; verify they belong to the factory body.
    factory = _function_body(cxx, guard["factory_function"])
    if factory is None:
        errors.append(f"guard:cxx -- factory {guard['factory_function']!r} not found")
    else:
        if "if (!IsTabsEnabled())" not in factory or "return nullptr;" not in factory:
            errors.append(
                "guard:cxx -- factory must return nullptr when tabs are disabled "
                "(the strip cannot construct when TabsEnabled is false)"
            )
    xcs = contents[guard["schema_file"]]
    default = _schema_default(xcs, guard["schema_default_property"])
    if default != guard["schema_required_default"]:
        errors.append(
            f"guard:schema -- {guard['schema_default_property']} default {default!r} != "
            f"required {guard['schema_required_default']!r} (tabs must stay off by default)"
        )

    # --- frame-raise reuse -------------------------------------------------
    raise_api = contract["reused_frame_raise_api"]
    raise_body = _function_body(cxx, "SfxDocumentTabBar::RaiseFrameForPage")
    if raise_body is None:
        errors.append("raise:cxx -- RaiseFrameForPage not found")
    else:
        for marker in raise_api["strip_must_contain"]:
            if marker not in raise_body:
                errors.append(f"raise:cxx -- RaiseFrameForPage missing {marker!r}")
        for marker in raise_api["strip_must_not_contain"]:
            if marker in raise_body:
                errors.append(
                    f"raise:cxx -- RaiseFrameForPage must not use topness-violating "
                    f"primitive {marker!r}"
                )
    # The reference function the reuse points at must still exist.
    ref_src = contents[raise_api["reference_source"]]
    ref_body = _function_body(ref_src, raise_api["reference_function"])
    if ref_body is None:
        errors.append(
            f"raise:reference -- {raise_api['reference_function']} not found in "
            f"{raise_api['reference_source']} (the reused frame-raise path vanished)"
        )
    else:
        for marker in raise_api["reference_markers"]:
            if marker not in ref_body:
                errors.append(
                    f"raise:reference -- {raise_api['reference_function']} no longer "
                    f"contains {marker!r} (the reused frame-raise path drifted)"
                )

    # --- appearance editor -------------------------------------------------
    editor = contract["appearance_editor"]
    if editor["context_menu_marker"] not in cxx:
        errors.append(
            f"editor:cxx -- missing context-menu marker {editor['context_menu_marker']!r}"
        )
    for marker in editor["cxx_markers"]:
        if marker not in cxx:
            errors.append(f"editor:cxx -- missing marker {marker!r}")
    for marker in editor.get("cxx_must_not_contain", []):
        if marker in cxx:
            errors.append(f"editor:cxx -- forbidden lossy/stale marker {marker!r}")
    if f'id="{editor["ui_dialog_id"]}"' not in ui:
        errors.append(f"editor:ui -- missing dialog id {editor['ui_dialog_id']!r}")
    for wid in editor["ui_required_ids"]:
        if f'id="{wid}"' not in ui:
            errors.append(f"editor:ui -- missing widget id {wid!r}")

    # --- production owner and layout --------------------------------------
    owner = contract["production_owner_and_layout"]
    owner_sources = frame_impl_hxx + "\n" + frame_cxx
    for marker in owner["owner_markers"]:
        if marker not in owner_sources:
            errors.append(f"owner:lifetime -- missing marker {marker!r}")
    create_body = _function_body(frame_cxx, owner["create_function"])
    if create_body is None:
        errors.append(f"owner:create -- function {owner['create_function']!r} not found")
    else:
        for marker in owner["create_markers"]:
            if marker not in create_body:
                errors.append(f"owner:create -- missing marker {marker!r}")
    workwindow_body = _function_body(frame_cxx, owner["workwindow_function"])
    if workwindow_body is None:
        errors.append(
            f"owner:workwindow -- function {owner['workwindow_function']!r} not found"
        )
    else:
        for marker in owner["workwindow_markers"]:
            if marker not in workwindow_body:
                errors.append(f"owner:workwindow -- missing marker {marker!r}")
    layout_body = _function_body(frame_cxx, owner["layout_function"])
    if layout_body is None:
        errors.append(f"owner:layout -- function {owner['layout_function']!r} not found")
    else:
        for marker in owner["layout_markers"]:
            if marker not in layout_body:
                errors.append(f"owner:layout -- missing marker {marker!r}")
        for marker in owner.get("layout_must_not_contain", []):
            if marker in layout_body:
                errors.append(f"owner:layout -- forbidden marker {marker!r}")
    for marker in (
        "RefreshDocumentTabBar_Impl",
        "RefreshDocumentTabBars_Impl",
    ):
        if marker not in frame_hxx:
            errors.append(f"owner:api -- frame header missing {marker!r}")

    # --- synchronization and disposed-frame safety ------------------------
    sync = contract["synchronization_and_safety"]
    sync_sources = {
        "frame_cxx": frame_cxx,
        "frame2_cxx": frame2_cxx,
        "viewframe_cxx": viewframe_cxx,
        "viewframe2_cxx": viewframe2_cxx,
        "strip_cxx": cxx,
    }
    for source_name, markers in sync["sync_markers"].items():
        source = sync_sources[source_name]
        for marker in markers:
            if marker not in source:
                errors.append(
                    f"sync:{source_name} -- missing refresh marker {marker!r}"
                )
    for marker in sync["strip_markers"]:
        if marker not in cxx:
            errors.append(f"safety:strip -- missing marker {marker!r}")
    for requirement in sync.get("function_markers", []):
        source_name = requirement["source"]
        body = _function_body(sync_sources[source_name], requirement["function"])
        if body is None:
            errors.append(
                f"sync:{source_name} -- function {requirement['function']!r} not found"
            )
            continue
        for marker in requirement["markers"]:
            if marker not in body:
                errors.append(
                    f"sync:{source_name} -- {requirement['function']} missing {marker!r}"
                )
    select_body = _function_body(cxx, "SfxDocumentTabBar::Select()")
    if select_body is None or "SelectOwnerFrame();" not in select_body:
        errors.append(
            "sync:selection -- Select must restore the owner page after raising a frame"
        )

    # --- per-page rendering hooks -----------------------------------------
    for marker in ("SetPageFont", "SetPageTextColor"):
        if marker not in tabbar_hxx:
            errors.append(f"style:tabbar-hxx -- missing per-page API {marker!r}")
        if marker not in tabbar_cxx:
            errors.append(f"style:tabbar-cxx -- per-page API {marker!r} is not implemented")
    for marker in (
        "pItem->moPageFont.value_or",
        "pItem->moPageTextColor",
    ):
        if marker not in tabbar_cxx:
            errors.append(f"style:tabbar-cxx -- missing paint-path marker {marker!r}")

    # --- CSS hex decode and lossless editor round-trip --------------------
    hex_contract = contract["hex_roundtrip"]
    parse_body = _function_body(cxx, hex_contract["function"])
    if parse_body is None:
        errors.append(f"hex:decode -- function {hex_contract['function']!r} not found")
    else:
        for marker in hex_contract["must_contain"]:
            if marker not in parse_body:
                errors.append(f"hex:decode -- missing marker {marker!r}")
        for marker in hex_contract["must_not_contain"]:
            if marker in parse_body:
                errors.append(f"hex:decode -- forbidden lossy marker {marker!r}")
    for marker in hex_contract["roundtrip_markers"]:
        if marker not in cxx:
            errors.append(f"hex:roundtrip -- missing marker {marker!r}")

    # --- Favorite behaviour and schema honesty ----------------------------
    favorite = contract["favorite_and_schema_honesty"]
    for marker in favorite["favorite_markers"]:
        if marker not in cxx:
            errors.append(f"favorite:behavior -- missing marker {marker!r}")
    for marker in favorite["schema_markers"]:
        if marker not in xcs:
            errors.append(f"schema:honesty -- missing marker {marker!r}")

    # --- build registration ------------------------------------------------
    reg = contract["build_registration"]
    if reg["library_entry"] not in lib_mk:
        errors.append(
            f"build:library -- {reg['library_entry']!r} not registered in "
            f"{contract['library_mk']}"
        )
    if reg["uiconfig_entry"] not in ui_mk:
        errors.append(
            f"build:uiconfig -- {reg['uiconfig_entry']!r} not registered in "
            f"{contract['uiconfig_mk']}"
        )
    for required_include in reg.get("source_required_includes", []):
        marker = f"#include {required_include}"
        if marker not in cxx:
            errors.append(
                f"build:include -- required definition include {marker!r} missing "
                f"from {contract['strip_cxx']}"
            )

    return errors


# --- entry point -----------------------------------------------------------


def run(repo_root: Path = REPOSITORY) -> list[str]:
    contract, contents = load_repository(repo_root)
    return violations(contract, contents)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=REPOSITORY, help="repository root"
    )
    args = parser.parse_args(argv)

    try:
        errors = run(args.repo)
    except FileNotFoundError as exc:
        print(f"FAIL document-tab-strip: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("FAIL document-tab-strip contract:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("OK document-tab-strip: Material tab strip contract satisfied (runtime unverified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
