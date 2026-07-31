#!/usr/bin/env python3
"""Generate deterministic Material branding bitmaps for Windows Installer.

The MSI UI is OS-owned and supports only classic bitmap controls. These assets
therefore carry the project's Material token palette and geometry without
replacing, faking, or intercepting Windows Installer dialogs.
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence


REPOSITORY = Path(__file__).resolve().parents[1]
DEFINITION = Path("vcl/uiconfig/theme_definitions/material/definition.xml")
OUTPUT_DIRECTORY = Path("instsetoo_native/inc_common/windows/msi_templates/Binary")

Color = tuple[int, int, int]


class GenerationError(RuntimeError):
    pass


def _parse_color(value: str) -> Color:
    if not value.startswith("#") or len(value) != 7:
        raise GenerationError(f"unsupported Material color {value!r}")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]


def _light_palette(repo: Path) -> dict[str, Color]:
    root = ET.parse(repo / DEFINITION).getroot()
    palette = next(
        (item for item in root.findall("palette") if not item.get("scheme")),
        None,
    )
    if palette is None:
        raise GenerationError("Material light palette is missing")
    colors = {
        item.get("name", ""): _parse_color(item.get("value", ""))
        for item in palette.findall("color")
        if item.get("name")
    }
    required = {
        "surface",
        "surface-container",
        "surface-container-low",
        "primary",
        "primary-container",
        "on-primary",
        "on-primary-container",
        "outline-variant",
    }
    missing = sorted(required - colors.keys())
    if missing:
        raise GenerationError(f"Material palette lacks {missing}")
    return colors


class Canvas:
    def __init__(self, width: int, height: int, color: Color):
        self.width = width
        self.height = height
        self.pixels = bytearray(color * (width * height))

    def pixel(self, x: int, y: int, color: Color, alpha: int = 255) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        offset = (y * self.width + x) * 3
        if alpha >= 255:
            self.pixels[offset : offset + 3] = bytes(color)
            return
        inverse = 255 - alpha
        for channel, value in enumerate(color):
            current = self.pixels[offset + channel]
            self.pixels[offset + channel] = (value * alpha + current * inverse + 127) // 255

    def rectangle(self, x0: int, y0: int, x1: int, y1: int, color: Color) -> None:
        for y in range(max(0, y0), min(self.height, y1)):
            for x in range(max(0, x0), min(self.width, x1)):
                self.pixel(x, y, color)

    def rounded_rectangle(
        self, x0: int, y0: int, x1: int, y1: int, radius: int, color: Color
    ) -> None:
        radius = max(0, min(radius, (x1 - x0) // 2, (y1 - y0) // 2))
        for y in range(max(0, y0), min(self.height, y1)):
            for x in range(max(0, x0), min(self.width, x1)):
                nearest_x = min(max(x, x0 + radius), x1 - radius - 1)
                nearest_y = min(max(y, y0 + radius), y1 - radius - 1)
                dx = x - nearest_x
                dy = y - nearest_y
                if dx * dx + dy * dy <= radius * radius:
                    self.pixel(x, y, color)

    def circle(self, center_x: int, center_y: int, radius: int, color: Color) -> None:
        radius_squared = radius * radius
        for y in range(center_y - radius, center_y + radius + 1):
            for x in range(center_x - radius, center_x + radius + 1):
                if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius_squared:
                    self.pixel(x, y, color)

    def polygon(self, points: Sequence[tuple[int, int]], color: Color) -> None:
        if len(points) < 3:
            return
        minimum_y = max(0, min(point[1] for point in points))
        maximum_y = min(self.height - 1, max(point[1] for point in points))
        for y in range(minimum_y, maximum_y + 1):
            intersections: list[float] = []
            for index, first in enumerate(points):
                second = points[(index + 1) % len(points)]
                if first[1] == second[1]:
                    continue
                low, high = sorted((first[1], second[1]))
                if not (low <= y < high):
                    continue
                ratio = (y - first[1]) / (second[1] - first[1])
                intersections.append(first[0] + ratio * (second[0] - first[0]))
            intersections.sort()
            for start, end in zip(intersections[0::2], intersections[1::2]):
                for x in range(max(0, math.ceil(start)), min(self.width, math.floor(end) + 1)):
                    self.pixel(x, y, color)

    def to_bmp(self) -> bytes:
        row_bytes = self.width * 3
        padding = (4 - row_bytes % 4) % 4
        image_size = (row_bytes + padding) * self.height
        header_size = 14 + 40
        file_header = struct.pack("<2sIHHI", b"BM", header_size + image_size, 0, 0, header_size)
        dib_header = struct.pack(
            "<IIIHHIIIIII",
            40,
            self.width,
            self.height,
            1,
            24,
            0,
            image_size,
            3780,
            3780,
            0,
            0,
        )
        rows: list[bytes] = []
        for y in range(self.height - 1, -1, -1):
            row = bytearray()
            for x in range(self.width):
                offset = (y * self.width + x) * 3
                red, green, blue = self.pixels[offset : offset + 3]
                row.extend((blue, green, red))
            row.extend(b"\x00" * padding)
            rows.append(bytes(row))
        return file_header + dib_header + b"".join(rows)


def _document_mark(
    canvas: Canvas,
    x: int,
    y: int,
    width: int,
    height: int,
    colors: dict[str, Color],
) -> None:
    canvas.rounded_rectangle(x, y, x + width, y + height, 10, colors["surface"])
    fold = max(12, width // 4)
    canvas.polygon(
        [(x + width - fold, y), (x + width, y + fold), (x + width - fold, y + fold)],
        colors["primary-container"],
    )
    line_x = x + max(12, width // 7)
    line_width = max(20, width - (line_x - x) - 14)
    canvas.rounded_rectangle(
        line_x,
        y + height // 3,
        line_x + line_width,
        y + height // 3 + 7,
        3,
        colors["primary"],
    )
    canvas.rounded_rectangle(
        line_x,
        y + height // 3 + 18,
        line_x + int(line_width * 0.78),
        y + height // 3 + 25,
        3,
        colors["outline-variant"],
    )
    canvas.rounded_rectangle(
        line_x,
        y + height // 3 + 36,
        line_x + int(line_width * 0.56),
        y + height // 3 + 43,
        3,
        colors["outline-variant"],
    )


def _banner(colors: dict[str, Color]) -> bytes:
    canvas = Canvas(632, 57, colors["surface"])
    canvas.rectangle(0, 0, 10, 57, colors["primary"])
    canvas.circle(535, 11, 55, colors["primary-container"])
    canvas.circle(604, 50, 42, colors["surface-container-low"])
    canvas.rounded_rectangle(27, 17, 250, 25, 4, colors["primary"])
    canvas.rounded_rectangle(27, 33, 185, 40, 3, colors["outline-variant"])
    _document_mark(canvas, 561, 7, 43, 45, colors)
    return canvas.to_bmp()


def _side_image(colors: dict[str, Color]) -> bytes:
    canvas = Canvas(162, 312, colors["surface-container"])
    canvas.circle(22, 26, 62, colors["primary-container"])
    canvas.circle(150, 244, 70, colors["surface-container-low"])
    canvas.rounded_rectangle(18, 26, 144, 272, 24, colors["primary"])
    canvas.circle(126, 52, 22, colors["on-primary-container"])
    _document_mark(canvas, 38, 76, 86, 130, colors)
    canvas.rounded_rectangle(40, 232, 122, 243, 5, colors["on-primary"])
    canvas.rounded_rectangle(55, 252, 107, 260, 4, colors["primary-container"])
    return canvas.to_bmp()


def _wide_image(colors: dict[str, Color]) -> bytes:
    canvas = Canvas(493, 312, colors["surface"])
    canvas.rounded_rectangle(0, 0, 178, 312, 0, colors["primary"])
    canvas.circle(36, 40, 84, colors["primary-container"])
    canvas.circle(460, 275, 92, colors["surface-container-low"])
    _document_mark(canvas, 46, 66, 92, 142, colors)
    canvas.rounded_rectangle(214, 64, 447, 82, 9, colors["primary"])
    canvas.rounded_rectangle(214, 102, 408, 114, 6, colors["outline-variant"])
    canvas.rounded_rectangle(214, 130, 378, 142, 6, colors["outline-variant"])
    canvas.rounded_rectangle(214, 186, 360, 226, 20, colors["primary-container"])
    canvas.rounded_rectangle(237, 202, 337, 211, 4, colors["on-primary-container"])
    return canvas.to_bmp()


def generated_assets(repo: Path = REPOSITORY) -> dict[str, bytes]:
    colors = _light_palette(repo)
    return {
        "Banner.bmp": _banner(colors),
        "Image.bmp": _side_image(colors),
        "Image_2.bmp": _wide_image(colors),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPOSITORY)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo = args.repo_root.resolve()
    try:
        assets = generated_assets(repo)
        output = repo / OUTPUT_DIRECTORY
        stale: list[str] = []
        for name, payload in assets.items():
            path = output / name
            if args.check:
                if not path.is_file() or path.read_bytes() != payload:
                    stale.append(name)
            else:
                output.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
        if stale:
            raise GenerationError(f"stale Material MSI branding assets: {', '.join(stale)}")
    except (OSError, ET.ParseError, GenerationError) as error:
        print(f"Material MSI branding generation failed: {error}", file=sys.stderr)
        return 1
    verb = "verified" if args.check else "generated"
    print(
        f"Material MSI branding {verb}: Banner.bmp 632x57, Image.bmp 162x312, "
        "Image_2.bmp 493x312 (deterministic 24-bit BMP)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
