# LibreOffice Material

An experimental LibreOffice engineering fork exploring a suite-wide Material
Design 3 interface while retaining LibreOffice's native implementation stack,
document engine, file-format support, and accessibility foundations.

> **Current development focus: Phase 1 — tenth Material VCL milestone plus a
> post-tenth Start Center and Windows MSI follow-up.**
> Phase 0's full evidence matrix remains open. Semantic
> widget tokens, full-track progress indicators, value-sensitive level
> indicators, native outlined frames, net-less tree connectors, stricter VCL
> definition parsing, broader state coverage, Start Center changes, and a
> consent-based Windows updater are present in source. Before the Windows-only
> cut removed Linux CI, the then-current tree passed its five required native
> C++ targets in Linux Actions run
> [`29695793821`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/29695793821)
> and in Windows Actions run
> [`29695815101`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/29695815101).
> That Windows run also completed the full LibreOfficeDev installation-set build
> and the legacy CLI payload check; it did not stage an MSI artifact. A later
> exact-source local build at `577059e2741185b512c184c64685c16d335d10ea`
> completed the same five native targets with Visual Studio 2026, produced a
> 199,692,288-byte Windows x64 MSI, and successfully administratively extracted
> its payload with Windows Installer status `0`.
> The whole GUI has not been rewritten, and no application surface is
> Material-complete. The corrected build was published as a normal public,
> non-draft, non-prerelease release at
> [`windows-msi-local-20260720-fbba560e2`](https://github.com/Ding-Ding-Projects/libreoffice-material/releases/tag/windows-msi-local-20260720-fbba560e2).
> It targets exact product source `fbba560e27db26de605c40aa237c554c1f0744b1`,
> contains exactly the MSI plus its checksum and two update manifests, and was
> published on 2026-07-20 at 06:44:07 UTC. Its unsigned 199,688,192-byte MSI has
> SHA-256
> `180e511c065f3e21cd9e4fd0abe31f8886b0cc5ce5ce27a48f2890f83d1afeea`.
> Cache-busted unauthenticated Latest downloads for all four corrected assets
> matched the release sizes and SHA-256 values exactly at that time. On
> 2026-07-26 a pre-fix source-installer release displaced the stable MSI from
> GitHub Latest, so the public Latest MSI URL returned 404. The immutable
> corrected release remained available by its explicit tag. The one-time repair
> restored `windows-msi-123-1-952090ce26` at `952090ce2` as Latest with exactly
> four assets; the canonical MSI/XML/checksum Latest URLs returned HTTP 200 with
> lengths 197,111,808/960/103 bytes. The guarded publisher has since advanced
> Latest to `windows-msi-132-1-90e5ea4f1e` at `90e5ea4f1e`, also with exactly
> four assets. The three legacy unguarded MSI
> runs were cancelled before this follow-up push; the same API shape and public
> route lengths were reverified after cancellation. A later real Sandbox
> diagnostic found that this release's updater command still mixes
> major-upgrade and repair properties: it detects the old ProductCode but
> `REINSTALL=ALL` prevents the new ProductCode from selecting features. Current
> source removes both `REINSTALL` properties from the update launch while
> retaining both restart-suppression properties; this correction is not yet
> runtime lifecycle proof. The older
> [`577059e274` release](https://github.com/Ding-Ding-Projects/libreoffice-material/releases/tag/windows-msi-local-20260720-577059e274)
> remains historical because its updater launch forwarded only four of five
> generated arguments and omitted `REBOOT=ReallySuppress`; do not treat that
> older release as restart-suppression or updater-runtime proof. The earlier hosted run
> found a staging-rule defect after building the MSI:
> recursive discovery included two retained intermediate MSI databases alongside
> the final package. The workflow now scopes discovery to the final success-only
> `install\en-US` directory. The local MSI is unsigned, and the local wrapper's
> parent process exited after successful extraction but before final dist
> staging. Current source now launches administrative extraction through a
> safely quoted, hidden `Start-Process -Wait` client and validates that invariant
> under PowerShell 5.1/7. Exact implementation commit `7029dccf4` then passed
> all five required VS 2026 native targets, the full product/MSI build, waited
> administrative extraction, and canonical MSI/checksum/manifest staging, which
> closes the local wrapper gate.
> Real LibreOfficeDev Start Center runs from the corrected extracted MSI payload
> are now the canonical gallery evidence: three light, three dark, and three forced-
> high-contrast captures with nine matching bounded UNO trees and no collector
> errors. Each appearance profile proves one keyboard Tab focus transition to the
> accessible `Open File` button. The separate interactive
> [design reference](https://ding-ding-projects.github.io/libreoffice-material/prototype.html)
> is a mockup, not the app. To run the actual editor, install upstream LibreOffice
> from [libreoffice.org](https://www.libreoffice.org/download/), which does not
> include these Material changes. This fork is now strictly Windows-only.
> Stages 4+5 landed at `7874c6b85`, removing the former Linux installer workflow
> with the remaining non-Windows build bodies. Successful MSI-123 at
> `952090ce2` compiled that tree, restored document-tab Stage 3 (`af689a470`),
> and the UI-scale control. Tabs still lack runtime UI evidence; UI scale remains
> stored-only. The source-installer workflow has published at least 21 releases,
> but its packaged build-from-source script remains unverified end to end. Current
> release-channel guards make source packages non-Latest, exclude release tags
> from the Windows UI contract, close the build-free CI fleet, and serialize
> future MSI Latest promotion along proven commit ancestry. The one-time remote
> repair and legacy-run containment are complete, and the guarded publisher is
> verified through MSI-132. Exact-source MSI run
> [`30423589955`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/30423589955)
> reached the native compiler and exposed a missing definition include in the
> document-tab source. Corrective run
> [`30427865981`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/30427865981)
> compiled that translation unit, then exposed an owning header that instantiated
> `VclPtr<SfxDocumentTabBar>` with only a forward declaration. Current source
> fixes and regression-pins both definition requirements, but a further MSI
> rerun is still pending. See
> [`docs/build/release-channel-integrity.md`](docs/build/release-channel-integrity.md).

[Project site](https://ding-ding-projects.github.io/libreoffice-material/) ·
[Interactive preview](https://ding-ding-projects.github.io/libreoffice-material/prototype.html) ·
[Roadmap](ROADMAP.md) ·
[Windows UI inventory](docs/WINDOWS_UI_INVENTORY.md) ·
[Canonical Windows rewrite contract](docs/design/00-windows-rewrite-contract.md) ·
[Material specification](MATERIAL_DESIGN.md) ·
[Full design spec](docs/design/README.md) ·
[Headless UI evidence plan](docs/HEADLESS_UI_EVIDENCE.md) ·
[Screenshot index](docs/SCREENSHOTS.md) ·
[Release-channel integrity](docs/build/release-channel-integrity.md)

**[Download the latest Windows x64 MSI](https://github.com/Ding-Ding-Projects/libreoffice-material/releases/latest/download/LibreOfficeMaterial-Windows-x64.msi)** ·
[Release details](https://github.com/Ding-Ding-Projects/libreoffice-material/releases/tag/windows-msi-132-1-90e5ea4f1e)

The repaired Latest route returned HTTP 200 at the expected MSI length on
2026-07-26. The three old-policy runs were cancelled and the route was rechecked
after their cancellation; the ancestry-guarded publisher subsequently advanced
Latest through successful MSI-132.

## What is true today

| Area | State | Evidence |
| --- | --- | --- |
| LibreOffice source baseline | Imported | This repository's initial tree matches upstream commit `63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21` |
| Material design direction | Initial specification | [`MATERIAL_DESIGN.md`](MATERIAL_DESIGN.md) |
| Material VCL implementation | Tenth milestone plus a native-test-backed Start Center follow-up | Light/dark profile routing, complete semantic `StyleSettings` color mapping, native-preserving type roles, semantic shape/metric roles, full-track progress and value-sensitive level indicators, native outlined frames and net-less tree connectors, disabled-affordance state completeness, strict source validation, high-contrast fallback, shared renderer fixes, and Start Center source changes are present. The standard `suggested-action` UI class reaches `PushButton::setAction(true)` through `VclBuilder`, selecting the existing Material `extra="action"` states. Exact source `393263ad9` removes the bottom Donate action and leaves Help/Extensions in the footer; its focused 6-test validator, VS 2026 product build, native regression phase, MSI extraction, light UI smoke, and bounded accessibility capture pass |
| Whole-suite implementation | Incomplete | Phased work remains in [`ROADMAP.md`](ROADMAP.md); the 105-row [`Windows UI inventory`](docs/WINDOWS_UI_INVENTORY.md) records the owner, current evidence, missing gates, and stable acceptance IDs for every named Windows surface |
| Canonical rewrite coverage | Contracted; implementation in progress | The operator-provided design ZIP is pinned by hash in the [`Windows rewrite contract`](docs/design/00-windows-rewrite-contract.md). Its eleven surfaces govern the native Windows rewrite. Fail-closed registries currently track all 599 top-level LibreOffice dialog roots (with explicit modal exclusions for input/destructive/credential/security prompts), 30 audited shipping text-query fields, a 1271-surface UI-closure ledger, dialog anatomy, eight routed notification producers, Impress/Draw surfaces, and the wave-2 shell/navigation contracts. Sixteen of the 30 search fields are source-integrated with the shared adjacent regex builder and 14 carry documented architectural gaps. The document Find toolbar now owns a real adjacent builder, validates ICU state, synchronizes Match Case, and hands effective strings/algorithms into `.uno:ExecuteSearch`; its old empty hidden label is gone. The Windows Installer templates now carry deterministic local-token Material branding with fourteen lifecycle and three safe-decision table contracts while preserving OS ownership. Active/deactive frame slots now reach VCL floating title bands and Windows DWM caption/border/text colors, with forced colors and all OS frame behavior preserved. The 2026-07-31 slices also add Material inset grids plus ordered, bounded, or exact-occurrence C++ page-host proof for twenty-one runtime-composed dialog shells. A hash-locked composition contract now owns 195 audited runtime/modeless/lifecycle dialogs and host/atomic fragments: 184 retain prior adversarial `blocked-confirmed` evidence and 11 were re-audited from current source, with every resource tied to the globally activated Material renderer without fake labels, changed modality, or broken host geometry. The shared runtime wizard consumes token-derived page spacing and marks exactly Next/Finish as Material forward actions. Every `.ui`-backed family is complete. A fail-closed ownership contract retains only updater lifecycle and Writer canvas as still-unimplemented. Immutable title-bar source evidence raises the commit-auditable headline to 99.84% (1269/1271), with 2 pending. These are source/static/build-free facts; native and runtime proof remain separate gates. |
| Verified UI screenshots | 9 canonical Start Center captures: 3 each in light, dark, and forced high contrast | Exact build `393263ad9` supplies Help/Extensions-only Home/focus/Templates trios in [`light`](docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/), [`dark`](docs/evidence/runs/20260720-144200-393263ad92-windows-headless-dark/), and [`forced high contrast`](docs/evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/). Every current canonical screenshot omits the retired footer Donate control. Earlier runs remain historical proof; scaling, accelerated rendering, localization, and suite surfaces remain open |
| Headless harness | Appearance smoke accepted; fresh/legacy no-nag runner source-ready | The sibling low-level driver launched the exact MSI payload on run-scoped off-screen desktops, resolved stable runtime ownership, captured nine canonical states, drove background pointer and Tab input in every appearance profile, collected nine bounded UNO trees with no collector errors, shut down normally, and left zero matching processes/windows. A dedicated blank-Writer runner now encodes fresh/legacy profiles, suppression-free launch, batch-safe profile URIs, inherited crash-dump neutralization, exact total-window/PID/HWND/thread/DPI polling, dedicated-listener cleanup, and independent screenshot/UNO deny checks; it has not produced runtime evidence yet. All accepted canonical runs used dedicated same-token MCP sessions so UNO and the GUI shared the same integrity boundary; see [`docs/HEADLESS_UI_EVIDENCE.md`](docs/HEADLESS_UI_EVIDENCE.md) |
| Interactive design reference | Published mockup | [`site/prototype.html`](site/prototype.html) — all 11 suite surfaces, customizable bottom-right dialog/notification forms, bulk manager, recoverable local Git-style ledger, and one documented advanced regex builder shared by all five prototype search surfaces; guarded by [`bin/validate-prototype.mjs`](bin/validate-prototype.mjs) (9/9) and the `prototype-check` CI |
| Windows updater | Protected staging and no-restart source regressions pass; end-user flow not yet exercised | Windows-only update source reads the exact GitHub Latest XML asset, rejects untrusted or legacy state, verifies the canonical MSI metadata and bytes, stages through protected LocalAppData, and requires default-No consent before a visible install. Current source launches a major update with exactly `/i`, the staged MSI, `REBOOT=ReallySuppress`, and `MSIRESTARTMANAGERCONTROL=DisableShutdown`; repair-only `REINSTALL` properties are excluded. Its regression suite covers this four-argument vector, exclusive `CREATE_NEW` staging, the SYSTEM/Administrators/Owner Rights DACL, and a retained read lock that rejects write/delete opens. Download/consent/visible-launch and real MSI lifecycle proof remain pending; see [Privacy](PRIVACY.md) |
| Installer / release | MSI-132 is Latest; further complete-type correction rerun pending | The one-time repair restored `windows-msi-123-1-952090ce26` at `952090ce2` as Latest with exactly four assets, and canonical unauthenticated MSI/XML/checksum routes returned HTTP 200 with 197,111,808/960/103-byte lengths. The serialized ancestry-guarded publisher has since advanced Latest to `windows-msi-132-1-90e5ea4f1e` at `90e5ea4f1e`, also with four assets. Source releases are non-Latest; the Windows UI contract excludes release-tag pushes; and CI enforces fleet/release-channel closure. Three legacy unguarded MSI runs were cancelled and Latest was rechecked. Source run `30214506688` verified the exact-tag preflight; initial MSI run `30214506398` exposed GitHub's 21,000-character expression limit before job creation, and current source removes inline expressions from that 23 KB publish body. The source workflow has published at least 21 packages, but the packaged build-from-source script remains unverified end to end. MSI-123 remains historical build evidence for Windows-only stages 4+5, restored document-tab Stage 3, and UI scale; run `30427865981` compile-confirmed the earlier `MapUnit` fix, while the modified document-tab owner now awaits an exact-SHA rerun of its complete-type correction. Tabs remain runtime-unverified and scale remains stored-only. See [release-channel integrity](docs/build/release-channel-integrity.md). |

This table is deliberately conservative. A roadmap item changes state only when
its code, build result, interaction checks, and committed visual evidence agree.

## Running Windows app — exact-source VS 2026/MSI evidence

<p align="center">
  <a href="docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-light.png"><img src="docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-light.png" alt="Exact-build LibreOfficeDev light Start Center with Help and Extensions only in the footer" width="32%"></a>
  <a href="docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-light-keyboard-focus.png"><img src="docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-light-keyboard-focus.png" alt="Exact-build LibreOfficeDev light Start Center with a visible keyboard focus ring on Open File and no footer Donate button" width="32%"></a>
  <a href="docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-templates-light.png"><img src="docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/screenshots/start-center-templates-light.png" alt="Exact-build LibreOfficeDev light Start Center Templates gallery with Help and Extensions only in the footer" width="32%"></a>
</p>

<p align="center">
  <a href="docs/evidence/runs/20260720-144200-393263ad92-windows-headless-dark/screenshots/start-center-dark-keyboard-focus.png"><img src="docs/evidence/runs/20260720-144200-393263ad92-windows-headless-dark/screenshots/start-center-dark-keyboard-focus.png" alt="Exact-build LibreOfficeDev dark Start Center with visible keyboard focus and no footer Donate button" width="49%"></a>
  <a href="docs/evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/screenshots/start-center-highcontrast-keyboard-focus.png"><img src="docs/evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/screenshots/start-center-highcontrast-keyboard-focus.png" alt="Exact-build LibreOfficeDev forced-high-contrast Start Center with visible keyboard focus and no footer Donate button" width="49%"></a>
</p>

These are unedited `1920×1117` captures of actual Windows binaries. The light
trio comes from the MSI built at exact source commit `393263ad924eae8d64b4f9a35bd6486ef83578fc`
and visibly proves the Help/Extensions-only footer. The dark and
forced-high-contrast trios come from that same exact build and prove the same
footer contract. Each run used the Material
file-widget opt-in and software-raster fallback because the default-GPU
`PrintWindow` path produced a preserved blank capture. The canonical light run proves
stable launch, visible Start Center rendering, one background Tab transition,
and background navigation to Templates. Its three nonempty bounded UNO trees
contain 93/46, 93/46, and 108/61 total/visible nodes with no collector errors or
partial capture; `Open File` is the single `FOCUSED` node at the focus checkpoint.
It also proves normal shutdown and clean desktop/driver disposal. The dark and
forced-high-contrast runs repeated Home/focus/Templates and passed the same
cleanup gates; their [dark manifest](docs/evidence/runs/20260720-144200-393263ad92-windows-headless-dark/manifest.json)
and [high-contrast manifest](docs/evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/manifest.json)
bind every PNG to its tree. This still does not prove accelerated rendering,
scaling, localization, updater behavior, or the whole-suite matrix. It also does
not execute MSI install, repair, upgrade, uninstall, or restart-suppression
lifecycle scenarios. See the
[canonical light manifest](docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/manifest.json),
[results](docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/results.json),
and [screenshot registry](docs/SCREENSHOTS.md). The canonical image SHA-256
values are `c339a8516ca84489f3a96b53cf63b5e448692cc327c3a7683622d2fa64f5ee84`
for Home/Recent Documents, `b799b696902744cbb80be340c6319cfa899308031d019bddfa6cd06d2476427b`
for keyboard focus, and
`11e3762201ee5b8e516a4cd32b94092491269e1c9415d4d8c181feaa97fc759c`
for Templates. The former canonical corrected light pair under
[`20260720-022159-fbba560e27-vs2026-msi-raster-restart-suppression`](docs/evidence/runs/20260720-022159-fbba560e27-vs2026-msi-raster-restart-suppression/)
and the earlier accepted `577059e274` software-raster pair remain historical proof.

## Screenshots

Every image in this section is a **genuine capture from release
[`windows-msi-89-1-705cf7ff4b`](https://github.com/codingmachineedge/libreoffice-material/releases/tag/windows-msi-89-1-705cf7ff4b)**
— the shipped, unsigned Windows x64 MSI in which Material activation is
unconditional. Nothing here is a mockup, a prototype render, or an edited image.
This is the first genuine visual coverage of the Material rewrite across the
whole suite.

**Capture method (applies to every image):** each screenshot is an unedited
per-window `PrintWindow` capture taken on an **off-screen** virtual desktop from
the administratively **extracted release payload** (`program/soffice.exe`),
driven by the sibling `lowlevel-computer-use-mcp` harness. The **per-image
SHA-256**, the run or desktop id, and the visual-verification result are recorded
in
[`docs/screenshots/genuine/PROVENANCE.json`](docs/screenshots/genuine/PROVENANCE.json);
the Start Center trio additionally carries a schema-v2 evidence-run manifest
under [`docs/evidence/runs/`](docs/evidence/runs/). Any surface that could not be
captured is listed as **capture pending** rather than substituted with a mock —
none are pending in this set.

The captures show Material chrome — the redesigned Start Center, rounded pill
dropdowns and buttons, purple accents, sidebar accent glyphs, and left-rail
tabbed dialogs — over LibreOffice's unchanged document canvases and plain menu
text. A specific per-surface Material-vs-stock review is in
[`HANDOFF.md`](HANDOFF.md).

### Start Center

| Home — light | Home — dark | Home — forced high contrast |
| --- | --- | --- |
| <a href="docs/screenshots/genuine/start-center-light.png"><img src="docs/screenshots/genuine/start-center-light.png" alt="Material Start Center, light theme" width="250"></a> | <a href="docs/screenshots/genuine/start-center-dark.png"><img src="docs/screenshots/genuine/start-center-dark.png" alt="Material Start Center, dark theme" width="250"></a> | <a href="docs/screenshots/genuine/start-center-highcontrast.png"><img src="docs/screenshots/genuine/start-center-highcontrast.png" alt="Material Start Center, forced high contrast" width="250"></a> |

A visible keyboard-focus state and a Templates-navigation state, both light, are
also registered in [`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md).

### Applications

Each row is one application, captured light and dark as shipped.

| Application | Light | Dark |
| --- | --- | --- |
| **Writer** — blank document | <a href="docs/screenshots/genuine/writer-light.png"><img src="docs/screenshots/genuine/writer-light.png" alt="Material Writer, light" width="300"></a> | <a href="docs/screenshots/genuine/writer-dark.png"><img src="docs/screenshots/genuine/writer-dark.png" alt="Material Writer, dark" width="300"></a> |
| **Calc** — blank spreadsheet | <a href="docs/screenshots/genuine/calc-light.png"><img src="docs/screenshots/genuine/calc-light.png" alt="Material Calc, light" width="300"></a> | <a href="docs/screenshots/genuine/calc-dark.png"><img src="docs/screenshots/genuine/calc-dark.png" alt="Material Calc, dark" width="300"></a> |
| **Impress** — new presentation | <a href="docs/screenshots/genuine/impress-light.png"><img src="docs/screenshots/genuine/impress-light.png" alt="Material Impress, light" width="300"></a> | <a href="docs/screenshots/genuine/impress-dark.png"><img src="docs/screenshots/genuine/impress-dark.png" alt="Material Impress, dark" width="300"></a> |
| **Draw** — blank drawing | <a href="docs/screenshots/genuine/draw-light.png"><img src="docs/screenshots/genuine/draw-light.png" alt="Material Draw, light" width="300"></a> | <a href="docs/screenshots/genuine/draw-dark.png"><img src="docs/screenshots/genuine/draw-dark.png" alt="Material Draw, dark" width="300"></a> |
| **Math** — formula editor | <a href="docs/screenshots/genuine/math-light.png"><img src="docs/screenshots/genuine/math-light.png" alt="Material Math, light" width="300"></a> | <a href="docs/screenshots/genuine/math-dark.png"><img src="docs/screenshots/genuine/math-dark.png" alt="Material Math, dark" width="300"></a> |
| **Base** — Database Wizard | <a href="docs/screenshots/genuine/base-light.png"><img src="docs/screenshots/genuine/base-light.png" alt="Material Base Database Wizard, light" width="300"></a> | <a href="docs/screenshots/genuine/base-dark.png"><img src="docs/screenshots/genuine/base-dark.png" alt="Material Base Database Wizard, dark" width="300"></a> |

### Dialogs

Opened in a Writer host via UNO `.uno:` dispatch and captured, then dismissed
with Escape — none was confirmed, so nothing was printed, exported, or saved, and
no database was created.

| | |
| --- | --- |
| **Find & Replace** (light)<br><a href="docs/screenshots/genuine/find-replace-light.png"><img src="docs/screenshots/genuine/find-replace-light.png" alt="Material Find and Replace dialog, light" width="330"></a> | **Print** (light)<br><a href="docs/screenshots/genuine/print-light.png"><img src="docs/screenshots/genuine/print-light.png" alt="Material Print dialog, light" width="330"></a> |
| **Export as PDF — PDF Options** (light)<br><a href="docs/screenshots/genuine/pdf-export-light.png"><img src="docs/screenshots/genuine/pdf-export-light.png" alt="Material PDF Options dialog, light" width="330"></a> | **Tools &gt; Options** (light)<br><a href="docs/screenshots/genuine/options-light.png"><img src="docs/screenshots/genuine/options-light.png" alt="Material Options dialog, light" width="330"></a> |
| **File &gt; Properties — Document Properties** (light)<br><a href="docs/screenshots/genuine/document-properties-light.png"><img src="docs/screenshots/genuine/document-properties-light.png" alt="Material Document Properties dialog, light" width="330"></a> | **Template Manager** (light)<br><a href="docs/screenshots/genuine/template-manager-light.png"><img src="docs/screenshots/genuine/template-manager-light.png" alt="Material Template Manager, light" width="330"></a> |

## Material VCL source milestones

The implementation is intentionally opt-in and shared-layer first. The current
source includes:

- a packaged `material/definition.xml` file-widget theme with matching light and
  dark palettes of 23 semantic color roles each, 79 definition-backed parts,
  and 205 component states;
- eight semantic corner roles resolved order-independently by the native XML
  reader into both existing rectangle radius axes; all 159 rounded Material
  rectangles use one named role while the 11 square rectangles remain
  attribute-free, and legacy numeric `rx`/`ry` definitions stay supported;
- 15 semantic native integer metric roles for strokes, control dimensions,
  spacing, tab/title heights, and list-preview geometry; 346 integer values now
  resolve through those roles—307 drawing strokes, 34 explicit part
  dimensions/margins, and 5 numeric settings—while the existing native action,
  part, and settings representations remain unchanged;
- all 684 normalized `x1`/`y1`/`x2`/`y2` coordinate values remain local
  literals because they describe proportional component geometry rather than
  integer metrics; typography scaling and rectangle corners retain their
  separate semantic contracts;
- an exact 72-slot Material style contract that closes the ten previously
  native-dependent accent, list-box collection, alternating-row, warning, and
  error colors; these newer reader fields remain optional so partial legacy and
  out-of-tree file themes preserve native values when a role is omitted;
- typed `body`, `label`, and `title` roles with bounded relative scaling and a
  strict minimum-weight vocabulary; each role copies the captured platform font,
  applies the declared nonshrinking height scale, and only raises weight to the
  declared minimum, so family, style, charset, language, pitch, orientation,
  width, and icon fonts remain native;
- order-independent color, shape, and metric `@token` resolution and strict
  rejection of malformed colors, shapes, or metrics, invalid or duplicate token
  sections, mismatched palette schemas, unknown references, ambiguous radius
  declarations, and unknown or duplicate control parts; older bundled and
  out-of-tree definitions retain their existing literal numeric geometry path;
- selection through `VCL_FILE_WIDGET_THEME`, with a restricted safe theme name,
  shared immutable definitions, and a mutex-protected cache keyed by theme and
  resolved light/dark scheme; a failed request attempts `online`, which is not
  packaged in this imported desktop tree, and otherwise leaves the file theme
  inactive;
- native settings collected and captured before the opt-in Material pass, with
  the resolved precedence high contrast over dark over light; high contrast
  restores the pre-Material style/framework baseline and delegates to native or
  generic forced-color drawing;
- runtime profile transitions recompute native-focus suppression for buttons,
  tabs, and list boxes so generic fallback retains a visible VCL focus
  indicator; Qt proxy styles preserve their high-contrast signal, and headless
  VCL honors an explicitly selected dark appearance;
- definition-aware support reporting so parts absent from the selected file
  theme stay on their existing fallback path;
- expanded mixed, disabled, hover, pressed, focus, selected, flat-button,
  toolbar, list-node, edit, scrollbar, slider, tab, menu, progress, and
  standalone vertical/horizontal spin-button coverage;
- native Material progress and level indicators that draw an optional full
  track before the clipped fill; level fills retain the existing four value
  bands through `critical`, `low`, `medium`, and `high` semantic states, while
  legacy file themes with only an `Entire` fill keep their prior path;
- a native Material outlined frame (`ControlType::Frame`/`Border`) that reuses
  the shared container outline, surface-container fill, thin stroke, and
  container corner roles; the renderer now reports a native frame region so
  `decoview` issues the file-definition border draw, and a net-less Material
  tree (`ControlType::ListNet`/`Entire`) that is supported yet draws nothing so
  VCL suppresses its own connector nets for a flatter tree;
- disabled-affordance state completeness for three controls that previously
  collapsed a disabled tuple onto a generic state: a dimmed `SubmenuArrow` when a
  submenu parent is disabled, a dimmed-but-checked toolbar button
  (`enabled="false"` + `button-value="true"`), and a disabled-but-selected tab
  (`Entire` and `MenuItem`) so a disabled tab control still identifies its
  current page;
- shared renderer corrections for composite combo geometry and RTL placement,
  toolbar grips, standalone spin geometry and direction, native control regions,
  slider sizing, and raw graphics-state invalidation;
- a standalone source validator for exact color, shape, metric, 72-slot style,
  and typography contracts, required parts and states, light/dark schema parity,
  unused tokens, native font/geometry-preservation invariants, and selected
  WCAG contrast pairs—including list selection and warning/error feedback—plus
  reader, XML-walker, and headless draw C++ coverage with negative XML fixtures;
- Start Center spacing, a Home header/subtitle, surface roles, and recent/template
  text and fill colors derived from VCL style settings; `open_all` now uses the
  standard `suggested-action` class, which VCL preserves as the push-button
  action state used by the existing Material `extra="action"` definitions.

The local static validator passes with 2 schemes, 23 semantic color tokens per
scheme, 3 semantic typography roles, 8 semantic shape tokens, 15 semantic
metric roles, 72 style slots, 79 parts, and 205 states.
The static validator remains source validation, but the five required native
C++ targets—including the focused `vcl_treeview` builder fixture—passed in the
historical pre-Windows-only Linux run, Windows Actions, and the exact-source
local VS 2026 build. The later Windows-only tree completed MSI-123 at
`952090ce2`. A
real `soffice` Start Center smoke has now passed Home/focus/Templates in all
three appearance profiles; no surface is yet verified Material-complete, and the broader
appearance, input, localization, suite, and updater matrix remains open.
Controls whose current file-widget geometry cannot preserve native semantics
continue through LibreOffice's existing fallback.

The metric roles preserve the current integer values and existing downstream
native conversions exactly. This token layer adds **no** density profile or new
DPI-aware, `dp`, fractional-scale, or touch-target policy; those require later
renderer and runtime work backed by real builds and captures.

On Windows this fork enables Material **unconditionally**. Upstream reaches the
file-widget renderer only when `VCL_DRAW_WIDGETS_FROM_FILE` is set and selects
the shared theme only when `VCL_FILE_WIDGET_THEME` equals `material`; because
nothing in the shipped product set either variable, the packaged Material assets
shipped **dormant** in every prior MSI. Per operator directive — Material Design
is the product — `soffice_main()` (`desktop/source/app/sofficemain.cxx`) now
forces both variables on **every** Windows launch, under `#ifdef _WIN32`, before
any consumer reads them, so a stock launch always renders Material:

- there is **no opt-out variable** (the former `LIBREOFFICE_MATERIAL_THEME`
  escape is removed) and **no user override** — both writes run unconditionally,
  so stock native widget rendering is not a supported mode on Windows;
- the only runtime path that bypasses Material is the system
  forced-colors / high-contrast precedence inside VCL, which stays as an
  accessibility requirement, not an opt-out.

The two environment variables are useful only to **preview Material on an older,
pre-activation build** (one published before this change) — set them by hand
before launching that older binary:

```powershell
$env:VCL_DRAW_WIDGETS_FROM_FILE = "1"
$env:VCL_FILE_WIDGET_THEME = "material"
```

On any build that includes this change they are already set for you and need no
manual step. This unconditional switch is **source-implemented wiring only**,
locked by the `material-default-activation` source contract
(`bin/check-material-default-activation.py`), which fails closed on a moved,
dropped, or drifted block and on any reintroduced opt-out token or `getenv`
override conditional; `runtime_verified` stays `false`. Its presence does not
prove that every visible control used the file theme — the first release built
after this change is the first shipped binary with Material active by default,
and no pixel evidence exists for it yet. The
`vcl_widget_definition_reader_test` and `vcl_file_definition_widget_draw_test`
targets passed in the hosted pre-Windows-only runs and the local VS 2026 build.
The exact-source MSI payload supplied the accepted `soffice` run linked
above, which had both variables set by hand.

## Windows updater source milestone

The Windows package source now enables LibreOffice's consent-based updater
against one exact feed:
`https://github.com/Ding-Ding-Projects/libreoffice-material/releases/latest/download/windows-update-manifest.xml`.
GitHub's Latest route supplies the workflow-generated XML for the normal stable
release. After the pre-fix source-channel incident, the 2026-07-26 repair
restored MSI-123 and the canonical XML route returned HTTP 200 at 960 bytes;
the three legacy publisher runs were cancelled and that route was rechecked.
The parser accepts one
Windows x64 MSI only when its safe release tag,
tag-derived GitHub URL, canonical `LibreOfficeMaterial-Windows-x64.msi` name,
`application/x-msi` MIME type, positive byte count, and lowercase SHA-256 all
match. Legacy or malformed persisted update state is discarded before a resume.

After download, the complete file is checked by size and SHA-256. A confirmed
install copies those bytes with `CREATE_NEW` into a protected, per-run
LocalAppData directory whose DACL is limited to the user, Administrators, and
SYSTEM; it verifies the staged copy and retains a final read lock that excludes
write/delete replacement. The only install action is a visible Windows
Installer launch after an explicit confirmation whose default is **No**. There
is no silent install path, and the launch passes `REBOOT=ReallySuppress` so it
cannot request or force a Windows restart. It also passes
`MSIRESTARTMANAGERCONTROL=DisableShutdown`, and it deliberately omits
`REINSTALL=ALL` and `REINSTALLMODE=vomus` because those maintenance properties
prevent a newly generated ProductCode from selecting features during a major
upgrade.

Automatic update checking is enabled by default on a weekly interval. Automatic
download is disabled by default, and download and installation remain user
opt-in. Network and data-handling details are in [`PRIVACY.md`](PRIVACY.md).
For runtime accessibility verification, the repository now includes a bounded,
read-only UNO tree collector that runs only with the matching built Python
runtime and is paired with off-screen screenshots; it records roles, names,
states, and bounds without extracting document text or driving the UI.
The Start Center headless UI and bounded UNO-tree collection now have runtime
proof, but they do not constitute a full accessibility audit and do not exercise
the updater. A launch-site audit after publishing the older `577059e274` MSI
found that only four of the command builder's five generated arguments reached
`osl_executeProcess`, dropping `REBOOT=ReallySuppress`. Commit `fbba560e2`
replaced that fixed four-element list with an array sized from the command and
forwarded all five entries. The third Sandbox diagnostic later proved that two
of those entries, `REINSTALL=ALL` and `REINSTALLMODE=vomus`, were repair-only:
the corrected MSI found the old ProductCode but selected no features for its
new ProductCode. Current source now forwards the exact four major-update entries
and retains the reinstall properties only in the harness's explicit repair.
`CppunitTest_extensions_test_update`, the incremental
full product build, and MSI creation passed with Visual Studio 2026. The corrected
unsigned MSI is 199,688,192 bytes with SHA-256 `180e511c…afeea`; administrative
extraction returned `0` with 4,885 files and 603,901,200 bytes, and the extracted
updater DLL exactly matches the built DLL at SHA-256 `32f80a…46a3`. Its corrected
extracted runtime passed the canonical light Start Center UI/UNO smoke. The
download/protected-stage/consent/install flow, MSI install/repair/upgrade/
restart-suppression lifecycle, and broader UI/accessibility matrix are still pending.

The stable release workflow starts on every push to `main` (manual dispatch
remains available), creates a draft release, uploads the validated MSI and
update metadata directly to that release, and checks the exact target, asset
names, upload states, sizes, and digests. All publisher-capable main runs now
share one non-cancelling concurrency group; non-main manual diagnostics use a
run-unique group and cannot occupy the stable queue. A verified draft is promoted to Latest only
when its exact commit is identical to or descends from the current stable MSI
commit; an older, divergent, or ancestry-unprovable build becomes a normal
historical non-Latest release. A successful promotion still checks the public
Latest feed and all four cache-busted assets. Only diagnostics use an Actions
artifact, and a failed draft is cleaned up. Hosted run `30214506398` exposed a
workflow-compile limit before any job or release existed: inline `${{ ... }}`
substitutions made the 23 KB publish body exceed GitHub's 21,000-character
expression cap. Current source reads the standard `GITHUB_*` environment
variables instead and guards that constraint with a mutation test; its first
hosted run is pending. The independently staged corrected release
[`windows-msi-local-20260720-fbba560e2`](https://github.com/Ding-Ding-Projects/libreoffice-material/releases/tag/windows-msi-local-20260720-fbba560e2)
was verified as the normal public, non-prerelease Latest release before the
2026-07-26 source-channel incident. It targets exact source
`fbba560e27db26de605c40aa237c554c1f0744b1` and has exactly four assets.
Cache-busted unauthenticated Latest downloads then matched the release assets exactly:
the 199,688,192-byte MSI is
`180e511c065f3e21cd9e4fd0abe31f8886b0cc5ce5ce27a48f2890f83d1afeea`;
the 102-byte checksum sidecar is
`e82f022d06665a165b8d0145acac0aae7b39cd9f8b9cbd0f7a1cfa1105021b9e`;
the 1,011-byte JSON manifest is
`12e6495e5d5051657dd99e6c0afc6d61941144c1bcde5f792f09a9949bea0fc1`;
and the 972-byte XML manifest is
`b686d9e9641360c3962bc27b8b6517b9a76c14c06cd50efbcbcfe485724eab72`.
The immutable tag and bytes remain evidence. The repaired mutable Latest route
now points to MSI-123 and its canonical public downloads returned HTTP 200 at
the expected lengths. Source-installer releases now use `--latest=false`, fail
closed on exact-tag lookup, and check the canonical MSI both before and after
publication; the three legacy unguarded runs were cancelled and the repaired
route was rechecked. See
[`docs/build/release-channel-integrity.md`](docs/build/release-channel-integrity.md).
Hosted workflow run `29720519794` later completed unsuccessfully and remains
historical workflow diagnosis, not release evidence.

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

The current Windows rewrite is governed by the
[`canonical archive contract`](docs/design/00-windows-rewrite-contract.md).
Later operator requirements intentionally extend it with customizable
bottom-right notification forms, local Git-backed notification undo and bulk
management, and a documented advanced regex builder beside every app-owned
search field. Promotional and recurring nags are removed while safety-critical
confirmations remain. These requirements are tracked as source and coverage
work until an exact build supplies interaction, accessibility, and visual proof.

The first native dialog slice now hooks the shared VCL final-`InitShow` path on
Windows and moves `Dialog` windows to the lower-right of the visible owner/work
area after derived layout completes. A 16 px Material inset is bounded when
space is tight, decorated extents are clamped to the work area, and
LibreOfficeKit plus non-Windows paths retain their existing geometry. The
source validator and eleven mutation regressions pass. This does not yet add
the notification form host, event routing, customization UI, stacking, or
compiled/headless proof.

The notification storage/service foundation now persists redacted structured
records in a genuine local bare Git repository with fixed `main`, durable
same-process plus OS-held cross-process exclusion, CAS ref updates, atomic bulk
state transitions, recoverable tombstones,
pin/deduplicate/purge/empty-trash maintenance, bounded parentless checkpoints,
history enumeration, and inverse-commit undo. Metadata-only persistence is the
default, repository operations are explicitly worker-thread-only, and a durable
compaction gate blocks further user commits after a prune failure; retries reuse
the installed checkpoint without growing objects or advancing `main`. A lazy
application-owned `NotificationCenterService` now constructs, uses, and destroys
that store on one serialized worker, returns immutable generation-stamped
snapshots, refreshes after CAS conflicts, drains accepted mutations at shutdown,
and marshals profile completions through a self-retaining VCL event queue. Worker
admission closes before callback cancellation, repository-test dispatch must
transfer completions off-worker, and the stable joined worker owner is retained
through repeated shutdown. A typed adapter reads and writes every generated
`Office.UI.NotificationCenter` preference. Twenty-one native CppUnit cases are
wired and all 24 source mutation tests pass.
The service architecture is recorded in
[`docs/design/02-notification-service-architecture.md`](docs/design/02-notification-service-architecture.md).
No dialog producer, visible notification form/manager, stack, compiled service
test, or runtime behavior is claimed yet.

The shared native regex foundation now uses LibreOffice’s ICU-backed
`SearchOptions2`/`TextSearch` semantics for literal and regular-expression
search, exposes `i/g/m/s`, reports syntax errors, bounds zero-width live-preview
matches, and preserves LibreOffice's consumer rule that skips internal
zero-length matches while accepting terminal anchors. Its full
Build/Test/Reference/Examples UI is a
non-modal `GtkPopover` anchored directly to the adjacent builder button, so it
does not inherit bottom-right dialog placement. All pages scroll within the
bounded surface, backend-independent close handling cancels hidden preview
work, and the Qt popover path clamps to the monitor work area. Fourteen native
CppUnit cases are wired (not locally compiled in the current checkout).
The separate 30-field coverage ledger records 16 source integrations and 14
documented gaps. Its parameterized source validator and 100 mutation regressions
guard callback ownership, mode/case synchronization, bounded validation,
effective-pattern routing, global-result semantics, repeat-search metadata, and
dead-route bypasses. The Find toolbar additionally has a ten-mutation focused
composition contract covering its UNO handoff and native Match Case/Find All
ownership. Calc Go to Sheet preserves its legacy
`OUString::indexOf` default; Forms, Find & Replace, and Writer Quick Find now
feed the shared state into their real LibreOffice matchers. Exact-build
compilation and runtime interaction proof remain open.

Automatic donation/Get Involved/What’s New promotion, first-start Welcome,
Tip of the Day scheduling, Windows file-association solicitation, AutoCorrect
explanation, and crash-report submission prompts are now removed in source.
Their dead controllers, factories, configuration keys, startup checkboxes, and
misleading crash-report opt-in are removed too. Explicit Tip, What’s New, and
file-association actions remain, and a fail-closed contract guards sixteen
recovery, Safe Mode, compatibility, security, credential, read-only,
runtime-suppression, and manual-action markers. Its 35 forbidden-marker checks,
16 retained safeguards, and four mutation regressions pass.

The source-controlled
[`Run-Windows-NoNag-Headless-Smoke.ps1`](bin/Run-Windows-NoNag-Headless-Smoke.ps1)
now provides the missing exact-build test path. It launches a blank Writer on a
dedicated off-screen desktop with either a genuinely empty profile or a fixed
legacy profile whose former Welcome, tip, promotion, association, AutoCorrect,
and crash-report triggers are deliberately enabled. Both modes reject
UI-suppression launch switches, bind `program/version.ini` to the full source
commit, poll every payload-owned top-level window for at least 15 seconds, and
bind a nonblank screenshot to a complete UNO accessibility tree. The retained
safety/manual list is separate from the former-nag denylist. Static and mutation
validation pass, but this harness has not yet been run against a newly built
payload, so fresh/legacy screenshots and runtime acceptance remain pending.

An administratively extracted MSI is not registered under `HKLM`; therefore an
absence of the old automatic file-association dialog in an extracted payload
cannot prove that registry-gated branch. That one check needs an MSI-installed
disposable Windows Sandbox or VM. The explicit Options action remains guarded
by the source contract.

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

The five screenshots above were captured from exact-source Windows builds of this
repository and registered with their commit, environment, scenarios, hashes,
and review. Remaining empty cards on the project site are **evidence slots**,
not mockups or generated UI claims.

The interactive reference at
[`site/prototype.html`](site/prototype.html) is the intended Material look and
interaction drawn as a self-contained, dependency-free HTML page (system fonts,
inline SVG icons, no web fonts or CDN). Every search bar in it carries a full
regex builder — token palette, `i`/`g`/`m`/`s` flags, live validity and match
count — filtering the real Start Center, command-catalog, and gallery data, and
the Dialogs surface includes a working Find & Replace that runs the same builder
over live document text. The token contract behind it is documented in
[`docs/DESIGN_TOKENS.md`](docs/DESIGN_TOKENS.md), and
[`bin/validate-prototype.mjs`](bin/validate-prototype.mjs) is a dependency-free
Node check of the prototype's self-containment, tokens, icons, and regex engine
(`node bin/validate-prototype.mjs`). Every color, corner, and metric mirrors
the semantic roles in
[`vcl/uiconfig/theme_definitions/material/definition.xml`](vcl/uiconfig/theme_definitions/material/definition.xml).
It is a design specification aid, **not** a screenshot of a compiled LibreOffice
and **not** build evidence; current capture status is tracked only in
[`docs/SCREENSHOTS.md`](docs/SCREENSHOTS.md).

The verification driver is the sibling
[`lowlevel-computer-use-mcp`](https://github.com/codingmachineedge/lowlevel-computer-use-mcp)
project. It can launch real GUI applications on an off-screen desktop, target
windows without focusing them, and capture window images. The 2026-07-20
accepted run used clean driver commit
`beed66ca6ed2503e6170ee1e1158247f1c2f0140` to launch and inspect the exact MSI
payload without taking over the live desktop. The driver is not currently
vendored into this repository. Exact preflight facts, accepted-run boundaries,
the capture contract, and safety rules are in
[`docs/HEADLESS_UI_EVIDENCE.md`](docs/HEADLESS_UI_EVIDENCE.md).

## Building LibreOffice

This fork retains the upstream LibreOffice build chain. LibreOffice is a large,
cross-platform native project; consult The Document Foundation's current
[platform build instructions](https://wiki.documentfoundation.org/Development/How_to_build)
and the imported build files before configuring a machine.

> **Local one-click build:** [`Build-Windows.cmd`](Build-Windows.cmd) now calls
> the source-controlled bootstrapper described in
> [`docs/LOCAL_WINDOWS_BUILD.md`](docs/LOCAL_WINDOWS_BUILD.md). It provisions
> an isolated Visual Studio 2022 Build Tools profile with C++/CLI, the C++ Clang
> compiler, and Cygwin
> when needed,
> verifies it, and builds from an LF snapshot without touching this checkout.
> On 2026-07-19, this host installed the dedicated VS 2022/Cygwin profile and a
> clean local preflight passed it. The first real configure exposed a missing C++
> Clang compiler; the bootstrap now requires that component. A separate explicit
> VS 2026 run then completed from clean detached source
> `577059e2741185b512c184c64685c16d335d10ea`:
> all five required native targets, the legacy CLI payload, product build, final
> MSI, and Windows Installer administrative extraction succeeded. The extracted
> payload supplied the accepted Start Center UI and bounded UNO-tree run. The wrapper's parent
> process exited before its final dist copy/manifest step, so that wrapper is not
> claimed as an end-to-end success. Current source fixes that asynchronous
> `msiexec` race with an explicit hidden waited process. Exact implementation
> commit `7029dccf4` subsequently passed all five native targets, full product/MSI
> regeneration, administrative extraction, and final canonical staging. This
> local result complements the hosted results from before the Windows-only cut:
> Linux run `29695793821` and Windows run `29695815101` passed
> all five required native C++ targets, and the Windows run built the full
> installation set but stopped at MSI staging. Hosted run `29720519794` later
> completed unsuccessfully and is historical workflow diagnosis. A separate
> corrected normal public, non-prerelease release exists at
> `windows-msi-local-20260720-fbba560e2`; it was verified as Latest before the
> later source-channel incident and targets
> `fbba560e27db26de605c40aa237c554c1f0744b1`, and its four public assets have
> been independently downloaded and matched byte-for-byte. Its immutable assets
> remain evidence. The mutable Latest route has since been repaired to MSI-123;
> the three legacy unguarded runs were cancelled and the route was rechecked.
> Neither publication
> establishes updater-runtime or MSI lifecycle behavior.

> **Optional local VS 2026 profile:** Visual Studio 2022 remains the default
> and the profile that matches the current Windows CI workflow. To select VS
> 2026 explicitly with a verified existing installation, use a separate build
> root on the first run:
>
> ```powershell
> .\Build-Windows.cmd -VisualStudioYear 2026 -VisualStudioInstallPath 'C:\Program Files\Microsoft Visual Studio\18\Enterprise' -BuildRoot "$env:USERPROFILE\lo-material-vs2026"
> ```
>
> The supplied path is validated as the selected VS 2026 toolchain. The script
> never silently selects, repairs, or substitutes a host Visual Studio
> installation; it stops if that explicit path is incomplete. Without
> `-VisualStudioInstallPath`, the opt-in profile uses its separate dedicated
> `%ProgramData%\LibreOfficeMaterialTools\VS2026` Build Tools root. This is a
> local-build option only until the CI profile is deliberately updated. Its
> addition is now exercised by the exact-source build described above; it is not
> the hosted CI profile.
> The checker accepts VS 2022's legacy <code>Llvm\bin</code> layout and VS
> 2026's host-native <code>Llvm\x64\bin</code> layout for <code>clang-cl</code>.
> On 2026-07-19, the named VS 2026 Enterprise host passed no-bootstrap
> preflight and an isolated configure at `a6d9f9a7dbdf10c08afe2eb03239e702ec5172ef`.
> Its first native build reached third-party compilation and exposed MSVC v145's
> C++20 `mdds` conditional-`noexcept` incompatibility. The source now carries a
> narrowly scoped v145 C++20 compatibility patch. On 2026-07-20, a fresh build
> at `577059e274` completed the native targets, product, and final MSI; its
> extracted runtime passed the linked light-profile Start Center UI and bounded
> UNO-tree smoke. A later launch-site audit found that binary omitted the fifth
> generated updater argument. Commit `fbba560e2` forwards all five, including
> `REBOOT=ReallySuppress`; its focused updater target, incremental product build,
> corrected 199,688,192-byte MSI, administrative extraction, and updater-DLL hash
> match, corrected scoped headless UI/UNO rerun, and corrected normal public
> release all passed. A subsequent Sandbox log proved that its two reinstall
> properties suppress a new ProductCode's feature selection; current source
> replaces that launch vector with the four correct major-update arguments.
> MSI install/repair/upgrade/uninstall and restart-suppression lifecycle proof
> remain open. Remaining
> gates are stated in the evidence manifest.

The bootstrapper creates a clean detached LF worktree rather than normalizing
the development checkout. It checks root safety, free space, and (when Git is
available) source cleanliness before dependency installation; its isolated
Cygwin Git and Git configuration avoid a system-wide Git mutation. It is
intentionally fail-safe: it never deletes a previous build root, reboots
Windows, installs the output MSI, or silently substitutes a host Visual Studio
installation. The default remains isolated VS 2022; a host VS 2026 install is
used only when both the year and its exact path are supplied. A full successful
run removes only its verified-clean temporary source snapshot and preserves
build logs and artifacts.

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
