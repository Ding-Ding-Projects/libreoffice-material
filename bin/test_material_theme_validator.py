#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Regression tests for the Material theme source validator."""

from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY / "bin/check-material-theme.py"
DEFINITION_PATH = (
    REPOSITORY / "vcl/uiconfig/theme_definitions/material/definition.xml"
)
RENDERER_PATH = REPOSITORY / "vcl/source/gdi/FileDefinitionWidgetDraw.cxx"
TYPOGRAPHY_SOURCE_PATH = REPOSITORY / "vcl/source/gdi/WidgetDefinition.cxx"

SPEC = importlib.util.spec_from_file_location("check_material_theme", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load validator from {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class MaterialThemeValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.definition = DEFINITION_PATH.read_text(encoding="utf-8")

    def replace_once(self, old: str, new: str) -> str:
        self.assertEqual(
            self.definition.count(old),
            1,
            f"production definition no longer has one copy of {old!r}",
        )
        return self.definition.replace(old, new, 1)

    def assert_definition_fails(self, definition: str, message: str) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "definition.xml"
            path.write_text(definition, encoding="utf-8")
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError, re.escape(message)
            ):
                VALIDATOR.validate(path)

    def test_canonical_theme_and_native_sources_pass(self) -> None:
        self.assertEqual(
            VALIDATOR.validate(DEFINITION_PATH), (2, 23, 3, 72, 74, 190)
        )
        VALIDATOR.validate_native_typography_source(
            (RENDERER_PATH, TYPOGRAPHY_SOURCE_PATH)
        )
        VALIDATOR.validate_native_style_source(
            (
                REPOSITORY / "vcl/inc/widgetdraw/WidgetDefinition.hxx",
                REPOSITORY / "vcl/source/gdi/WidgetDefinitionReader.cxx",
                RENDERER_PATH,
                REPOSITORY / "include/vcl/settings.hxx",
                REPOSITORY / "vcl/source/app/settings.cxx",
                REPOSITORY
                / "vcl/qa/cppunit/widgetdraw/FileDefinitionWidgetDrawTest.cxx",
            )
        )

    def test_style_structure_and_semantic_mapping_are_strict(self) -> None:
        face = '        <faceColor value="@surface-container"/>'
        missing_section = self.replace_once(
            "    <style>", "    <ignoredStyle>"
        ).replace("    </style>", "    </ignoredStyle>", 1)
        cases = {
            "missing section": (
                missing_section,
                "expected exactly one <style> section, found 0",
            ),
            "duplicate section": (
                self.replace_once(
                    "    </style>", "    </style>\n\n    <style/>"
                ),
                "expected exactly one <style> section, found 2",
            ),
            "section attribute": (
                self.replace_once("    <style>", '    <style mode="material">'),
                "style section must not have attributes",
            ),
            "section text": (
                self.replace_once("    <style>", "    <style>invalid"),
                "style section must not contain text",
            ),
            "unknown element": (
                self.replace_once(face, '        <mysteryColor value="@surface"/>'),
                "style has unknown element <mysteryColor>",
            ),
            "missing value": (
                self.replace_once(face, "        <faceColor/>"),
                "style <faceColor> requires exactly one value attribute",
            ),
            "extra attribute": (
                self.replace_once(
                    face,
                    '        <faceColor value="@surface-container" mode="fixed"/>',
                ),
                "style <faceColor> requires exactly one value attribute",
            ),
            "child text": (
                self.replace_once(
                    face,
                    '        <faceColor value="@surface-container">invalid</faceColor>',
                ),
                "style <faceColor> must not have content",
            ),
            "nested element": (
                self.replace_once(
                    face,
                    '        <faceColor value="@surface-container"><color/></faceColor>',
                ),
                "style <faceColor> must not have content",
            ),
            "nested processing instruction": (
                self.replace_once(
                    face,
                    '        <faceColor value="@surface-container">'
                    "<?material style?></faceColor>",
                ),
                "style <faceColor> must not have content",
            ),
            "direct processing instruction": (
                self.replace_once(
                    "    <style>", "    <style>\n        <?material style?>"
                ),
                "style has unknown element <",
            ),
            "child tail": (
                self.replace_once(face, face + "invalid"),
                "style section must not contain text",
            ),
            "duplicate element": (
                self.replace_once(face, f"{face}\n{face}"),
                "duplicate style element <faceColor>",
            ),
            "missing element": (
                self.replace_once(face, ""),
                "missing required style elements: faceColor",
            ),
            "wrong mapping": (
                self.replace_once(
                    face, '        <faceColor value="@surface"/>'
                ),
                "style <faceColor> must reference @surface-container",
            ),
            "literal value": (
                self.replace_once(face, '        <faceColor value="#FFFBFE"/>'),
                "style <faceColor> must reference @surface-container",
            ),
        }
        for name, (definition, message) in cases.items():
            with self.subTest(name=name):
                self.assert_definition_fails(definition, message)

    def test_feedback_tokens_are_scheme_specific_and_exact(self) -> None:
        expected = {
            ("light", "warning-container"): "#FFDDB3",
            ("light", "on-warning-container"): "#2A1800",
            ("light", "error-container"): "#F9DEDC",
            ("light", "on-error-container"): "#410E0B",
            ("dark", "warning-container"): "#5F4100",
            ("dark", "on-warning-container"): "#FFDDB3",
            ("dark", "error-container"): "#8C1D18",
            ("dark", "on-error-container"): "#F9DEDC",
        }
        for (scheme, name), color in expected.items():
            with self.subTest(scheme=scheme, token=name):
                line = f'        <color name="{name}" value="{color}"/>'
                definition = self.replace_once(
                    line, f'        <color name="{name}" value="#000000"/>'
                )
                self.assert_definition_fails(
                    definition,
                    f"{scheme} palette token {name!r} must be {color}, "
                    "found #000000",
                )

        light = '        <color name="warning-container" value="#FFDDB3"/>'
        dark = '        <color name="warning-container" value="#5F4100"/>'
        definition = self.definition.replace(light, "", 1).replace(dark, "", 1)
        self.assert_definition_fails(
            definition,
            "light palette is missing required feedback token 'warning-container'",
        )

    def test_list_selection_warning_and_error_contrast_is_enforced(self) -> None:
        cases = {
            "list": (
                self.replace_once(
                    '        <color name="on-surface" value="#1D1B20"/>',
                    '        <color name="on-surface" value="#FFFBFE"/>',
                ),
                "light listBoxWindowTextColor/listBoxWindowBackgroundColor "
                "contrast is only 1.00:1",
                None,
            ),
            "selection": (
                self.replace_once(
                    '        <color name="on-primary-container" value="#1D192B"/>',
                    '        <color name="on-primary-container" value="#E8DEF8"/>',
                ),
                "light listBoxWindowHighlightTextColor/"
                "listBoxWindowHighlightColor contrast is only 1.00:1",
                None,
            ),
            "warning": (
                self.replace_once(
                    '        <color name="on-warning-container" value="#2A1800"/>',
                    '        <color name="on-warning-container" value="#FFDDB3"/>',
                ),
                "light warningTextColor/warningColor contrast is only 1.00:1",
                ("on-warning-container", "#FFDDB3"),
            ),
            "error": (
                self.replace_once(
                    '        <color name="on-error-container" value="#410E0B"/>',
                    '        <color name="on-error-container" value="#F9DEDC"/>',
                ),
                "light errorTextColor/errorColor contrast is only 1.00:1",
                ("on-error-container", "#F9DEDC"),
            ),
        }
        for name, (definition, message, feedback_override) in cases.items():
            with self.subTest(name=name):
                feedback_colors = {
                    scheme: dict(colors)
                    for scheme, colors in VALIDATOR.REQUIRED_FEEDBACK_COLORS.items()
                }
                if feedback_override is not None:
                    token, color = feedback_override
                    feedback_colors["light"][token] = color
                with mock.patch.object(
                    VALIDATOR, "REQUIRED_FEEDBACK_COLORS", feedback_colors
                ):
                    self.assert_definition_fails(definition, message)

    def test_typography_structure_is_strict(self) -> None:
        body = '        <role name="body" scale="100" weight="preserve"/>'
        label = '        <role name="label" scale="100" weight="medium"/>'
        cases = {
            "duplicate role": (
                self.replace_once(body, f"{body}\n{body}"),
                "duplicate typography role 'body'",
            ),
            "duplicate section": (
                self.replace_once(
                    "    </typography>", "    </typography>\n\n    <typography/>"
                ),
                "expected exactly one <typography> section, found 2",
            ),
            "missing role": (
                self.replace_once(label, ""),
                "missing typography roles: label",
            ),
            "font family": (
                self.replace_once(body, body[:-2] + ' family="Inter"/>'),
                "typography role has unknown attributes: family",
            ),
            "unknown role": (
                self.replace_once('name="body"', 'name="caption"'),
                "unknown typography role 'caption'",
            ),
            "unknown element": (
                self.replace_once(body, "        <font/>"),
                "typography has unknown element <font>",
            ),
            "nested element": (
                self.replace_once(body, body[:-2] + "><font/></role>"),
                "typography role 'body' must not have content",
            ),
            "section text": (
                self.replace_once("    <typography>", "    <typography>invalid"),
                "typography section must not contain text",
            ),
            "role text": (
                self.replace_once(body, body[:-2] + ">invalid</role>"),
                "typography role 'body' must not have content",
            ),
            "role processing instruction": (
                self.replace_once(
                    body, body[:-2] + "><?material role?></role>"
                ),
                "typography role 'body' must not have content",
            ),
            "processing instruction": (
                self.replace_once(
                    "    <typography>",
                    "    <typography>\n        <?material typography?>",
                ),
                "typography has unknown element",
            ),
        }
        for name, (definition, message) in cases.items():
            with self.subTest(name=name):
                self.assert_definition_fails(definition, message)

    def test_typography_values_are_bounded_and_canonical(self) -> None:
        cases = {
            "below minimum": (
                self.replace_once('name="body" scale="100"', 'name="body" scale="099"'),
                "typography scale for 'body' must be between 100 and 200",
            ),
            "above maximum": (
                self.replace_once('name="body" scale="100"', 'name="body" scale="201"'),
                "typography scale for 'body' must be between 100 and 200",
            ),
            "bad weight": (
                self.replace_once('weight="preserve"', 'weight="heavy"'),
                "invalid typography weight 'heavy' for 'body'",
            ),
        }
        for name, (definition, message) in cases.items():
            with self.subTest(name=name):
                self.assert_definition_fails(definition, message)

    def test_palette_rejects_text_and_processing_instructions(self) -> None:
        color = '        <color name="primary" value="#6750A4"/>'
        cases = {
            "direct text": (
                self.replace_once("    <palette>", "    <palette>invalid"),
                "palette 'light' must not contain text",
            ),
            "color tail": (
                self.replace_once(color, color + "invalid"),
                "palette 'light' must not contain text",
            ),
            "processing instruction": (
                self.replace_once(
                    "    <palette>", "    <palette>\n        <?material palette?>"
                ),
                "palette 'light' has unknown element",
            ),
            "color extra attribute": (
                self.replace_once(
                    color,
                    '        <color name="primary" value="#6750A4" mode="fixed"/>',
                ),
                "palette 'light' <color> requires exactly name and value attributes",
            ),
            "nested color element": (
                self.replace_once(
                    color,
                    '        <color name="primary" value="#6750A4"><extra/></color>',
                ),
                "palette 'light' color 'primary' must not have content",
            ),
            "nested color processing instruction": (
                self.replace_once(
                    color,
                    '        <color name="primary" value="#6750A4">'
                    "<?material color?></color>",
                ),
                "palette 'light' color 'primary' must not have content",
            ),
            "root processing instruction": (
                self.replace_once("<widgets>", "<widgets>\n    <?material root?>"),
                "Material definition must not contain processing instructions",
            ),
            "settings processing instruction": (
                self.replace_once(
                    "    <settings>",
                    "    <settings>\n        <?material settings?>",
                ),
                "Material definition must not contain processing instructions",
            ),
        }
        for name, (definition, message) in cases.items():
            with self.subTest(name=name):
                self.assert_definition_fails(definition, message)

    def test_settings_section_is_unique_and_cannot_set_a_default_font(self) -> None:
        duplicate = self.replace_once(
            "    </settings>", "    </settings>\n\n    <settings/>"
        )
        self.assert_definition_fails(
            duplicate, "expected exactly one <settings> section, found 2"
        )

        default_font = self.replace_once(
            "    <settings>",
            '    <settings>\n        <defaultFontSize value="10"/>',
        )
        self.assert_definition_fails(
            default_font,
            "Material typography must not replace the native font with defaultFontSize",
        )

    def test_required_native_source_patterns_cannot_hide_in_comments(self) -> None:
        comments = "\n".join(
            (
                "// mpTypography->apply(aStyleSet, aNativeStyleSet);",
                "// moNativeStyle;",
                "// applyLegacyMinimumFontHeight(aStyleSet, aNativeStyleSet, 10);",
                "// WidgetDefinitionTypography::apply() {}",
                "// rTarget.SetAppFont();",
                "// rTarget.SetTitleFont();",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            renderer = Path(directory) / "renderer.cxx"
            typography = Path(directory) / "typography.cxx"
            renderer.write_text(comments, encoding="utf-8")
            typography.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError,
                "native typography source is missing pattern",
            ):
                VALIDATOR.validate_native_typography_source((renderer, typography))

    def test_required_native_style_patterns_cannot_hide_in_comments(self) -> None:
        comments = "\n".join(
            (
                "// std::optional<Color> moAccentColor;",
                '// { "accentColor", &rWidgetDefinition.mpStyle->moAccentColor },',
                "// if (pDefinitionStyle->moAccentColor)",
                "//     aStyleSet.SetAccentColor(*pDefinitionStyle->moAccentColor);",
                "// StyleSettings::SetWarningTextColor(const Color&);",
                "// StyleSettings::SetErrorColor(const Color&);",
                "// StyleSettings::SetErrorTextColor(const Color&);",
                "// pGraphics->UpdateSettings(aSettings);",
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "style-source.cxx"
            source.write_text(comments, encoding="utf-8")
            with self.assertRaisesRegex(
                VALIDATOR.ValidationError,
                "native style source is missing pattern",
            ):
                VALIDATOR.validate_native_style_source((source,))

    def test_native_source_guard_rejects_fixed_identity_setters(self) -> None:
        valid_source = "\n".join(
            (
                "mpTypography->apply(aStyleSet, aNativeStyleSet);",
                "moNativeStyle;",
                "applyLegacyMinimumFontHeight(aStyleSet, aNativeStyleSet, 10);",
                "WidgetDefinitionTypography::apply() {}",
                "rTarget.SetAppFont();",
                "rTarget.SetTitleFont();",
            )
        )
        forbidden_overrides = (
            ".SetIconFont(",
            ".SetFamilyName(",
            ".SetFamily(",
            ".SetStyleName(",
            ".SetCharSet(",
            ".SetLanguage(",
            ".SetPitch(",
            ".SetOrientation(",
            ".SetFontWidth(",
        )
        for forbidden in forbidden_overrides:
            with self.subTest(forbidden=forbidden):
                with tempfile.TemporaryDirectory() as directory:
                    renderer = Path(directory) / "renderer.cxx"
                    typography = Path(directory) / "typography.cxx"
                    renderer.write_text(
                        valid_source + f"\nrTarget{forbidden}value);\n",
                        encoding="utf-8",
                    )
                    typography.write_text("", encoding="utf-8")
                    with self.assertRaisesRegex(
                        VALIDATOR.ValidationError,
                        re.escape(
                            "native typography source contains forbidden override "
                            f"{forbidden!r}"
                        ),
                    ):
                        VALIDATOR.validate_native_typography_source(
                            (renderer, typography)
                        )


if __name__ == "__main__":
    unittest.main()
