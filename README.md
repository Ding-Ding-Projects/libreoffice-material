# LibreOffice Material

An experimental LibreOffice engineering fork exploring a suite-wide Material
Design 3 interface while retaining LibreOffice's native implementation stack,
document engine, file-format support, and accessibility foundations.

> **Current milestone: 0 — foundation with an initial native source slice.**
> Material widget definitions, VCL selection/fallback plumbing, reader coverage,
> and Start Center changes now exist in the local worktree. They have **not**
> been compiled or run as LibreOffice. The whole GUI has not been rewritten, and
> no application surface is Material-complete.

[Project site](https://codingmachineedge.github.io/libreoffice-material/) ·
[Roadmap](ROADMAP.md) ·
[Material specification](MATERIAL_DESIGN.md) ·
[Headless UI evidence plan](docs/HEADLESS_UI_EVIDENCE.md) ·
[Screenshot index](docs/SCREENSHOTS.md)

## What is true today

| Area | State | Evidence |
| --- | --- | --- |
| LibreOffice source baseline | Imported | This repository's initial tree matches upstream commit `63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21` |
| Material design direction | Initial specification | [`MATERIAL_DESIGN.md`](MATERIAL_DESIGN.md) |
| Initial native implementation | Source present, unbuilt | Material file theme/VCL plumbing and Start Center source changes are local; build and runtime gates remain open |
| Whole-suite implementation | Incomplete | Phased work remains in [`ROADMAP.md`](ROADMAP.md) |
| Verified UI screenshots | None yet | The truthful empty registry is in [`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md) |
| Headless harness | Preflight passed; LibreOffice not run | A temporary Notepad-only driver preflight proved the off-screen mechanics, not this UI; see [`docs/HEADLESS_UI_EVIDENCE.md`](docs/HEADLESS_UI_EVIDENCE.md) |

This table is deliberately conservative. A roadmap item changes state only when
its code, build result, interaction checks, and committed visual evidence agree.

## Initial native slice

The first implementation slice is intentionally opt-in and shared-layer first.
The current local source changes include:

- a packaged `material/definition.xml` file-widget theme with Material palette,
  controls, focus/state variants, menus, tabs, surfaces, and progress drawing;
- selection through `VCL_FILE_WIDGET_THEME`, with a restricted safe theme name,
  a mutex-protected cache keyed by theme, and fallback to the existing `online`
  definition when a requested theme cannot load;
- Windows non-printer graphics initialization routed through the existing
  file-widget backend gate; it remains inactive unless
  `VCL_DRAW_WIDGETS_FROM_FILE` is present;
- definition-aware support reporting so parts absent from the selected file
  theme stay on their existing fallback path;
- expanded `WidgetDefinitionReader` style/palette mapping and C++ assertions for
  the Material definition;
- Start Center spacing, a Home header/subtitle, surface roles, and recent/template
  text and fill colors derived from VCL style settings.

Once a compatible LibreOffice build exists, the intended Windows opt-in is to
set both variables before launching the built application:

```powershell
$env:VCL_DRAW_WIDGETS_FROM_FILE = "1"
$env:VCL_FILE_WIDGET_THEME = "material"
```

These variables describe the source path; they are not a successful-run claim.
The `vcl_widget_definition_reader_test` target and a real `soffice` launch have
not run on this worktree.

## Product direction

LibreOffice Material aims to modernize the complete desktop experience rather
than place a cosmetic skin over a few screenshots. The intended scope includes:

- shared application chrome, menus, command surfaces, sidebars, status bars,
  dialogs, pickers, notifications, and start center;
- Writer, Calc, Impress, Draw, Base, Math, and shared editing components;
- Material 3 color, type, shape, elevation, state, density, and motion tokens;
- keyboard-first operation, screen-reader semantics, high contrast, reduced
  motion, localization, bidirectional text, and platform conventions;
- responsive/adaptive behavior that respects information-dense desktop work.

The implementation remains native LibreOffice code. Product UI changes should
use the languages and resource formats already used by the affected upstream
module—primarily C++, VCL, UNO, and XML `.ui`/configuration resources. The
static HTML and CSS under [`site/`](site/) are only the project website; they
are not a replacement runtime for LibreOffice.

## Architecture at a glance

Materialization should flow from shared primitives into suite surfaces:

1. semantic tokens and platform-aware theme resolution;
2. VCL widgets, focus/state behavior, and rendering primitives;
3. shared framework chrome and reusable dialogs;
4. application-specific surfaces in Writer, Calc, Impress/Draw, Base, and Math;
5. accessibility, localization, performance, and headless visual verification.

The core upstream areas remain the natural integration points:

| Module | Relevance |
| --- | --- |
| [`vcl/`](vcl/) | Widget toolkit, rendering abstraction, platform backends, and theme behavior |
| [`framework/`](framework/) | Menus, toolbars, status bars, and application chrome |
| [`sfx2/`](sfx2/) | Shared document framework and shell behavior |
| [`svx/`](svx/) | Shared drawing and editing controls |
| [`cui/`](cui/) | Common dialogs and option surfaces |
| [`desktop/`](desktop/) | Application bootstrap and start-center integration |
| [`sw/`](sw/) | Writer |
| [`sc/`](sc/) | Calc |
| [`sd/`](sd/) | Impress and Draw |

See [`MATERIAL_DESIGN.md`](MATERIAL_DESIGN.md) for component rules and
[`ROADMAP.md`](ROADMAP.md) for sequencing and acceptance gates.

## Evidence, not mock completion

No screenshot is shown until it is captured from a build of this repository and
registered with its commit, environment, test scenario, and result. Empty cards
on the project site are **evidence slots**, not mockups or generated UI claims.

The verification driver is the sibling
[`lowlevel-computer-use-mcp`](https://github.com/codingmachineedge/lowlevel-computer-use-mcp)
project. It can launch real GUI applications on an off-screen desktop, target
windows without focusing them, and capture window images. A 2026-07-16 preflight
using driver commit `806d9ba85e4afbc2af58d7499496babfa7c68891`
successfully created and removed an off-screen Win32 desktop around Notepad.
That temporary capture was unrelated to LibreOffice, was not retained, and is
not registered as project evidence. The driver is not currently vendored into
this repository. Exact preflight facts, the future LibreOffice capture contract,
and safety rules are in [`docs/HEADLESS_UI_EVIDENCE.md`](docs/HEADLESS_UI_EVIDENCE.md).

## Building LibreOffice

This fork retains the upstream LibreOffice build chain. LibreOffice is a large,
cross-platform native project; consult The Document Foundation's current
[platform build instructions](https://wiki.documentfoundation.org/Development/How_to_build)
and the imported build files before configuring a machine.

> **Current build blocker:** this host has no installed WSL distribution or
> configured LibreOffice WSL helper, and the Windows-native LibreOffice build
> prerequisites are not available. Consequently the C++ unit target and a real
> application capture have not been run.

At the imported baseline, the upstream README records these minimum build
baselines:

| Platform | Imported upstream build baseline |
| --- | --- |
| Windows | WSL helper plus Visual Studio 2022; runtime baseline Windows 10 |
| macOS | macOS 13 or later with Xcode 14.3 or later; runtime baseline macOS 11 |
| Linux | GCC 13 or Clang 18 with libstdc++ 11; RHEL/CentOS 9-class baseline |
| Java | JDK 17 or later |
| Python | Python 3.11 |

Typical source builds start with the upstream `autogen.sh`/`configure` flow and
then use `make`. Platform-specific dependencies and supported switches change,
so the TDF build documentation and [`distro-configs/`](distro-configs/) are the
authority. [LODE](https://wiki.documentfoundation.org/Development/lode) can help
prepare Windows and macOS development environments.

For extension development rather than core changes, use the
[LibreOffice SDK](https://api.libreoffice.org/) and
[Developer's Guide](https://wiki.documentfoundation.org/Documentation/DevGuide).

## Upstream provenance

This is an independent experimental fork of
[`LibreOffice/core`](https://github.com/LibreOffice/core), the office-suite
source maintained by The Document Foundation and its contributor community.

- Upstream remote: `https://github.com/LibreOffice/core.git`
- Imported upstream commit: `63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21`
- Import commit in this repository: `44d393283e776c7e099763496c57b02ae509cd15`
- Import method: a new root commit with a tree identical to that upstream commit;
  the original upstream history is available through the `upstream` remote.

See [`docs/PROVENANCE.md`](docs/PROVENANCE.md) for reproducible verification.
LibreOffice Material is not an official The Document Foundation distribution,
and no endorsement is implied.

## Contributing

Start with the design contract and the earliest incomplete roadmap gate. Keep
changes narrow enough to build and verify, preserve existing shortcuts and
accessibility semantics, and attach genuine headless evidence for visible UI
changes. Never add generated or staged images as if they were application
captures.

When changing native product UI:

1. identify the shared component before adding an application-local variant;
2. use semantic tokens instead of hard-coded colors or elevations;
3. test keyboard, focus, high-contrast, localization, and reduced-motion paths;
4. record the exact commit and environment in the evidence manifest;
5. update the roadmap and repository memory only after the acceptance gate
   passes.

## License and attribution

LibreOffice source is open source and copyleft-licensed. Retain the license
headers and notices of every file you modify. The authoritative license texts
shipped with this source tree are [`COPYING`](COPYING),
[`COPYING.LGPL`](COPYING.LGPL), and [`COPYING.MPL`](COPYING.MPL); entirely new
LibreOffice source files should follow [`TEMPLATE.SOURCECODE.HEADER`](TEMPLATE.SOURCECODE.HEADER).

LibreOffice is backed by The Document Foundation. LibreOffice and The Document
Foundation names and marks belong to their respective owners. Project-specific
documentation and site work must not erase upstream authorship or licensing.
