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

Stages 0-3 are done and were verified green by the Linux native CI leg plus the
Windows UI contract.

## What is preserved and why

Deliberately **not** removed, because Windows depends on them:

- **`sal`** — the portability layer. Untouched at every stage.
- **`vcl/headless`** — the Windows CppUnit test path links `vclplug_win`, not
  `svp`; an earlier "headless is the test harness" premise was wrong, so
  headless stays.
- **`vcl/unx/generic`, `vcl/unx/x11`, `Library_vclplug_gen.mk`** and the
  `vcl.common.component` fragments — they belong to the final stage.
- **The Windows forced-colors / high-contrast widget-draw fallback** — an
  accessibility path; untouched.

## Remaining stages (NOT done)

The plan has six stages, 0-5. Stages 0-3 are complete; the following are held:

- **Stage 4** — the non-Windows module *bodies*.
- **Stage 5** — `vcl/unx` + `vcl/headless` **and the Linux CI leg itself**.

Stages 4 and 5 are held until an MSI baseline confirms the current state,
**because stage 5 removes the fast Linux check** that currently guards every
push. Losing it before an MSI baseline exists would remove the only fast
compile signal.

## Failure modes and verification

- Stages 0-3 are Linux-CI-green and cross-checked by the build-free gate (78
  checkers + 78 suites, 0 failures) plus the Windows UI contract.
- **Honest caveat:** roughly 5% of the removal — `configure.ac` host-os edits
  and dropped UNO component fragments — can produce a **green MSI that fails
  only when a user opens the affected feature**. Those parts need a
  shipped-MSI smoke test, which is exactly why stages 4-5 are gated behind an
  MSI baseline rather than shipped on the fast Linux signal alone.
- `.mk` files are CRLF in the worktree and normalised by git on commit, so
  build-file edits must be newline-agnostic and verified by blob-hash
  comparison, not by eye. (This host has `core.autocrlf=true` in the system
  gitconfig but `false` locally, which caused several whole-file CRLF-flip
  incidents this session.)

## Security considerations

None. This is a build-graph reduction; it removes non-Windows code paths and
changes no security-relevant behavior on Windows.
