#!/usr/bin/env python3
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Validate the semantic palette and required VCL Material widget coverage."""

from __future__ import annotations

import argparse
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


TOKEN_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
TOKEN_REFERENCE = re.compile(r"^@([a-z][a-z0-9-]*)$")
REQUIRED_SCHEMES = {"light", "dark"}

REQUIRED_PARTS = {
    "pushbutton": {"Entire", "Focus"},
    "radiobutton": {"Entire", "Focus"},
    "checkbox": {"Entire", "Focus"},
    "combobox": {"Entire", "SubEdit", "ButtonDown", "Focus"},
    "editbox": {"Entire"},
    "editboxnoborder": {"Entire"},
    "multilineeditbox": {"Entire"},
    "listbox": {"Entire", "ListboxWindow", "SubEdit", "ButtonDown", "Focus"},
    "spinbox": {"Entire", "SubEdit", "ButtonDown", "ButtonUp", "Focus"},
    "spinbuttons": {"ButtonDown", "ButtonUp", "ButtonLeft", "ButtonRight"},
    "scrollbar": {
        "Entire",
        "ThumbHorz",
        "ThumbVert",
        "ButtonUp",
        "ButtonDown",
        "ButtonLeft",
        "ButtonRight",
        "TrackHorzLeft",
        "TrackHorzRight",
        "TrackVertUpper",
        "TrackVertLower",
    },
    "slider": {
        "Button",
        "TrackHorzLeft",
        "TrackHorzRight",
        "TrackVertUpper",
        "TrackVertLower",
    },
    "fixedline": {"SeparatorHorz", "SeparatorVert"},
    "progress": {"Entire"},
    "tabitem": {"Entire", "MenuItem"},
    "tabheader": {"Entire"},
    "tabpane": {"Entire"},
    "tabbody": {"Entire"},
    "windowbackground": {"Entire", "BackgroundWindow", "BackgroundDialog"},
    "toolbar": {
        "Entire",
        "DrawBackgroundHorz",
        "DrawBackgroundVert",
        "ThumbHorz",
        "ThumbVert",
        "SeparatorHorz",
        "SeparatorVert",
        "Button",
    },
    "listnode": {"Entire"},
    "listheader": {"Button", "Arrow"},
    "menubar": {"Entire", "MenuItem"},
    "menupopup": {
        "Entire",
        "MenuItem",
        "MenuItemCheckMark",
        "MenuItemRadioMark",
        "Separator",
        "SubmenuArrow",
    },
    "tooltip": {"Entire"},
}


class ValidationError(Exception):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def parse_color(value: str) -> tuple[int, int, int]:
    if not HEX_COLOR.fullmatch(value):
        fail(f"invalid RGB color {value!r}")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def linear_component(component: int) -> float:
    value = component / 255.0
    return value / 12.92 if value <= 0.04045 else math.pow((value + 0.055) / 1.055, 2.4)


def luminance(color: tuple[int, int, int]) -> float:
    red, green, blue = (linear_component(component) for component in color)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first: tuple[int, int, int], second: tuple[int, int, int]) -> float:
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def find_part(root: ET.Element, control_name: str, part_name: str) -> ET.Element:
    control = root.find(control_name)
    if control is None:
        fail(f"missing control {control_name}")
    for part in control.findall("part"):
        if part.get("value") == part_name:
            return part
    fail(f"missing {control_name}/{part_name}")


def has_state(part: ET.Element, **attributes: str) -> bool:
    return any(all(state.get(name) == value for name, value in attributes.items())
               for state in part.findall("state"))


def validate_interaction_states(part: ET.Element, label: str) -> None:
    states = part.findall("state")
    expected = {
        "normal": lambda state: state.get("enabled") == "true"
        and state.get("rollover") is None
        and state.get("pressed") is None,
        "rollover": lambda state: state.get("enabled") == "true"
        and state.get("rollover") == "true"
        and state.get("pressed") is None,
        "pressed": lambda state: state.get("enabled") == "true"
        and state.get("pressed") == "true"
        and state.get("rollover") is None,
        "disabled": lambda state: state.get("enabled") == "false"
        and state.get("rollover") is None
        and state.get("pressed") is None,
    }
    for state_name, matches in expected.items():
        matching = [state for state in states if matches(state)]
        if not matching:
            fail(f"{label} missing {state_name} state")
        if any(len(state) == 0 for state in matching):
            fail(f"{label} {state_name} state has no drawing action")


def read_palettes(
    root: ET.Element,
) -> tuple[dict[str, dict[str, tuple[int, int, int]]], set[ET.Element]]:
    palettes: dict[str, dict[str, tuple[int, int, int]]] = {}
    palette_elements: set[ET.Element] = set()

    for palette in root.findall("palette"):
        unknown_attributes = sorted(set(palette.attrib) - {"scheme"})
        if unknown_attributes:
            fail(f"palette has unknown attributes: {', '.join(unknown_attributes)}")

        scheme_attribute = palette.get("scheme")
        scheme = "light" if scheme_attribute is None else scheme_attribute
        if not TOKEN_NAME.fullmatch(scheme):
            fail(f"invalid palette scheme {scheme!r}")
        if scheme in palettes:
            fail(f"duplicate palette scheme {scheme!r}")

        tokens: dict[str, tuple[int, int, int]] = {}
        for element in palette:
            if element.tag != "color":
                fail(f"palette {scheme!r} has unknown element <{element.tag}>")
            palette_elements.add(element)
            name = element.get("name", "")
            value = element.get("value", "")
            if not TOKEN_NAME.fullmatch(name):
                fail(f"invalid token name {name!r} in {scheme!r} palette")
            if name in tokens:
                fail(f"duplicate token {name!r} in {scheme!r} palette")
            tokens[name] = parse_color(value)
        if not tokens:
            fail(f"palette {scheme!r} is empty")
        palettes[scheme] = tokens

    if not palettes:
        fail("missing semantic <palette>")
    missing_schemes = sorted(REQUIRED_SCHEMES - palettes.keys())
    if missing_schemes:
        fail(f"missing palette schemes: {', '.join(missing_schemes)}")
    unexpected_schemes = sorted(palettes.keys() - REQUIRED_SCHEMES)
    if unexpected_schemes:
        fail(f"unexpected palette schemes: {', '.join(unexpected_schemes)}")

    light_tokens = set(palettes["light"])
    for scheme, tokens in palettes.items():
        missing_tokens = sorted(light_tokens - tokens.keys())
        extra_tokens = sorted(tokens.keys() - light_tokens)
        if missing_tokens or extra_tokens:
            details = []
            if missing_tokens:
                details.append(f"missing {', '.join(missing_tokens)}")
            if extra_tokens:
                details.append(f"extra {', '.join(extra_tokens)}")
            fail(f"palette {scheme!r} token mismatch: {'; '.join(details)}")

    return palettes, palette_elements


def validate(path: Path) -> tuple[int, int, int, int]:
    root = ET.parse(path).getroot()
    if root.tag != "widgets":
        fail("root element must be <widgets>")

    palettes, palette_elements = read_palettes(root)
    token_names = set(palettes["light"])

    references: set[str] = set()
    style = root.find("style")
    if style is None:
        fail("missing <style>")

    style_references: dict[str, str] = {}
    for element in style:
        value = element.get("value", "")
        match = TOKEN_REFERENCE.fullmatch(value)
        if match is None:
            fail(f"style {element.tag} must reference a semantic token")
        name = match.group(1)
        if name not in token_names:
            fail(f"style {element.tag} references unknown token {name!r}")
        references.add(name)
        style_references[element.tag] = name

    for element in root.iter():
        if element in palette_elements:
            continue
        for attribute in ("stroke", "fill"):
            value = element.get(attribute)
            if value is None:
                continue
            match = TOKEN_REFERENCE.fullmatch(value)
            if match is None:
                fail(f"{element.tag}/@{attribute} must reference a semantic token")
            name = match.group(1)
            if name not in token_names:
                fail(f"{element.tag}/@{attribute} references unknown token {name!r}")
            references.add(name)

    unused = sorted(token_names - references)
    if unused:
        fail(f"unused semantic tokens: {', '.join(unused)}")

    for control_name, required_parts in REQUIRED_PARTS.items():
        control = root.find(control_name)
        if control is None:
            fail(f"missing control {control_name}")
        actual_parts = {part.get("value", "") for part in control.findall("part")}
        missing_parts = sorted(required_parts - actual_parts)
        if missing_parts:
            fail(f"{control_name} missing parts: {', '.join(missing_parts)}")

    checkbox = find_part(root, "checkbox", "Entire")
    for enabled in ("true", "false"):
        for value in ("false", "true", "mixed"):
            if not has_state(checkbox, enabled=enabled, **{"button-value": value}):
                fail(f"checkbox missing enabled={enabled}, button-value={value}")

    radio = find_part(root, "radiobutton", "Entire")
    for enabled in ("true", "false"):
        for value in ("false", "true"):
            if not has_state(radio, enabled=enabled, **{"button-value": value}):
                fail(f"radiobutton missing enabled={enabled}, button-value={value}")

    tab = find_part(root, "tabitem", "Entire")
    if not has_state(tab, enabled="true", selected="true", rollover="true"):
        fail("tabitem missing combined selected+rollover state")
    if not has_state(tab, enabled="true", selected="true", focused="true"):
        fail("tabitem missing combined selected+focused state")
    tab_menu_item = find_part(root, "tabitem", "MenuItem")
    if not has_state(tab_menu_item, enabled="true", selected="true", focused="true"):
        fail("tabitem/MenuItem missing combined selected+focused state")

    toolbar_button = find_part(root, "toolbar", "Button")
    if not has_state(toolbar_button, enabled="true", **{"button-value": "true"}):
        fail("toolbar button missing checked state")
    if not has_state(
        toolbar_button, enabled="true", pressed="true", **{"button-value": "true"}
    ):
        fail("toolbar button missing combined checked+pressed state")
    if not has_state(toolbar_button, enabled="true", focused="true"):
        fail("toolbar button missing focused state")

    slider_button = find_part(root, "slider", "Button")
    if not has_state(slider_button, enabled="true", focused="true"):
        fail("slider thumb missing focused state")
    for part_name in ("TrackHorzLeft", "TrackHorzRight", "TrackVertUpper", "TrackVertLower"):
        if not has_state(find_part(root, "slider", part_name), enabled="false"):
            fail(f"slider/{part_name} missing disabled state")

    for part_name in ("ButtonDown", "ButtonUp"):
        validate_interaction_states(
            find_part(root, "spinbox", part_name), f"spinbox/{part_name}"
        )
    for part_name in ("ButtonDown", "ButtonUp", "ButtonLeft", "ButtonRight"):
        validate_interaction_states(
            find_part(root, "spinbuttons", part_name), f"spinbuttons/{part_name}"
        )

    contrast_pairs = (
        ("windowTextColor", "windowColor"),
        ("fieldTextColor", "fieldColor"),
        ("menuTextColor", "menuColor"),
        ("highlightTextColor", "highlightColor"),
        ("helpTextColor", "helpColor"),
    )
    for scheme, tokens in palettes.items():
        style_colors = {
            style_name: tokens[token_name]
            for style_name, token_name in style_references.items()
        }
        for foreground, background in contrast_pairs:
            ratio = contrast(style_colors[foreground], style_colors[background])
            if ratio < 4.5:
                fail(
                    f"{scheme} {foreground}/{background} contrast is only "
                    f"{ratio:.2f}:1"
                )
        for foreground, background in (
            ("on-primary", "primary"),
            ("on-primary-container", "primary-container"),
            ("on-primary-container", "primary-hover"),
            ("on-primary-container", "primary-pressed"),
            ("on-surface", "primary-hover"),
            ("on-surface", "primary-pressed"),
        ):
            ratio = contrast(tokens[foreground], tokens[background])
            if ratio < 4.5:
                fail(
                    f"{scheme} {foreground}/{background} contrast is only "
                    f"{ratio:.2f}:1"
                )
        disabled_ratio = contrast(tokens["outline"], tokens["disabled-container"])
        if disabled_ratio < 3.0:
            fail(
                f"{scheme} outline/disabled-container contrast is only "
                f"{disabled_ratio:.2f}:1"
            )

    part_count = sum(len(control.findall("part")) for control in root
                     if control.tag not in {"palette", "style", "settings"})
    state_count = sum(1 for _ in root.iter("state"))
    return len(palettes), len(token_names), part_count, state_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "definition",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "vcl/uiconfig/theme_definitions/material/definition.xml",
    )
    args = parser.parse_args()
    try:
        scheme_count, token_count, part_count, state_count = validate(args.definition)
    except (ET.ParseError, OSError, ValidationError) as error:
        print(f"{args.definition}: {error}", file=sys.stderr)
        return 1
    print(
        f"Material theme OK: {scheme_count} schemes, {token_count} tokens each, "
        f"{part_count} parts, {state_count} states"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
