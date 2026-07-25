#!/usr/bin/env python3
#
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

"""Sanity tests for bin/check-ui-a11y-fatals.py.

Run with:  py -3 bin/test_check_ui_a11y_fatals.py

These tests avoid a full-tree gla11y sweep (which takes minutes); they cover
the cheap, fragile-if-broken parts: module enumeration is non-empty and the
gla11y invocation actually catches a deliberately broken .ui file for one
small module (vcl).
"""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRCDIR = os.path.abspath(os.path.join(HERE, os.pardir))


def _load_checker():
    path = os.path.join(HERE, "check-ui-a11y-fatals.py")
    spec = importlib.util.spec_from_file_location("check_ui_a11y_fatals", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enumeration_non_empty(chk):
    modules = chk.enumerate_modules()
    assert modules, "no UIConfig modules enumerated"
    # A few well-known modules must be present with .ui files.
    for expected in ("vcl", "cui", "modules/swriter"):
        assert expected in modules, "missing module %s" % expected
        assert modules[expected], "module %s enumerated zero .ui files" % expected
    total = sum(len(v) for v in modules.values())
    assert total > 500, "suspiciously few .ui files enumerated: %d" % total
    print("ok: enumeration -> %d modules, %d .ui files" % (len(modules), total))


def test_broken_ui_is_caught(chk):
    # Build a minimal valid .ui and a broken one (one-sided label-for relation).
    broken = """<?xml version="1.0" encoding="UTF-8"?>
<interface domain="vcl">
  <object class="GtkBox" id="box">
    <child>
      <object class="GtkLabel" id="label">
        <accessibility>
          <relation type="label-for" target="entry"/>
        </accessibility>
      </object>
    </child>
    <child>
      <object class="GtkEntry" id="entry"/>
    </child>
  </object>
</interface>
"""
    # Place the temp .ui inside SRCDIR so the -P prefix strip behaves as in
    # the real run, and pass it as a repo-relative path.
    fd, abspath = tempfile.mkstemp(suffix=".ui", dir=SRCDIR, prefix="a11ytest_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(broken)
        rel = os.path.relpath(abspath, SRCDIR).replace(os.sep, "/")
        # Use vcl's real suppr file; the temp file has no entries there, so the
        # one-sided relation must surface as a new fatal.
        ok, count, output = chk.run_module("vcl", [rel])
        assert not ok, "broken .ui was NOT caught (ok=True)\n%s" % output
        assert count >= 1, "expected >=1 new fatal, got %d\n%s" % (count, output)
        assert "label-for" in output, "unexpected gla11y output:\n%s" % output
        print("ok: broken .ui caught (count=%d)" % count)
    finally:
        os.remove(abspath)


def main():
    chk = _load_checker()
    test_enumeration_non_empty(chk)
    test_broken_ui_is_caught(chk)
    print("\nALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
