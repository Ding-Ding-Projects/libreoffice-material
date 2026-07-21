#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Mutation regressions for native regex-search field integrations."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-windows-regex-search-integrations.py"
SPEC = importlib.util.spec_from_file_location(
    "check_windows_regex_search_integrations", VALIDATOR_PATH
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


class WindowsRegexSearchIntegrationsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, self.coverage, self.contents = VALIDATOR.load_repository(REPOSITORY)
        self.entry = self.registry["integrations"][0]

    def failures(
        self,
        *,
        registry: dict | None = None,
        coverage: dict | None = None,
        contents: dict[str, str] | None = None,
    ) -> list[str]:
        return VALIDATOR.violations(
            self.registry if registry is None else registry,
            self.coverage if coverage is None else coverage,
            self.contents if contents is None else contents,
        )

    def test_production_contract(self) -> None:
        VALIDATOR.validate_repository(REPOSITORY)
        self.assertEqual([], self.failures())

    def test_shipping_inventory_link_is_required(self) -> None:
        registry = copy.deepcopy(self.registry)
        registry["integrations"] = []
        registry["expected_integrations"] = 0
        self.assertIn(
            "registry:integrations:at least one source integration required",
            self.failures(registry=registry),
        )

        coverage = copy.deepcopy(self.coverage)
        for item in coverage["shipping_fields"]:
            if item["coverage_id"] == self.entry["coverage_id"]:
                item["widget_id"] = "different-entry"
                break
        self.assertTrue(
            any(
                error.endswith("registry locator or policy mismatch")
                for error in self.failures(coverage=coverage)
            )
        )

    def test_adjacent_builder_button_is_structural(self) -> None:
        contents = dict(self.contents)
        ui_file = self.entry["ui_file"]
        contents[ui_file] = contents[ui_file].replace(
            f'id="{self.entry["builder_button_id"]}"', 'id="removed-regex-builder"', 1
        )
        self.assertTrue(any(":ui-button:" in error for error in self.failures(contents=contents)))

        contents = dict(self.contents)
        contents[ui_file] = contents[ui_file].replace(
            '<property name="orientation">horizontal</property>',
            '<property name="orientation">vertical</property>',
            1,
        )
        self.assertTrue(any(":ui-parent:" in error for error in self.failures(contents=contents)))

    def test_accessible_name_description_and_tooltip_are_required(self) -> None:
        ui_file = self.entry["ui_file"]
        for marker, replacement, failure in (
            (
                '<property name="tooltip-text" translatable="yes" '
                'context="gotosheetdialog|entry-mask_regex_builder|tooltip_text">',
                '<property name="removed-tooltip" translatable="yes" '
                'context="gotosheetdialog|entry-mask_regex_builder|tooltip_text">',
                ":ui-accessibility:tooltip missing",
            ),
            (
                '<property name="AtkObject::accessible-name" translatable="yes" '
                'context="gotosheetdialog|entry-mask_regex_builder-atkobject">',
                '<property name="removed-accessible-name" translatable="yes" '
                'context="gotosheetdialog|entry-mask_regex_builder-atkobject">',
                ":ui-accessibility:AtkObject::accessible-name missing",
            ),
            (
                '<property name="AtkObject::accessible-description" translatable="yes" '
                'context="gotosheetdialog|extended_tip|entry-mask_regex_builder">',
                '<property name="removed-accessible-description" translatable="yes" '
                'context="gotosheetdialog|extended_tip|entry-mask_regex_builder">',
                ":ui-accessibility:AtkObject::accessible-description missing",
            ),
        ):
            with self.subTest(marker=marker):
                contents = dict(self.contents)
                contents[ui_file] = contents[ui_file].replace(marker, replacement, 1)
                self.assertTrue(
                    any(error.endswith(failure) for error in self.failures(contents=contents))
                )

        contents = dict(self.contents)
        contents[ui_file] = contents[ui_file].replace(
            '<property name="AtkObject::accessible-name" translatable="yes" '
            'context="gotosheetdialog|entry-mask_regex_builder-atkobject">',
            '<property name="AtkObject::accessible-name" translatable="no" '
            'context="gotosheetdialog|entry-mask_regex_builder-atkobject">',
            1,
        )
        self.assertTrue(
            any(
                error.endswith(
                    ":ui-accessibility:AtkObject::accessible-name must be translated"
                )
                for error in self.failures(contents=contents)
            )
        )

    def test_controller_must_own_the_existing_changed_handler(self) -> None:
        contents = dict(self.contents)
        source_file = self.entry["source_file"]
        contents[source_file] = contents[source_file].replace(
            f"LINK(this, {self.entry['owner_type']}, {self.entry['owner_changed_handler']})",
            "Link<weld::TextWidget&, void>()",
            1,
        )
        contents[source_file] += (
            "\n// A comment cannot satisfy the controller-owned callback contract: "
            f"LINK(this, {self.entry['owner_type']}, "
            f"{self.entry['owner_changed_handler']})\n"
        )
        self.assertTrue(
            any(
                error.endswith("source-wiring:controller constructor mismatch")
                for error in self.failures(contents=contents)
            )
        )

        contents = dict(self.contents)
        contents[source_file] += (
            f"\n// forbidden bypass\n{self.entry['entry_member']}->connect_changed("
            "Link<weld::TextWidget&, void>());\n"
        )
        self.assertTrue(
            any(
                error.endswith("direct changed handler bypasses controller")
                for error in self.failures(contents=contents)
            )
        )

        contents = dict(self.contents)
        header_file = self.entry["header_file"]
        controller_declaration = (
            "    std::unique_ptr<sfx2::RegexSearchController> "
            f"{self.entry['controller_member']};\n"
        )
        button_declaration = (
            f"    std::unique_ptr<weld::Button> {self.entry['builder_member']};\n"
        )
        header = contents[header_file].replace(controller_declaration, "", 1)
        contents[header_file] = header.replace(
            button_declaration,
            controller_declaration + button_declaration,
            1,
        )
        self.assertTrue(
            any(
                error.endswith("header:lifetime:controller must follow the entry and button")
                for error in self.failures(contents=contents)
            )
        )

    def test_literal_case_sensitive_compatibility_is_guarded(self) -> None:
        source_file = self.entry["source_file"]
        for marker in (
            "aState.Mode = sfx2::RegexSearchMode::Literal;",
            "aState.Flags.CaseInsensitive = false;",
        ):
            with self.subTest(marker=marker):
                contents = dict(self.contents)
                contents[source_file] = contents[source_file].replace(marker, "", 1)
                self.assertTrue(
                    any(
                        ":literal-default:missing" in error
                        for error in self.failures(contents=contents)
                    )
                )

    def test_compiled_matcher_and_search_options_are_exactly_once(self) -> None:
        source_file = self.entry["source_file"]
        for marker, failure in (
            ("std::make_unique<utl::TextSearch>", "handler-compiled-matcher"),
            (f"{self.entry['controller_member']}->GetSearchOptions()", "handler-search-options"),
            ("xSearch->searchForward", "handler-matching"),
        ):
            with self.subTest(marker=marker):
                contents = dict(self.contents)
                contents[source_file] = contents[source_file].replace(marker, "removed", 1)
                self.assertTrue(
                    any(failure in error for error in self.failures(contents=contents))
                )

    def test_matcher_compilation_cannot_move_inside_the_item_loop(self) -> None:
        contents = dict(self.contents)
        source_file = self.entry["source_file"]
        source = contents[source_file]
        build = (
            "    if (bValid && !bEmpty && !bLegacyCompatibleLiteral)\n"
            "        xSearch = std::make_unique<utl::TextSearch>("
            "m_xRegexSearchController->GetSearchOptions());\n\n"
        )
        self.assertIn(build, source)
        source = source.replace(build, "", 1)
        source = source.replace(
            "    for (const OUString& rSheetName : maCacheSheetsNames)\n    {\n",
            "    for (const OUString& rSheetName : maCacheSheetsNames)\n"
            "    {\n"
            "        if (bValid && !bEmpty && !bLegacyCompatibleLiteral)\n"
            "            xSearch = std::make_unique<utl::TextSearch>("
            "m_xRegexSearchController->GetSearchOptions());\n",
            1,
        )
        contents[source_file] = source
        self.assertTrue(
            any(
                ":compiled-once:matcher must be built before the loop" in error
                for error in self.failures(contents=contents)
            )
        )

        contents = dict(self.contents)
        contents[source_file] = contents[source_file].replace(
            "        if (bEmpty\n",
            "        while (bEmpty\n",
            1,
        )
        self.assertTrue(
            any(
                error.endswith("handler-zero-width:repeated matcher loop forbidden")
                for error in self.failures(contents=contents)
            )
        )

    def test_invalid_regex_remains_fail_closed(self) -> None:
        source_file = self.entry["source_file"]
        for marker, replacement, failure in (
            (
                "sfx2::RegexSearchService::Validate(rState)",
                "removedValidation(rState)",
                ":handler-validation:expected exactly 1",
            ),
            (
                "bEmpty\n            || (bLegacyCompatibleLiteral &&",
                "removedFailClosedRoute\n            || (bLegacyCompatibleLiteral &&",
                ":handler:empty/invalid fail-closed route missing",
            ),
        ):
            with self.subTest(marker=marker):
                contents = dict(self.contents)
                contents[source_file] = contents[source_file].replace(marker, replacement, 1)
                self.assertTrue(
                    any(
                        error.endswith(failure)
                        for error in self.failures(contents=contents)
                    )
                )

    def test_exact_legacy_literal_matching_cannot_be_replaced(self) -> None:
        contents = dict(self.contents)
        source_file = self.entry["source_file"]
        contents[source_file] = contents[source_file].replace(
            "rSheetName.indexOf(rState.Pattern)",
            "rSheetName.lastIndexOf(rState.Pattern)",
            1,
        )
        self.assertTrue(
            any(
                ":handler-legacy-literal:expected exactly 1" in error
                for error in self.failures(contents=contents)
            )
        )


# ---------------------------------------------------------------------------
# Synthetic fixtures for the parameterized branches.  Only the Calc and Start
# Center fields are registered against real source, and both use the
# entry/legacy/case-sensitive shape.  The other supported parameter combinations
# (editable combo box, case-insensitive literal default, options hand-off, native
# regex toggle sync) are exercised with fully-valid synthetic .ui/header/source so
# each new branch has fail-closed mutation coverage independent of any real file.
# ---------------------------------------------------------------------------

UI_FILE = "fixture/uiconfig/ui/fixture.ui"
HEADER_FILE = "fixture/inc/fixture.hxx"
SOURCE_FILE = "fixture/source/fixture.cxx"

# A synthetic controller source carrying the three shared-controller
# accessibility markers so fixture registries validate clean.
FIXTURE_CONTROLLER = (
    "set_accessible_name(SfxResId(STR_REGEX_BUILDER_ACCESSIBLE_NAME))\n"
    "set_accessible_description(\n"
    "        SfxResId(STR_REGEX_BUILDER_ACCESSIBLE_DESCRIPTION))\n"
    "set_tooltip_text(SfxResId(STR_REGEX_BUILDER_TOOLTIP))\n"
)

_ENTRY_ID = "fixture_search"
_BUTTON_ID = "fixture_search_regex_builder"
_TOGGLE_ID = "fixture_regexp"
_ENTRY_MEMBER = "m_xEntry"
_BUTTON_MEMBER = "m_xButton"
_TOGGLE_MEMBER = "m_xRegexToggle"
_CONTROLLER_MEMBER = "m_xController"
_OWNER = "FixtureDialog"
_HANDLER = "SearchHdl"
_HANDOFF_SINK = "m_xSearchEngine->ExecuteSearch"


def _fixture_ui(*, entry_class: str, has_entry: bool, native_toggle: bool) -> str:
    has_entry_line = (
        '        <property name="has-entry">True</property>\n' if has_entry else ""
    )
    toggle_block = (
        f'  <object class="GtkCheckButton" id="{_TOGGLE_ID}">\n'
        '    <property name="label">Regular expression</property>\n'
        "  </object>\n"
        if native_toggle
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<interface>\n"
        '  <object class="GtkBox" id="fixture_box">\n'
        '    <property name="visible">True</property>\n'
        '    <property name="orientation">horizontal</property>\n'
        '    <property name="spacing">6</property>\n'
        "    <child>\n"
        f'      <object class="{entry_class}" id="{_ENTRY_ID}">\n'
        '        <property name="visible">True</property>\n'
        '        <property name="can-focus">True</property>\n'
        '        <property name="hexpand">True</property>\n'
        f"{has_entry_line}"
        "      </object>\n"
        "      <packing>\n"
        '        <property name="expand">True</property>\n'
        '        <property name="fill">True</property>\n'
        '        <property name="position">0</property>\n'
        "      </packing>\n"
        "    </child>\n"
        "    <child>\n"
        f'      <object class="GtkButton" id="{_BUTTON_ID}">\n'
        '        <property name="label">.*</property>\n'
        '        <property name="visible">True</property>\n'
        '        <property name="can-focus">True</property>\n'
        '        <property name="receives-default">False</property>\n'
        '        <property name="tooltip-text" translatable="yes" '
        'context="fixture|tt">Build a regular expression</property>\n'
        '        <child internal-child="accessible">\n'
        f'          <object class="AtkObject" id="{_BUTTON_ID}-atkobject">\n'
        '            <property name="AtkObject::accessible-name" translatable="yes" '
        'context="fixture|an">Regular expression builder</property>\n'
        '            <property name="AtkObject::accessible-description" translatable="yes" '
        'context="fixture|ad">Open the builder.</property>\n'
        "          </object>\n"
        "        </child>\n"
        "      </object>\n"
        "      <packing>\n"
        '        <property name="expand">False</property>\n'
        '        <property name="fill">True</property>\n'
        '        <property name="position">1</property>\n'
        "      </packing>\n"
        "    </child>\n"
        "  </object>\n"
        f"{toggle_block}"
        "</interface>\n"
    )


def _fixture_header(*, member_type: str, native_toggle: bool) -> str:
    toggle_decl = (
        f"    std::unique_ptr<weld::CheckButton> {_TOGGLE_MEMBER};\n"
        if native_toggle
        else ""
    )
    return (
        "class RegexSearchController;\n"
        "class FixtureDialog\n"
        "{\n"
        f"    std::unique_ptr<{member_type}> {_ENTRY_MEMBER};\n"
        f"    std::unique_ptr<weld::Button> {_BUTTON_MEMBER};\n"
        f"{toggle_decl}"
        f"    std::unique_ptr<sfx2::RegexSearchController> {_CONTROLLER_MEMBER};\n"
        "};\n"
    )


def _fixture_source(
    *,
    widget_kind: str,
    matcher_strategy: str,
    case_insensitive_literal: str,
    match_subject: str = "rItem",
) -> str:
    weld_factory = "weld_entry" if widget_kind == "entry" else "weld_combo_box"
    arg = "weld::TextWidget&" if widget_kind == "entry" else "weld::ComboBox&"

    includes = "#include <sfx2/RegexSearchController.hxx>\n"
    if matcher_strategy == "legacy-literal-or-compiled-once-utl-textsearch":
        includes += "#include <unotools/textsearch.hxx>\n"

    ctor_init = (
        f'    : {_ENTRY_MEMBER}(m_xBuilder->{weld_factory}(u"{_ENTRY_ID}"_ustr))\n'
        f'    , {_BUTTON_MEMBER}(m_xBuilder->weld_button(u"{_BUTTON_ID}"_ustr))\n'
    )
    if matcher_strategy == "native-regex-option-sync":
        ctor_init += (
            f'    , {_TOGGLE_MEMBER}(m_xBuilder->weld_check_button(u"{_TOGGLE_ID}"_ustr))\n'
        )

    wiring = (
        f"    {_CONTROLLER_MEMBER} = std::make_unique<sfx2::RegexSearchController>(\n"
        f"        m_xDialog.get(), *{_ENTRY_MEMBER}, *{_BUTTON_MEMBER},\n"
        f"        LINK(this, {_OWNER}, {_HANDLER}));\n"
    )
    if matcher_strategy == "legacy-literal-or-compiled-once-utl-textsearch":
        ctor_body = (
            "{\n"
            f"{wiring}"
            f"    sfx2::RegexSearchState aState = {_CONTROLLER_MEMBER}->GetState();\n"
            "    aState.Mode = sfx2::RegexSearchMode::Literal;\n"
            f"    aState.Flags.CaseInsensitive = {case_insensitive_literal};\n"
            f"    {_CONTROLLER_MEMBER}->SetState(aState);\n"
            "}\n"
        )
    else:
        ctor_body = (
            "{\n"
            f"{wiring}"
            f"    sfx2::RegexSearchState aState = {_CONTROLLER_MEMBER}->GetState();\n"
            f"    aState.Flags.CaseInsensitive = {case_insensitive_literal};\n"
            f"    {_CONTROLLER_MEMBER}->SetState(aState);\n"
            "}\n"
        )

    if matcher_strategy == "legacy-literal-or-compiled-once-utl-textsearch":
        handler_body = (
            "{\n"
            f"    const sfx2::RegexSearchState& rState = {_CONTROLLER_MEMBER}->GetState();\n"
            "    const bool bEmpty = rState.Pattern.isEmpty();\n"
            "    const bool bValid = bEmpty || sfx2::RegexSearchService::Validate(rState).IsValid;\n"
            "    const bool bLegacyCompatibleLiteral\n"
            "        = rState.Mode == sfx2::RegexSearchMode::Literal "
            "&& !rState.Flags.CaseInsensitive;\n"
            "    std::unique_ptr<utl::TextSearch> xSearch;\n"
            "    if (bValid && !bEmpty && !bLegacyCompatibleLiteral)\n"
            "        xSearch = std::make_unique<utl::TextSearch>("
            f"{_CONTROLLER_MEMBER}->GetSearchOptions());\n"
            "\n"
            "    m_xList->clear();\n"
            f"    for (const OUString& {match_subject} : maItems)\n"
            "    {\n"
            "        if (bEmpty\n"
            f"            || (bLegacyCompatibleLiteral && {match_subject}.indexOf(rState.Pattern) >= 0)\n"
            f"            || (xSearch && xSearch->searchForward({match_subject})))\n"
            f"            m_xList->append_text({match_subject});\n"
            "    }\n"
            "}\n"
        )
    elif matcher_strategy == "options-handoff-to-existing-search-engine":
        handler_body = (
            "{\n"
            "    const i18nutil::SearchOptions2 aOptions = "
            f"{_CONTROLLER_MEMBER}->GetSearchOptions();\n"
            f"    {_HANDOFF_SINK}(aOptions);\n"
            "}\n"
        )
    else:  # native-regex-option-sync
        handler_body = (
            "{\n"
            f"    const sfx2::RegexSearchState& rState = {_CONTROLLER_MEMBER}->GetState();\n"
            f"    {_TOGGLE_MEMBER}->set_active(rState.Mode == "
            "sfx2::RegexSearchMode::RegularExpression);\n"
            "}\n"
        )

    return (
        f"{includes}"
        "\n"
        f"{_OWNER}::{_OWNER}(weld::Window* pParent)\n"
        f"{ctor_init}"
        f"{ctor_body}"
        "\n"
        f"IMPL_LINK_NOARG({_OWNER}, {_HANDLER}, {arg}, void)\n"
        f"{handler_body}"
    )


def build_fixture(
    *,
    widget_kind: str,
    matcher_strategy: str,
    default_mode: str,
) -> tuple[dict, dict, dict[str, str], dict]:
    """Return (registry, coverage, contents, entry) for a valid synthetic field."""
    entry_class = "GtkEntry" if widget_kind == "entry" else "GtkComboBoxText"
    member_type = "weld::Entry" if widget_kind == "entry" else "weld::ComboBox"
    native_toggle = matcher_strategy == "native-regex-option-sync"
    engine_preserving = default_mode == "engine-preserving-current-default"

    if default_mode == "literal-case-sensitive-indexof-compatible":
        ci_literal = "false"
    elif default_mode == "literal-case-insensitive-contains-compatible":
        ci_literal = "true"
    else:  # engine-preserving; mirror the declared engine default (false here)
        ci_literal = "false"

    entry: dict = {
        "coverage_id": "fixture.search",
        "surface": "Fixture search",
        "status": "source-integrated",
        "ui_file": UI_FILE,
        "entry_id": _ENTRY_ID,
        "builder_button_id": _BUTTON_ID,
        "header_file": HEADER_FILE,
        "source_file": SOURCE_FILE,
        "owner_type": _OWNER,
        "owner_changed_handler": _HANDLER,
        "entry_member": _ENTRY_MEMBER,
        "builder_member": _BUTTON_MEMBER,
        "controller_member": _CONTROLLER_MEMBER,
        "controller_parent": "m_xDialog.get()",
        "widget_kind": widget_kind,
        "matcher_strategy": matcher_strategy,
        "default_mode": default_mode,
        "runtime_verified": False,
    }
    if matcher_strategy == "legacy-literal-or-compiled-once-utl-textsearch":
        entry["match_subject"] = "rItem"
    if matcher_strategy == "options-handoff-to-existing-search-engine":
        entry["handoff_sink"] = _HANDOFF_SINK
    if native_toggle:
        entry["native_regex_toggle"] = _TOGGLE_MEMBER
        entry["native_regex_toggle_id"] = _TOGGLE_ID
    if engine_preserving:
        entry["engine_default_case_insensitive"] = ci_literal == "true"

    registry = {
        "schema_version": 1,
        "contract": "windows-native-regex-search-integrations",
        "platform": "windows",
        "expected_integrations": 1,
        "integrations": [entry],
    }
    coverage = {
        "shipping_fields": [
            {
                "coverage_id": "fixture.search",
                "ui_file": UI_FILE,
                "widget_id": _ENTRY_ID,
                "regex_builder": "adjacent-advanced-builder",
            }
        ]
    }
    contents = {
        VALIDATOR.CONTROLLER_SOURCE: FIXTURE_CONTROLLER,
        UI_FILE: _fixture_ui(
            entry_class=entry_class, has_entry=widget_kind == "combobox",
            native_toggle=native_toggle,
        ),
        HEADER_FILE: _fixture_header(member_type=member_type, native_toggle=native_toggle),
        SOURCE_FILE: _fixture_source(
            widget_kind=widget_kind,
            matcher_strategy=matcher_strategy,
            case_insensitive_literal=ci_literal,
        ),
    }
    return registry, coverage, contents, entry


class ParameterizedContractTest(unittest.TestCase):
    """Fail-closed coverage for every parameterized branch of the checker."""

    def failures(self, registry, coverage, contents) -> list[str]:
        return VALIDATOR.violations(registry, coverage, contents)

    # -- Clean baselines: every supported combination validates with no error. --

    def test_entry_legacy_case_sensitive_fixture_is_clean(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-sensitive-indexof-compatible",
        )
        self.assertEqual([], self.failures(registry, coverage, contents))

    def test_combobox_legacy_case_insensitive_fixture_is_clean(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="combobox",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-insensitive-contains-compatible",
        )
        self.assertEqual([], self.failures(registry, coverage, contents))

    def test_options_handoff_fixture_is_clean(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="options-handoff-to-existing-search-engine",
            default_mode="engine-preserving-current-default",
        )
        self.assertEqual([], self.failures(registry, coverage, contents))

    def test_native_regex_option_sync_fixture_is_clean(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="native-regex-option-sync",
            default_mode="engine-preserving-current-default",
        )
        self.assertEqual([], self.failures(registry, coverage, contents))

    # -- widget_kind branch --------------------------------------------------

    def test_declared_combobox_rejects_gtkentry_ui(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="combobox",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-insensitive-contains-compatible",
        )
        # A GtkEntry cannot satisfy the editable-combobox widget_kind.
        contents[UI_FILE] = contents[UI_FILE].replace(
            'class="GtkComboBoxText"', 'class="GtkEntry"', 1
        )
        self.assertTrue(any(":ui-entry:" in e for e in self.failures(registry, coverage, contents)))

    def test_declared_entry_rejects_combobox_ui(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-sensitive-indexof-compatible",
        )
        contents[UI_FILE] = contents[UI_FILE].replace(
            'class="GtkEntry"', 'class="GtkComboBoxText"', 1
        )
        self.assertTrue(any(":ui-entry:" in e for e in self.failures(registry, coverage, contents)))

    def test_editable_combobox_requires_has_entry(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="combobox",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-insensitive-contains-compatible",
        )
        contents[UI_FILE] = contents[UI_FILE].replace(
            '        <property name="has-entry">True</property>\n', "", 1
        )
        self.assertTrue(
            any("has-entry True" in e for e in self.failures(registry, coverage, contents))
        )

    def test_combobox_member_type_must_match_widget_kind(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="combobox",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-insensitive-contains-compatible",
        )
        contents[HEADER_FILE] = contents[HEADER_FILE].replace(
            "std::unique_ptr<weld::ComboBox>", "std::unique_ptr<weld::Entry>", 1
        )
        self.assertTrue(
            any("weld::ComboBox" in e and "member missing" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_handler_signature_must_match_widget_kind(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="combobox",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-insensitive-contains-compatible",
        )
        # A combobox field wired through the TextWidget& handler signature is wrong.
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f"IMPL_LINK_NOARG({_OWNER}, {_HANDLER}, weld::ComboBox&, void)",
            f"IMPL_LINK_NOARG({_OWNER}, {_HANDLER}, weld::TextWidget&, void)",
            1,
        )
        self.assertTrue(
            any(":handler:signature must be" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_combobox_weld_factory_must_match_widget_kind(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="combobox",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-insensitive-contains-compatible",
        )
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f'weld_combo_box(u"{_ENTRY_ID}"_ustr)',
            f'weld_entry(u"{_ENTRY_ID}"_ustr)',
            1,
        )
        self.assertTrue(
            any("missing weld_combo_box" in e
                for e in self.failures(registry, coverage, contents))
        )

    # -- default_mode / constructor cross-validation -------------------------

    def test_case_insensitive_mode_requires_case_insensitive_true_seed(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-insensitive-contains-compatible",
        )
        # Constructor seeds CaseInsensitive = false while the declared default is
        # case-insensitive: the flag must match the mode.
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            "aState.Flags.CaseInsensitive = true;",
            "aState.Flags.CaseInsensitive = false;",
            1,
        )
        self.assertTrue(
            any("literal-default:missing aState.Flags.CaseInsensitive = true;" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_case_sensitive_mode_requires_case_insensitive_false_seed(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-sensitive-indexof-compatible",
        )
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            "aState.Flags.CaseInsensitive = false;",
            "aState.Flags.CaseInsensitive = true;",
            1,
        )
        self.assertTrue(
            any("literal-default:missing aState.Flags.CaseInsensitive = false;" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_strategy_and_default_mode_must_be_compatible(self) -> None:
        registry, coverage, contents, entry = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-sensitive-indexof-compatible",
        )
        entry["default_mode"] = "engine-preserving-current-default"
        self.assertTrue(
            any("default_mode:incompatible with matcher_strategy" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_unknown_tokens_are_rejected(self) -> None:
        for field, failure in (
            ("widget_kind", "widget_kind:unsupported kind"),
            ("matcher_strategy", "matcher_strategy:unsupported strategy"),
            ("default_mode", "default_mode:unsupported mode"),
        ):
            with self.subTest(field=field):
                registry, coverage, contents, entry = build_fixture(
                    widget_kind="entry",
                    matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
                    default_mode="literal-case-sensitive-indexof-compatible",
                )
                entry[field] = "not-a-real-token"
                self.assertTrue(
                    any(failure in e for e in self.failures(registry, coverage, contents))
                )

    def test_engine_preserving_requires_declared_case_default(self) -> None:
        registry, coverage, contents, entry = build_fixture(
            widget_kind="entry",
            matcher_strategy="options-handoff-to-existing-search-engine",
            default_mode="engine-preserving-current-default",
        )
        del entry["engine_default_case_insensitive"]
        self.assertTrue(
            any("engine_default_case_insensitive:boolean required" in e
                for e in self.failures(registry, coverage, contents))
        )

    # -- match_subject branch ------------------------------------------------

    def test_legacy_strategy_requires_declared_match_subject(self) -> None:
        registry, coverage, contents, entry = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-sensitive-indexof-compatible",
        )
        del entry["match_subject"]
        self.assertTrue(
            any("match_subject:non-empty text required" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_match_subject_must_be_the_loop_variable(self) -> None:
        registry, coverage, contents, entry = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-sensitive-indexof-compatible",
        )
        # Declare a subject that never appears as the range-for loop variable.
        entry["match_subject"] = "rGhost"
        self.assertTrue(
            any("handler-match-subject:rGhost must be the range-for loop variable" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_second_compile_site_is_rejected(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="legacy-literal-or-compiled-once-utl-textsearch",
            default_mode="literal-case-sensitive-indexof-compatible",
        )
        # A second TextSearch build (e.g. re-compiling per row) is forbidden.
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            "        if (bEmpty\n",
            "        std::unique_ptr<utl::TextSearch> xExtra = "
            f"std::make_unique<utl::TextSearch>({_CONTROLLER_MEMBER}->GetSearchOptions());\n"
            "        if (bEmpty\n",
            1,
        )
        self.assertTrue(
            any("handler-compiled-matcher:expected exactly 1" in e
                for e in self.failures(registry, coverage, contents))
        )

    # -- options-handoff strategy markers ------------------------------------

    def test_options_handoff_requires_search_options_once(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="options-handoff-to-existing-search-engine",
            default_mode="engine-preserving-current-default",
        )
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f"{_CONTROLLER_MEMBER}->GetSearchOptions()", "removedOptions()", 1
        )
        self.assertTrue(
            any("handler-search-options:expected exactly 1" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_options_handoff_requires_declared_sink(self) -> None:
        registry, coverage, contents, entry = build_fixture(
            widget_kind="entry",
            matcher_strategy="options-handoff-to-existing-search-engine",
            default_mode="engine-preserving-current-default",
        )
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f"{_HANDOFF_SINK}(aOptions);", "(void)aOptions;", 1
        )
        self.assertTrue(
            any("handler-handoff:sink" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_options_handoff_forbids_local_matching(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="options-handoff-to-existing-search-engine",
            default_mode="engine-preserving-current-default",
        )
        # Smuggling a local matcher into a hand-off surface is forbidden.
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f"    {_HANDOFF_SINK}(aOptions);\n",
            f"    {_HANDOFF_SINK}(aOptions);\n"
            "    auto xSearch = std::make_unique<utl::TextSearch>(aOptions);\n",
            1,
        )
        self.assertTrue(
            any("local matching path forbidden" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_options_handoff_requires_no_textsearch_include(self) -> None:
        # The hand-off strategy needs no unotools/textsearch include; its absence
        # in the clean fixture confirms the include is only required for legacy.
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="options-handoff-to-existing-search-engine",
            default_mode="engine-preserving-current-default",
        )
        self.assertNotIn("unotools/textsearch.hxx", contents[SOURCE_FILE])
        self.assertEqual([], self.failures(registry, coverage, contents))

    # -- native-regex-option-sync strategy markers ---------------------------

    def test_native_sync_requires_toggle_sync_marker(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="native-regex-option-sync",
            default_mode="engine-preserving-current-default",
        )
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f"{_TOGGLE_MEMBER}->set_active(rState.Mode == "
            "sfx2::RegexSearchMode::RegularExpression);",
            "// no native sync",
            1,
        )
        self.assertTrue(
            any("handler-native-regex-sync:expected exactly 1" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_native_sync_requires_toggle_widget_in_ui(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="native-regex-option-sync",
            default_mode="engine-preserving-current-default",
        )
        contents[UI_FILE] = contents[UI_FILE].replace(
            f'<object class="GtkCheckButton" id="{_TOGGLE_ID}">',
            f'<object class="GtkLabel" id="{_TOGGLE_ID}">',
            1,
        )
        self.assertTrue(
            any(":ui-native-toggle:" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_native_sync_forbids_options_handoff(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="native-regex-option-sync",
            default_mode="engine-preserving-current-default",
        )
        # A native-sync surface must not also build a second matching path.
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f"    {_TOGGLE_MEMBER}->set_active(rState.Mode == "
            "sfx2::RegexSearchMode::RegularExpression);\n",
            f"    {_TOGGLE_MEMBER}->set_active(rState.Mode == "
            "sfx2::RegexSearchMode::RegularExpression);\n"
            f"    auto o = {_CONTROLLER_MEMBER}->GetSearchOptions();\n",
            1,
        )
        self.assertTrue(
            any("handler-search-options:local matching path forbidden" in e
                for e in self.failures(registry, coverage, contents))
        )

    def test_native_sync_requires_check_button_wiring(self) -> None:
        registry, coverage, contents, _ = build_fixture(
            widget_kind="entry",
            matcher_strategy="native-regex-option-sync",
            default_mode="engine-preserving-current-default",
        )
        contents[SOURCE_FILE] = contents[SOURCE_FILE].replace(
            f'weld_check_button(u"{_TOGGLE_ID}"_ustr)',
            f'weld_toggle_button(u"{_TOGGLE_ID}"_ustr)',
            1,
        )
        self.assertTrue(
            any("missing weld_check_button" in e
                for e in self.failures(registry, coverage, contents))
        )


if __name__ == "__main__":
    unittest.main()
