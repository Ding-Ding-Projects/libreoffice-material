# Windows-only build strip

This fork is being made strictly Windows-only: the iOS, Android, macOS,
Quartz, Aqua, Qt, KF (KDE Frameworks) and GTK backends are removed from the
build graph. The work is staged so a mistake fails at gbuild parse time in
seconds rather than hours into a compile.

## Stages

| Stage | Commit | Removed |
| --- | --- | --- |
| 0 | `59f2928fb` | Non-Windows build-graph leaves neither CI leg builds: `CppunitTest_vcl_a11y` / `_gtk3_a11y` (ATSPI), `CppunitTest_vcl_gen` (X11), `CppunitTest_vcl_unx_generic`, the X11 font packages, `Package_osxres`, `Executable_lo_kde5filepicker`. |
| 1 | `272fb99de` | iOS and Android: `vcl/ios`, `vcl/android`, `sal/android`, `Library_lo-bootstrap.mk`, EMSCRIPTEN blocks, the `vcl.common.component.{ios,android}` fragments. |
| 2 | `58e4fec2e` | macOS, Quartz and Aqua: `vcl/osx`, `vcl/quartz`, `vcl/skia/osx`, `Library_vclplug_osx.mk`, the Aqua file picker, macOS extensions and setup, the top-level Xcode project (222 files). Fixed four unconditional `configure.ac` references to deleted `Info.plist` files that would have broken configure on Windows. |
| 3 | `769117ddc` | Qt, KF and GTK plugin backends: `vcl/qt5`, `vcl/qt6`, `vcl/unx/{gtk3,gtk3_kde5,gtk4,kf5,kf6}`, the `shell` desktop/KDE/mac backends, seven `Library_vclplug_*` makefiles (530 files). `use_qt6` is deliberately kept — avmedia's qt6 backend still consumes it. |
| 4+5 | `7874c6b85` | The non-Windows module bodies **and** the X11/headless VCL, in one commit: `vcl/{unx,headless,null,skia/x11,source/opengl/x11}` and their `vcl/inc` counterparts, `Library_vclplug_gen.mk`, the `unx`/`headless` component fragments, `sysui` (except the Windows `*.ico` files), `desktop/unx`, `svl/unx`, `shell/source/unix`, `odk/source/unoapploader/unx`, every `bridges/source/cpp_uno/gcc3_*` bridge, all non-WNT/MSC `solenv/gbuild/platform/*`, the whole `USE_HEADLESS_CODE` / `ENABLE_HEADLESS` / `--enable-headless` machinery, and the former Linux installer workflow itself. |

Stages 0-3 were historically verified green by the former Linux native CI leg
plus the Windows UI contract. Stage 4 deliberately made a Linux build
unsupported, so stages 4 and 5 landed together at `7874c6b85` with
`.github/workflows/build-installer.yml` removed in the same commit. The
resulting Windows-only tree later compiled in the successful MSI-123 build at
`952090ce2`. That is real Windows product/MSI compile evidence, not runtime
coverage for every feature whose non-Windows counterpart was removed.

## What is preserved and why

Deliberately **not** removed, because Windows depends on them:

- **`sal`** — the portability layer. Untouched at every stage. Its Windows path
  is `sal/osl/w32`; `sal/osl/unx` is left in place deliberately.
- **`sysui/desktop/icons/*.ico`** — the `sysui` *module* is gone, but the flat
  `.ico` files are consumed by `desktop/WinResTarget_*.mk` on Windows and must
  stay. Only `icons/hicolor` (freedesktop) and `icons/macos` (iconsets) went.
- **`bridges/Library_cpp_uno.mk`** — never deleted: `bridges/Module_bridges.mk`
  aborts the build if `bridges_SELECTED_BRIDGE` is unset. It now cascades to
  the three MSC arms (`msvc_win32_{arm64,intel,x86-64}`) only.
- **`solenv/gbuild/platform/unittest-failed-default.sh`** — the `?=` default at
  `CppunitTest.mk:22`.
- **The Windows forced-colors / high-contrast widget-draw fallback** — an
  accessibility path; untouched.

## The OS guard

`solenv/gbuild/gbuild.mk` now hard-errors when `OS != WNT` or `COM != MSC`,
because its only platform dispatch is
`include $(GBUILDDIR)/platform/$(OS)_$(CPUNAME)_$(COM).mk` and no non-Windows
platform makefile exists any more. Without the guard a wrong `OS` produced an
obscure "no rule to make target .../LINUX_X86_64_GCC.mk".

## Failure modes and verification

- Stages 0-3 were Linux-CI-green before that workflow was deliberately removed;
  the build-free gate and Windows UI contract remain active.
- **After stage 4+5 there is no Linux compile path.** The ~3h Windows MSI build
  is the native compile gate. Before MSI-123 completed, the change was validated
  statically with an inbound-reference grep before each deletion, a
  dangling-reference sweep over every removed name afterwards, an
  `ifeq/ifneq/ifdef/ifndef` vs `endif` balance count on every edited makefile
  (all balance to 0), and a `configure.ac` `if`/`fi` + `case`/`esac` delta
  check against `HEAD` (unchanged). Successful MSI-123 at `952090ce2` then
  compiled the resulting product and produced its installer.
- **`configure.ac` was the highest-risk file**, because a wrong edit could
  silently unset a variable and fail only at configure time. There was no
  `autoconf` on the authoring host, so the edits were not syntax-checked locally;
  MSI-123 subsequently passed configure and compile on Windows.
- **Honest caveat:** roughly 5% of the removal — `configure.ac` host-os edits
  and dropped UNO component fragments — can produce a **green MSI that fails
  only when a user opens the affected feature**. Those parts need a
  shipped-MSI smoke test.
- `.mk` files are often CRLF in the worktree while the git blob is LF. The
  repo-local `core.autocrlf=false` wins over the system `true`, so a CRLF
  worktree file staged as-is flips the whole file; `git status` hides this
  until the file is touched, because the stat cache reports it clean. Every
  edited file here was rewritten to match its `HEAD` blob's newline style and
  verified by per-file diffstat (20 insertions / 552 deletions across 29
  modified files — no whole-file rewrites).

## Security considerations

None. This is a build-graph reduction; it removes non-Windows code paths and
changes no security-relevant behavior on Windows.
