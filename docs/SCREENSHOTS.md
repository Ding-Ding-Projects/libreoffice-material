# Verified screenshot index

**Current canonical gallery screenshot count: 9.**

A newer genuine suite gallery from the shipped `windows-msi-89-1-705cf7ff4b`
release binary is registered in the
[2026-07-23 windows-msi-89 gallery](#2026-07-23--windows-msi-89-1-705cf7ff4b-genuine-suite-gallery)
section below: a Start Center trio (light, dark, forced high contrast) with
schema-v2 evidence-run manifests, plus best-effort direct-MCP captures of all six
applications (light and dark) and six shared dialogs. Those module and dialog
images are genuine and each was read and visually confirmed, but — unlike the
harness Start Center runs — they carry no per-run manifest, so they are registered
by [`screenshots/genuine/PROVENANCE.json`](screenshots/genuine/PROVENANCE.json)
rather than counted in the canonical smoke gallery above.

The canonical light, dark, and forced-high-contrast trios come from the newest
exact-source Windows x64 MSI payload at
`393263ad924eae8d64b4f9a35bd6486ef83578fc` and verify the
Help/Extensions-only footer. Together they
establish real launch, background Templates navigation, and one keyboard Tab
focus transition in each appearance. They do not establish 200% scaling,
accelerated rendering, localization, suite applications, dialogs, updater UI,
or the MSI lifecycle. The two earlier accepted light runs remain historical
proof, but are not duplicated in the canonical gallery.

A 2026-07-16 off-screen Notepad capture was used only to preflight the local
low-level desktop driver. It was temporary, was not committed, and cannot enter
this registry because it does not show LibreOffice. It remains excluded from
the current count.

## Evidence slots

| Slot | Surface | Minimum checkpoint | Current state | Verified file |
| --- | --- | --- | --- | --- |
| E-START-001 | Start center and shared shell | stable launch, light and dark | Passed for scoped exact-source Home/focus/Templates software-raster smoke in all three appearance profiles; broader shell work remains | Light [`Home`](evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-light.png) / [`keyboard focus`](evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-light-keyboard-focus.png) / [`Templates`](evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-templates-light.png) · dark [`Home`](evidence/runs/20260720-144200-393263ad92-windows-headless-dark/screenshots/start-center-dark.png) / [`keyboard focus`](evidence/runs/20260720-144200-393263ad92-windows-headless-dark/screenshots/start-center-dark-keyboard-focus.png) / [`Templates`](evidence/runs/20260720-144200-393263ad92-windows-headless-dark/screenshots/start-center-templates-dark.png) · light run [`manifest`](evidence/runs/20260720-143309-393263ad92-windows-headless-light/manifest.json) / [`results`](evidence/runs/20260720-143309-393263ad92-windows-headless-light/results.json) · dark run [`manifest`](evidence/runs/20260720-144200-393263ad92-windows-headless-dark/manifest.json) / [`results`](evidence/runs/20260720-144200-393263ad92-windows-headless-dark/results.json) · **shipped `windows-msi-89-1-705cf7ff4b` harness runs (2026-07-23):** light [`Home/focus`](evidence/runs/20260723-164940-705cf7ff4b-windows-headless-light-keyboard-focus/) / [`Templates`](evidence/runs/20260723-165153-705cf7ff4b-windows-headless-light-templates/) · dark [`Home`](evidence/runs/20260723-164421-705cf7ff4b-windows-headless-dark/) · forced high contrast [`Home`](evidence/runs/20260723-164734-705cf7ff4b-windows-headless-highcontrast/) |
| E-NONAG-FRESH | Blank Writer, genuinely fresh profile | no suppression flags; one owned Writer window for at least 15 seconds; former-nag titles/a11y absent | Dedicated source harness and mutation contract pass; exact-build run and review pending | — |
| E-NONAG-LEGACY | Blank Writer, seeded legacy profile | all former first-run/promotion/association/AutoCorrect/crash triggers enabled safely; one owned Writer window; former-nag titles/a11y absent | Dedicated source harness and mutation contract pass; exact-build run and review pending | — |
| E-WRITER-001 | Writer | document open, formatting and sidebar visible | Genuine light + dark capture 2026-07-23 from `windows-msi-89-1-705cf7ff4b` (direct MCP): menu bar, formatting toolbar with pill style/font pickers, ruler, blank page, and sidebar rail all visible. Full smoke-harness acceptance still pending | [`writer-light`](screenshots/genuine/writer-light.png) · [`writer-dark`](screenshots/genuine/writer-dark.png) (SHA-256 in [`PROVENANCE.json`](screenshots/genuine/PROVENANCE.json)) |
| E-CALC-001 | Calc | populated sheet, formula bar and sheet tabs visible | Genuine light + dark capture 2026-07-23 (direct MCP): pill Name Box, formula bar, purple-tinted A1 header, and Sheet1 tab visible. The sheet is **blank** — the populated-sheet checkpoint and full smoke-harness acceptance remain pending | [`calc-light`](screenshots/genuine/calc-light.png) · [`calc-dark`](screenshots/genuine/calc-dark.png) (SHA-256 in [`PROVENANCE.json`](screenshots/genuine/PROVENANCE.json)) |
| E-IMPRESS-001 | Impress | editing canvas, slide pane and properties visible | Genuine light + dark capture 2026-07-23 (direct MCP): Slides pane, editing canvas with title/text placeholders, and Properties/Layouts deck all visible. Full smoke-harness acceptance still pending | [`impress-light`](screenshots/genuine/impress-light.png) · [`impress-dark`](screenshots/genuine/impress-dark.png) (SHA-256 in [`PROVENANCE.json`](screenshots/genuine/PROVENANCE.json)) |
| E-DIALOG-001 | Shared dialog | keyboard focus, validation, and long labels | Genuine light captures 2026-07-23 (direct MCP; Writer host, UNO dispatch, Escape-cancelled): Find & Replace shows a purple-outlined focused field and long checkbox labels; six dialogs total (see gallery below). Validation/error states not yet exercised; full smoke-harness acceptance pending | [`find-replace`](screenshots/genuine/find-replace-light.png) · [`print`](screenshots/genuine/print-light.png) · [`options`](screenshots/genuine/options-light.png) · [`pdf-export`](screenshots/genuine/pdf-export-light.png) · [`document-properties`](screenshots/genuine/document-properties-light.png) · [`template-manager`](screenshots/genuine/template-manager-light.png) (SHA-256 in [`PROVENANCE.json`](screenshots/genuine/PROVENANCE.json)) |
| E-A11Y-001 | Accessibility modes | high contrast, 200% scale, visible focus | In progress — exact-source forced high contrast and visible Tab focus accepted; 200% scale pending | [`Home`](evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/screenshots/start-center-highcontrast.png) · [`keyboard focus`](evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/screenshots/start-center-highcontrast-keyboard-focus.png) · [`Templates`](evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/screenshots/start-center-templates-highcontrast.png) · run [`manifest`](evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/manifest.json) / [`results`](evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/results.json) · **shipped `windows-msi-89-1-705cf7ff4b` (2026-07-23):** forced high contrast [`Home`](evidence/runs/20260723-164734-705cf7ff4b-windows-headless-highcontrast/) · light [`keyboard focus`](evidence/runs/20260723-164940-705cf7ff4b-windows-headless-light-keyboard-focus/) |

## 2026-07-23 — windows-msi-89-1-705cf7ff4b genuine suite gallery

Source: the administratively extracted payload of release
[`windows-msi-89-1-705cf7ff4b`](https://github.com/codingmachineedge/libreoffice-material/releases/tag/windows-msi-89-1-705cf7ff4b)
(`program/soffice.exe`; Material activation unconditional). Method: unedited
per-window `PrintWindow` on an off-screen desktop via `lowlevel-computer-use-mcp`
`547a102a49169d41da876de217856229ab7c03a1` (branch `evidence-driver-547a102a`).
Every entry's SHA-256 and `visually_verified: true` flag is recorded in
[`screenshots/genuine/PROVENANCE.json`](screenshots/genuine/PROVENANCE.json)
(23 entries). Each image below was read and visually confirmed to render genuine
Material; no image is a mockup or prototype render.

### Start Center — smoke-harness runs (schema-v2 manifest + results + a11y tree)

| Appearance | Run directory | Screenshot(s) |
| --- | --- | --- |
| Light — Home + keyboard focus | [`20260723-164940-705cf7ff4b-windows-headless-light-keyboard-focus`](evidence/runs/20260723-164940-705cf7ff4b-windows-headless-light-keyboard-focus/) ([manifest](evidence/runs/20260723-164940-705cf7ff4b-windows-headless-light-keyboard-focus/manifest.json) / [results](evidence/runs/20260723-164940-705cf7ff4b-windows-headless-light-keyboard-focus/results.json)) | [`start-center-light`](screenshots/genuine/start-center-light.png) · [`start-center-light-keyboard-focus`](screenshots/genuine/start-center-light-keyboard-focus.png) |
| Light — Templates navigation | [`20260723-165153-705cf7ff4b-windows-headless-light-templates`](evidence/runs/20260723-165153-705cf7ff4b-windows-headless-light-templates/) ([manifest](evidence/runs/20260723-165153-705cf7ff4b-windows-headless-light-templates/manifest.json) / [results](evidence/runs/20260723-165153-705cf7ff4b-windows-headless-light-templates/results.json)) | [`start-center-templates-light`](screenshots/genuine/start-center-templates-light.png) |
| Dark — Home | [`20260723-164421-705cf7ff4b-windows-headless-dark`](evidence/runs/20260723-164421-705cf7ff4b-windows-headless-dark/) ([manifest](evidence/runs/20260723-164421-705cf7ff4b-windows-headless-dark/manifest.json) / [results](evidence/runs/20260723-164421-705cf7ff4b-windows-headless-dark/results.json)) | [`start-center-dark`](screenshots/genuine/start-center-dark.png) |
| Forced high contrast — Home | [`20260723-164734-705cf7ff4b-windows-headless-highcontrast`](evidence/runs/20260723-164734-705cf7ff4b-windows-headless-highcontrast/) ([manifest](evidence/runs/20260723-164734-705cf7ff4b-windows-headless-highcontrast/manifest.json) / [results](evidence/runs/20260723-164734-705cf7ff4b-windows-headless-highcontrast/results.json)) | [`start-center-highcontrast`](screenshots/genuine/start-center-highcontrast.png) |

The base light Start Center image predates this session and was already
committed; the fresh Dark/HC/keyboard-focus/Templates re-captures are
byte-identical to the earlier campaign's, corroborating reproducibility.

### Applications — direct-MCP captures (light + dark)

All under [`screenshots/genuine/`](screenshots/genuine/); no per-run manifest
(registered by `PROVENANCE.json`).

| Application | Light | Dark |
| --- | --- | --- |
| Writer — blank document | [`writer-light`](screenshots/genuine/writer-light.png) | [`writer-dark`](screenshots/genuine/writer-dark.png) |
| Calc — blank spreadsheet | [`calc-light`](screenshots/genuine/calc-light.png) | [`calc-dark`](screenshots/genuine/calc-dark.png) |
| Impress — new presentation | [`impress-light`](screenshots/genuine/impress-light.png) | [`impress-dark`](screenshots/genuine/impress-dark.png) |
| Draw — blank drawing | [`draw-light`](screenshots/genuine/draw-light.png) | [`draw-dark`](screenshots/genuine/draw-dark.png) |
| Math — formula editor | [`math-light`](screenshots/genuine/math-light.png) | [`math-dark`](screenshots/genuine/math-dark.png) |
| Base — Database Wizard | [`base-light`](screenshots/genuine/base-light.png) | [`base-dark`](screenshots/genuine/base-dark.png) |

### Dialogs — direct-MCP captures (light)

Opened in a Writer host via UNO `.uno:` dispatch and captured, then dismissed
with Escape — none was confirmed. Nothing was printed, exported, or saved, and no
database was created; Base's "Create a new database" is disabled because the
extracted payload bundles no embedded HSQLDB/Firebird engine.

| Dialog | UNO command | Screenshot |
| --- | --- | --- |
| Find & Replace | `.uno:SearchDialog` | [`find-replace-light`](screenshots/genuine/find-replace-light.png) |
| Print | `.uno:Print` | [`print-light`](screenshots/genuine/print-light.png) |
| Tools > Options | `.uno:OptionsTreeDialog` | [`options-light`](screenshots/genuine/options-light.png) |
| Export as PDF (PDF Options) | `.uno:ExportToPDF` | [`pdf-export-light`](screenshots/genuine/pdf-export-light.png) |
| File > Properties (Document Properties) | `.uno:SetDocumentProperties` | [`document-properties-light`](screenshots/genuine/document-properties-light.png) |
| Template Manager | `.uno:TemplateManager` | [`template-manager-light`](screenshots/genuine/template-manager-light.png) |

**Acceptance boundary:** the Start Center runs above carry schema-v2 manifests and
passed the smoke harness; the application and dialog captures are genuine and
visually confirmed but were taken by direct MCP driving without the harness's
scenario/manifest gate, so they are registered here and in `PROVENANCE.json`
rather than promoted into the canonical smoke gallery count. Formal `B V I A L P C`
acceptance-gate credit remains follow-up work.

## Adding a verified image

1. Complete a run using [`HEADLESS_UI_EVIDENCE.md`](HEADLESS_UI_EVIDENCE.md).
2. Confirm the image, manifest, hashes, scenario result, and sensitive-data
   review all pass.
3. Commit the real image inside its evidence run directory.
4. Replace the dash in **Verified file** with a relative link to that existing
   file and add its run identifier.
5. Update the public site, roadmap, and repository memory in the same change.

Never pre-populate the index with a future path: a link appearing here is a
claim that the referenced artifact exists and has passed review.

## Historical accepted proof

The first accepted light-profile run,
[`20260720-012853-577059e274-vs2026-msi-raster`](evidence/runs/20260720-012853-577059e274-vs2026-msi-raster/),
remains immutable evidence for the older extracted payload. Its Home image is
byte-identical to the current canonical run's Home image; its Templates image
has its own recorded hash. Corrected light run
[`20260720-022159-fbba560e27-vs2026-msi-raster-restart-suppression`](evidence/runs/20260720-022159-fbba560e27-vs2026-msi-raster-restart-suppression/)
also remains immutable historical evidence for the exact current payload. The
fresh committed-harness run supersedes both only as the canonical gallery source
because it adds a verified light keyboard-focus state and dedicated-driver
cleanup proof. None of these runs proves MSI install, repair, upgrade, uninstall,
or restart-suppression lifecycle behavior.
