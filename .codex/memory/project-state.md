# Project state

Last reviewed: 2026-07-16

## Objective

Modernize the complete LibreOffice GUI using Material Design principles while
retaining the native implementation languages and upstream office-suite
functionality. Prove visible work through real builds and off-screen desktop
testing, publish project documentation and evidence, and preserve upstream
licensing and provenance.

## Current milestone

**Milestone 0 — reproducible foundation, in progress.**

The repository contains an imported LibreOffice source baseline, an initial
native Material source slice, design contract, roadmap, published GitHub Pages
site, screenshot registry, and headless evidence plan. The automation harness
has passed a Notepad-only off-screen preflight. The native slice has not been
built or run as LibreOffice, so this does not prove a whole-GUI rewrite or any
completed application surface.

## Recorded facts

- GitHub repository: `codingmachineedge/libreoffice-material`.
- Default branch observed locally: `main`.
- Upstream: `LibreOffice/core`.
- Imported upstream commit: `63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21`.
- Fork import commit: `44d393283e776c7e099763496c57b02ae509cd15`.
- Initial Material implementation commit:
  `46807f76f9a744fe61732e90f6085cc82eef16f5`.
- The two commits shared tree object
  `68ccb73abac4f7da67f894f11b0802627e90b474` when verified.
- Initial native source slice: packaged Material definition; opt-in file-widget
  theme selection/cache/fallback; definition-aware support; palette reader
  coverage; Material control/menu/progress states; and Start Center
  spacing/header/surface/recent/template treatment.
- Required runtime opt-in: `VCL_DRAW_WIDGETS_FROM_FILE=1` and
  `VCL_FILE_WIDGET_THEME=material`.
- UI driver: sibling repository `lowlevel-computer-use-mcp`, preflighted at
  commit `806d9ba85e4afbc2af58d7499496babfa7c68891`.
- 2026-07-16 harness preflight: created
  `WinSta0\LibreOfficeMaterialQA`, launched and enumerated an off-screen Notepad
  window (HWND `37291736`, `1920×1125`), captured it through `PrintWindow` with
  `rendered_ok: true`, killed only run-scoped Notepad processes, and confirmed
  teardown when `OpenDesktop` returned Win32 error `2`.
- Temporary preflight capture SHA-256:
  `03C6A068ACAAB96579621CE0BFC4F447C0F43E8EB23DDB5B8665A580E062BFA3`;
  it was not retained because it was unrelated to LibreOffice.
- Verified LibreOffice Material screenshots: **0**.
- GitHub Pages source: `site/`; public URL:
  `https://codingmachineedge.github.io/libreoffice-material/`.
- Pages uses GitHub Actions workflow mode. Run `29510014215` deployed commit
  `46807f76f9a744fe61732e90f6085cc82eef16f5` successfully on 2026-07-16;
  follow-up endpoint checks returned HTTP `200` for both `/` and `styles.css`.

## Required next gates

1. install a supported LibreOffice build environment and document a reproducible
   native build for the fork;
2. run `vcl_widget_definition_reader_test` against the local Material changes;
3. launch the built start center with the two opt-in variables and an isolated
   profile on the proven headless desktop;
4. preserve the first LibreOffice baseline manifest, result, logs, and reviewed
   screenshot;
5. verify and expand semantic Material tokens and shared VCL primitives;
6. continue through every phase in `ROADMAP.md` without skipping suite surfaces.

## Known evidence gaps

- no native fork build is registered in the evidence ledger;
- no headless LibreOffice Material scenario is registered;
- no screenshot is registered;
- no application surface is verified Material-complete;
- this host has no installed WSL distribution/configured WSL helper and lacks
  the Windows-native LibreOffice prerequisites, so the C++ unit target and real
  application capture have not run.

## Multi-repository boundary

The low-level driver is currently external to this repository. If project
orchestration later requires several independently versioned repositories, a
separate master repository may pin them as Git submodules. That orchestration
decision does not convert unverified external state into evidence and must
record exact submodule commits.
