#!/usr/bin/env python3
# -*- tab-width: 4; indent-tabs-mode: nil; py-indent-offset: 4 -*-
#
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Emit deterministic dimensions and basic nonblank statistics for one PNG."""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageStat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    args = parser.parse_args()

    raw = args.image.read_bytes()
    with Image.open(args.image) as image:
        image.verify()
    with Image.open(args.image) as image:
        rgb = image.convert("RGB")
        extrema = [list(pair) for pair in rgb.getextrema()]
        stat = ImageStat.Stat(rgb)
        width, height = rgb.size
        payload = {
            "path": str(args.image.resolve()),
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "width": width,
            "height": height,
            "mode": "RGB",
            "channel_extrema": extrema,
            "channel_mean": [round(value, 6) for value in stat.mean],
            "channel_stddev": [round(value, 6) for value in stat.stddev],
            "nonblank": any(low != high for low, high in extrema)
            and any(value >= 1.0 for value in stat.stddev),
        }
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["nonblank"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
