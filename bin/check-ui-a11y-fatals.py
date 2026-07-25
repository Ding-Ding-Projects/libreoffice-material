#!/usr/bin/env python3
#
# This file is part of the LibreOffice project.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

"""Build-free gla11y accessibility FATAL gate.

The Windows MSI build runs the ``gla11y`` accessibility checker over every
UIConfig module's ``.ui`` files (solenv/gbuild/UIConfig.mk).  A new
accessibility FATAL there aborts the ~3h build at its a11y stage.  This script
reproduces that exact gla11y invocation locally so the same failure is caught
in seconds -- before push and in the fast CI legs -- without a full build.

Recipe reproduced verbatim from solenv/gbuild/UIConfig.mk:

    py -3 bin/gla11y \\
        -P <SRCDIR>/ \\
        -f solenv/sanitizers/ui/<module>.false      (only if it exists) \\
        -s solenv/sanitizers/ui/<module>.suppr      (only if it exists) \\
        --widgets-suffixignored +ValueSet,HBox,VBox,ToolBox,Preview,PreviewWin,PreviewWindow,PrevWindow \\
        --widgets-button +svtlo-ManagedMenuButton \\
        --fatal-all \\
        --not-fatal-type duplicate-mnemonic \\
        --not-fatal-type labelled-by-and-mnemonic \\
        --not-fatal-type orphan-label \\
        <uifiles...>

The ``-P <SRCDIR>/`` prefix flag and repo-relative ``.ui`` paths are essential:
that is how gla11y makes printed file names match the repo-relative entries in
the suppression files.  With absolute paths (and no matching prefix strip) the
suppressions silently fail to match and dozens of phantom FATALs appear.

The module -> ``.ui``-files mapping is parsed from the authoritative
``*/UIConfig_*.mk`` files (the ``gb_UIConfig_add_uifiles`` entries), not by
globbing directories.

Exit codes:
    0  all modules clean (no new errors / no new fatals)
    1  at least one module reported new gla11y errors or fatals
    2  usage / internal error
"""

import argparse
import os
import re
import subprocess
import sys

SRCDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
GLA11Y = os.path.join(SRCDIR, "bin", "gla11y")
SANITIZERS = os.path.join("solenv", "sanitizers", "ui")

# Extra gla11y arguments, copied verbatim from UIConfig.mk.
COMMON_ARGS = [
    "--widgets-suffixignored",
    "+ValueSet,HBox,VBox,ToolBox,Preview,PreviewWin,PreviewWindow,PrevWindow",
    "--widgets-button",
    "+svtlo-ManagedMenuButton",
    "--fatal-all",
    "--not-fatal-type", "duplicate-mnemonic",
    "--not-fatal-type", "labelled-by-and-mnemonic",
    "--not-fatal-type", "orphan-label",
]

# Matches a whole `$(eval $(call gb_UIConfig_add_uifiles,<module>,<body>))`
# invocation, body spanning backslash-continued lines up to the closing `))`.
ADD_UIFILES_RE = re.compile(
    r"gb_UIConfig_add_uifiles\s*,\s*([^,]+?)\s*,(.*?)\)\)",
    re.DOTALL,
)


def find_uiconfig_mk_files():
    """Return the sorted list of */UIConfig_*.mk files under SRCDIR."""
    result = []
    for entry in sorted(os.listdir(SRCDIR)):
        moddir = os.path.join(SRCDIR, entry)
        if not os.path.isdir(moddir):
            continue
        try:
            names = os.listdir(moddir)
        except OSError:
            continue
        for name in sorted(names):
            if name.startswith("UIConfig_") and name.endswith(".mk"):
                result.append(os.path.join(moddir, name))
    return result


def enumerate_modules():
    """Parse the UIConfig_*.mk files into a dict: module -> [repo-relative .ui paths].

    A module with no add_uifiles entries yields an empty list (and is skipped
    by the caller).  Paths are returned repo-relative with the .ui suffix.
    """
    modules = {}
    for mk in find_uiconfig_mk_files():
        with open(mk, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for match in ADD_UIFILES_RE.finditer(text):
            module = match.group(1).strip()
            body = match.group(2)
            uifiles = modules.setdefault(module, [])
            # Body is a backslash-continued whitespace-separated token list.
            for token in body.replace("\\", " ").split():
                token = token.strip()
                if not token or "/" not in token:
                    continue
                uifiles.append(token + ".ui")
    # Ensure every registered UIConfig module appears even with zero uifiles,
    # so --list reflects the full registration set.
    for mk in find_uiconfig_mk_files():
        with open(mk, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.search(r"gb_UIConfig_UIConfig\s*,\s*([^)\s]+)\s*\)", line)
                if m:
                    modules.setdefault(m.group(1).strip(), [])
    return modules


def suppr_paths(module):
    """Return (false_path_or_None, suppr_path_or_None) for a module.

    Paths are repo-relative and returned only when the file actually exists.
    """
    false_rel = os.path.join(SANITIZERS, module + ".false")
    suppr_rel = os.path.join(SANITIZERS, module + ".suppr")
    false_path = false_rel if os.path.isfile(os.path.join(SRCDIR, false_rel)) else None
    suppr_path = suppr_rel if os.path.isfile(os.path.join(SRCDIR, suppr_rel)) else None
    return false_path, suppr_path


# gla11y prints e.g. "3 new errors" / "1 new fatal"; capture the leading count.
COUNT_RE = re.compile(r"^(\d+)\s+new\s+(error|fatal)s?\b")


def run_module(module, uifiles, verbose=False):
    """Run gla11y for one module. Return (ok, count, output).

    ok is False when gla11y reports N>0 new errors or new fatals, or when it
    exits non-zero.  Missing suppr/false files are simply not passed.
    """
    if not uifiles:
        return True, 0, ""

    false_path, suppr_path = suppr_paths(module)

    # Invoke gla11y with the SAME interpreter running this checker so the gate
    # is portable: `py -3` on this Windows host, `python3` on the Linux CI
    # runner (where `py` does not exist). Passing the script to the interpreter
    # avoids depending on the shebang/executable bit across platforms.
    cmd = [sys.executable, "bin/gla11y", "-P", SRCDIR + os.sep]
    if false_path:
        cmd += ["-f", false_path]
    if suppr_path:
        cmd += ["-s", suppr_path]
    cmd += COMMON_ARGS
    cmd += uifiles

    proc = subprocess.run(
        cmd,
        cwd=SRCDIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    output = proc.stdout or ""

    max_count = 0
    for line in output.splitlines():
        m = COUNT_RE.match(line.strip())
        if m:
            max_count = max(max_count, int(m.group(1)))

    ok = (max_count == 0) and (proc.returncode == 0)

    if verbose and output.strip():
        sys.stderr.write(output)

    return ok, max_count, output


def cmd_list(modules):
    total_files = 0
    print("UIConfig modules (module -> .ui file count):")
    for module in sorted(modules):
        uifiles = modules[module]
        total_files += len(uifiles)
        _, suppr_path = suppr_paths(module)
        flag = "" if suppr_path else "   (no suppr file)"
        print("  %-24s %4d%s" % (module, len(uifiles), flag))
    print("Total: %d modules, %d .ui files" % (len(modules), total_files))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build-free gla11y accessibility FATAL gate for UIConfig .ui files.",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Print the module -> .ui-file counts and exit (no gla11y run).",
    )
    parser.add_argument(
        "--module", action="append", metavar="NAME",
        help="Only check the named module(s). May be repeated.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Echo gla11y output for every module, not just failing ones.",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(GLA11Y):
        sys.stderr.write("error: gla11y not found at %s\n" % GLA11Y)
        return 2

    modules = enumerate_modules()
    if not modules:
        sys.stderr.write("error: no UIConfig modules enumerated from */UIConfig_*.mk\n")
        return 2

    if args.list:
        return cmd_list(modules)

    selected = sorted(modules)
    if args.module:
        wanted = set(args.module)
        selected = [m for m in selected if m in wanted]
        missing = wanted - set(modules)
        if missing:
            sys.stderr.write("error: unknown module(s): %s\n" % ", ".join(sorted(missing)))
            return 2

    failures = []
    checked_files = 0
    for module in selected:
        uifiles = modules[module]
        if not uifiles:
            continue
        checked_files += len(uifiles)
        ok, count, output = run_module(module, uifiles, verbose=args.verbose)
        if ok:
            print("  OK   %-24s (%d files)" % (module, len(uifiles)))
        else:
            print("  FAIL %-24s (%d new error/fatal)" % (module, count))
            failures.append((module, output))

    print("")
    if failures:
        print("gla11y a11y FATAL gate FAILED: %d module(s) with new errors/fatals\n"
              % len(failures))
        for module, output in failures:
            print("=" * 70)
            print("MODULE: %s" % module)
            print("=" * 70)
            print(output.rstrip())
            print("")
        return 1

    print("gla11y a11y FATAL gate PASSED: %d module(s), %d .ui files, 0 FATALs"
          % (len([m for m in selected if modules[m]]), checked_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
