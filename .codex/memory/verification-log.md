# Verification log

This file records checks of documentation and site infrastructure. These checks
do not prove the native LibreOffice UI has been rebuilt or tested.

## 2026-07-16 — initial documentation and site foundation

- **Upstream import comparison:** `git rev-parse` returned tree object
  `68ccb73abac4f7da67f894f11b0802627e90b474` for both fork import commit
  `44d393283e776c7e099763496c57b02ae509cd15` and upstream commit
  `63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21`; `git diff --stat` between those
  commits was empty.
- **HTML and Markdown integrity:** a read-only Node checker found 15 unique HTML
  IDs, validated 22 HTML links, validated relative links across 12 Markdown
  files, confirmed 197 balanced CSS brace pairs, and reported no missing local
  target.
- **Media truthfulness:** the checked site and project documentation contained
  no `<img>`, inline `<svg>`, Markdown image embed, or CSS `url()` reference.
- **Whitespace:** full `git diff --check` exited successfully after authored
  documentation/site files were normalized to UTF-8 LF without a byte-order
  mark.
- **Trackability:** Git status reported `docs/` as untracked rather than ignored
  after the Doxygen ignore rule was narrowed for authored Markdown and evidence.

Not verified by these checks:

- GitHub Pages deployment (requires repository settings and a workflow run);
- browser rendering on supported viewport and assistive-technology matrices;
- native LibreOffice build, headless launch, interaction, or screenshot capture.

## 2026-07-16 — low-level off-screen harness preflight

- Driver checkout commit:
  `806d9ba85e4afbc2af58d7499496babfa7c68891`.
- Interface: Cheap Version exact functions from the local
  `lowlevel-computer-use-mcp` repository.
- Created `WinSta0\LibreOfficeMaterialQA` and launched Notepad on it.
- Enumerated `Untitled - Notepad` as HWND `37291736` at `1920×1125`.
- `PrintWindow` capture reported `rendered_ok: true` with SHA-256
  `03C6A068ACAAB96579621CE0BFC4F447C0F43E8EB23DDB5B8665A580E062BFA3`.
- Cleanup killed only run-scoped Notepad processes; a subsequent `OpenDesktop`
  returned Win32 error `2`, confirming the named desktop no longer existed.
- The capture was temporary and was not registered, published, or retained.

Scope conclusion: Windows off-screen harness mechanics passed for Notepad. No
LibreOffice binary was built or launched, so accepted Material build/UI evidence
remains zero.

## 2026-07-16 — native verification blocker

- No installed WSL distribution or configured LibreOffice WSL helper was
  available.
- Windows-native LibreOffice build prerequisites were unavailable.
- `vcl_widget_definition_reader_test` and a real `soffice` capture were not run.

## 2026-07-16 — local implementation source audit

Read-only inspection of the dirty worktree confirmed source for:

- packaged `vcl/uiconfig/theme_definitions/material/definition.xml`;
- `VCL_FILE_WIDGET_THEME` selection with safe theme-name validation, a
  mutex-protected cache keyed by theme, and fallback to `online`;
- Windows non-printer graphics invoking the existing widget-backend initializer,
  which only selects file definitions when `VCL_DRAW_WIDGETS_FROM_FILE` is
  present;
- definition-aware support reporting for existing fallback behavior;
- Material controls, menus, progress states, expanded reader palette mappings,
  and corresponding unexecuted C++ assertions;
- Start Center spacing/header/surface/recent/template source changes.

Scope conclusion: implementation source exists locally. This inspection is not
a compiler, unit-test, runtime, accessibility, or visual result.

## 2026-07-16 — status-site refresh

- Read-only link checks found 16 unique HTML IDs, validated 22 HTML links, and
  checked relative links across 12 Markdown files.
- CSS inspection found 218 balanced brace pairs and no remaining layout-width
  `100vw`, negative horizontal margin, or `calc(50% - 50vw)` rule.
- The earlier evidence-section and current-roadmap overflow risks were replaced
  with paint-only full bleed and normal layout margins.
- No image element, inline SVG, Markdown image embed, CSS `url()`, missing local
  target, UTF-8 BOM, CRLF, or trailing whitespace was found in scoped files.
- A separate in-app browser session rendered the live local site after the CSS
  fix. Desktop reported `clientWidth = scrollWidth = 1265`; a `390×844`
  viewport reported `clientWidth = scrollWidth = 375`. A DOM geometry scan
  found no element beyond either viewport.
- The hero, direction, evidence, roadmap, and provenance sections were visually
  inspected, and the browser console reported no warnings or errors. These are
  project-site checks only, not LibreOffice application evidence.
