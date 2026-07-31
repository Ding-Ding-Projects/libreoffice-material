# LibreOffice Material roadmap

This roadmap covers a whole-GUI modernization, not a theme preview. It is
ordered so shared native primitives are proved before individual applications
diverge. Dates are intentionally omitted until build capacity and baseline
metrics are recorded.

Status vocabulary:

- **planned** — scoped but no accepted implementation evidence;
- **in progress** — implementation exists but one or more acceptance gates fail;
- **verified** — code, build, interaction, accessibility, and visual evidence all
  pass at a recorded commit;
- **blocked** — a named external dependency prevents further work.

No phase is currently marked verified.

**2026-07-31 MSI lifecycle composition:** the installer now bundles three
deterministic 24-bit branding assets generated from the local Material token
palette. A fail-closed contract follows them through Binary/Control/Dialog
tables, Segoe UI hierarchy, fourteen install/maintenance/progress/completion
stages, three safe native decisions, template copying, and the existing
lifecycle harness. Ten mutations and byte regeneration pass. Windows Installer
still owns chrome, controls, DPI, keyboard, and accessibility. The native row
is credited against immutable source commit
`3d25fea0279d9f44bc7daff7a2b329509d38f951`, raising the source headline to
**99.76% (1268/1271), 3 pending**. Real MSI lifecycle behavior remains
unverified.

**2026-07-31 native Find-toolbar implementation:** the layout-manager-owned
Find item window now has a real adjacent advanced regex builder. Validated ICU
state supplies the effective string, flags, and algorithm to the existing UNO
dispatch; the native Match Case and Find Next/Previous/All controls retain
authority. The fake empty label has been removed and its `.ui` root promoted to
the 195-resource host-composed family. The focused 10-mutation contract, shared
100-mutation integration suite, 22 coverage tests, and 143-file SVX
accessibility gate pass. Commit `5f9bc77fc35901bfe9f355c483409302bb642b34`
now supplies immutable evidence, raising the source headline to **99.69%
(1267/1271), 4 pending**. Runtime UI remains unverified.

**2026-07-31 runtime-wizard composition milestone:** the shared assistant now
uses token-derived 12 px spacing on every C++-generated page and marks exactly
Next and Finish as Material primary forward actions, without inventing static
widgets or changing response semantics. The six-mutation composition contract,
VCL accessibility gate (19 files, 0 FATALs), 57 ledger tests, and 179/179
build-free workflow closure pass. At that checkpoint the source headline was
**99.61% (1266/1271), 5 pending**; all `.ui`-backed families were complete.
Runtime UI remains unverified.

**2026-07-31 host-composed classification correction:** the 194 remaining
static blockers are now an explicit `host-composed-surface` family rather than
being forced through a complete-form predicate they cannot structurally own.
The contract locks 64 runtime/modeless/lifecycle dialog variants and 130
host/atomic fragments by surface-set digest, per-file SHA-256, live predicate
failure, root identity, marker snapshot, owner/inventory attribution, audit
provenance, and shared Material renderer dependencies. It preserves 184 prior
`blocked-confirmed` audits and 10 current-source re-audits; 12 contract
mutations, 57 ledger tests, and the 177/177 build-free workflow closure pass.
At that checkpoint the source headline advanced to **99.53% (1265/1271), 6 pending**. This is
source-composition evidence only; runtime UI remains unverified.

**2026-07-31 runtime-dialog composition milestone:** twenty-one empty-notebook
dialogs now carry real Material inset grids while their labels and page bodies
remain owned by the existing C++ controllers. A new explicit
`runtime-dialog-shell` family proves both the empty static shell and ordered
or bounded runtime page hosts, plus the exact conditional occurrence map used
by Chart Object Attributes, without weakening the ordinary dialog predicate. Twenty-three
contract mutations, 56 ledger tests, XML, dialog anatomy, accessibility-fatals,
and the 175/175 build-free workflow gate pass. At that checkpoint the source
headline advanced to **84.26% (1071/1271), 200 pending**; native runtime and pixel evidence remain
open.

**2026-07-31 native/wizard ownership contract:** five native shells and the
shared wizard shell initially received a fail-closed owner/marker contract. The
wizard has since moved to its implemented runtime-composition contract; the
ownership boundary now retains only the four pending native shells.

**2026-07-31 blocked-surface design proposal:** the six non-static pending
surfaces now have a concrete Material token/anatomy proposal in
[`docs/design/blocked-surface-material-proposal.md`](docs/design/blocked-surface-material-proposal.md).
It remains design-only until runtime contracts and Windows evidence are
available; the ledger does not award coverage for a proposal.

**2026-07-31 ledger correction:** `fielddescpanel.ui` is now explicitly
classified as a panel fragment because its C++ owner is Base's ordinary
`OChildWindow`, not the sfx2 sidebar deck. The regenerated ledger and 55-test
suite pass; the overall headline remains **82.61% (1050/1271), 221 pending**.

**2026-07-31 milestone — behavior-safe UI slice:** the existing search dialog
primary action now uses `RET_OK`, and the existing database field-description
panel has Material margins plus ellipsizing and mnemonic metadata. XML,
dialog-anatomy, accessibility-fatal, and 55 rewrite-ledger unit tests pass.
The fail-closed headline remains **82.61% (1050/1271), 221 pending** because
the runtime-composed child panel is not credited by the current ledger rule.

**2026-07-29 milestone — source bug audit and evidence correction:** a
post-pull audit closed the six product bug clusters recorded below at source
level. Notification selection now follows visible rows, Undo skips prior Undo
records, high-severity/pinned cards cannot auto-dismiss, and the overlay
re-anchors on resize. Document tabs now have frame ownership, live open/close/
title/current-frame refresh, disposed-frame pruning, robust style/config
round-tripping, and a complete appearance dialog. Persisted Material accents
now resolve through the runtime token consumer path after restart. Start Center
regex-mode synchronization and Templates filtering are wired, while AutoCorrect
search keeps section/header rows disabled and non-actionable after every
rebuild. Forms, Find & Replace, and Writer Quick Find now route `i/g/m/s`,
invalid-pattern guards, mode transitions, and repeat state to the real
LibreOffice matcher. A final adversarial pass also removed cosmetic Global
controls from the Start Center and AutoCorrect boolean filters, reapplies an
active Start Center query after recent-document maintenance reloads, prevents
docked side borders from being subtracted twice from document-tab width, and
makes notification Undo follow repository chain order across wall-clock
rollback. The fail-closed regex integration suite now has 100 regressions, and
the document-tab suite has 41.

The rewrite evaluator itself also had a fail-closed dead end: a valid historical
snapshot was retained after a still-conforming surface changed, so C4 rejected
the stale markers but `--evaluate` could not refresh them. The evaluator and
its mutation coverage now refresh such evidence. The audited headline is
**82.61% (1050/1271), 221 pending, 0 in-progress**. This corrects ten
previously over-credited surfaces; eleven rows now carry explicit regression
waivers in total. All claims in this milestone are source/static/build-free
evidence. There is no configured local LibreOffice build, so the new C++ tests,
headless interaction, pixels, accessibility, and performance remain unverified.
Exact-source MSI run
[`30423589955`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/30423589955)
provided the first hosted compiler contact for this follow-up and failed in the
first critical desktop-library link because the document-tab source used
`MapUnit::MapPoint` through a forward declaration. Current source includes the
defining `tools/mapunit.hxx` header, removes the adjacent MSVC local-shadow
warning, and has a fail-closed regression for the include. Corrective run
[`30427865981`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/30427865981)
compiled that translation unit, then failed compiling `frame2.cxx` because
`impframe.hxx` owned `VclPtr<SfxDocumentTabBar>` through only a forward
declaration. Current source makes the owning header self-contained and
regression-pins the complete-type include; a further hosted MSI rerun is
pending, so this is not yet successful native-build proof.

**2026-07-28 milestone — CI repair + provisional burn-down 73.41% → 83.24%:**
the Phase 7.5 search-bar merge had left `main` red (gla11y FATALs, illegal
interface-level `<child>` markup, registry claims with no backing C++); commit
`56d210c38` repaired all of it and produced verified-green runs of every
workflow including MSI-131. An adversarially-verified Opus wave then rewrote
127 of the 338 pending ledger surfaces (footer anatomy with C++-audited
response repairs, real label anatomy, Material content grids) and landed the
genuine `RegexSearchController` wiring for both Phase 7.5 search bars
(registries truthfully at 15/15). The 213-pending headline was the provisional
wave result; the 2026-07-29 commit-auditable evaluation above corrects it to
223. Per-surface blocked evidence remains in
`docs/design/material-rewrite-wave-2026-07-28-evidence.json`; the wave C++ is
source-implemented. Its first exact-SHA MSI compile did not clear; the
two concrete document-tab header-completeness failures are corrected and a
further rerun is pending.

**2026-07-26 milestone — Windows-only compile closure and release-channel
containment:** Windows-only stages 4+5 landed at `7874c6b85`, including removal
of the Linux installer workflow, and the resulting tree compiled in successful
MSI-123 at `952090ce2`. Restored document-tab Stage 3 (`af689a470`) and the
UI-scale control were in that build; tabs still have no runtime UI evidence,
and UI scale remains stored-only. The source-installer workflow has published
at least 21 releases, but its packaged PowerShell installer remains unverified
end to end. A pre-fix source release displaced the stable MSI from GitHub Latest and
made the public Latest MSI URL return 404. Commit `27a7c7d00` made source
releases non-Latest, excluded release tags from the Windows UI contract, and
added CI fleet-closure/release-channel guards. Current source additionally
serializes MSI publishers and permits Latest promotion only along proven commit
ancestry. The one-time remote repair restored
`windows-msi-123-1-952090ce26` at `952090ce2` as Latest with four assets; the
canonical MSI/XML/checksum routes returned HTTP 200 at
197,111,808/960/103-byte lengths. The three legacy unguarded MSI runs were
cancelled before this follow-up push and the repaired API/assets/routes were
rechecked. Initial hosted MSI run `30214506398` then failed before job creation
because inline substitutions exceeded GitHub's 21,000-character expression
limit; current source uses default `GITHUB_*` variables and pins that constraint,
so a successful post-change hosted MSI publisher run remains pending. See
[`docs/build/release-channel-integrity.md`](docs/build/release-channel-integrity.md).

The same 2026-07-26 source audit identified six product bug clusters: filtered
notification-manager selection/focus and sequential Undo; document-tab
ownership/configuration/stale-frame/schema mismatches; disconnected `i/g/m/s`
paths in Find/Replace, Forms, and Quick Find; overlay re-anchoring and unsafe
auto-dismiss; persisted accents bypassed by runtime token consumers; and Start
Center regex/Templates desynchronization. The 2026-07-29 milestone above closes
those findings in source and regression contracts only. It does not change the
older compile evidence or create native/runtime proof.

**2026-07-23 milestone — first genuine cross-suite capture:** the shipped
`windows-msi-89-1-705cf7ff4b` release binary produced the first honest Material
screenshots spanning the Start Center (light, dark, forced high contrast), all six
applications (light and dark), and six shared dialogs, captured off-screen from the
administratively extracted MSI payload with per-image SHA-256 in
[`docs/screenshots/genuine/PROVENANCE.json`](docs/screenshots/genuine/PROVENANCE.json).
This is visual evidence only — it does not by itself mark any phase verified.

**2026-07-25 milestones (status at that date; superseded above):** the Windows-only OS strip landed stages 0–3
(iOS/Android, macOS/Quartz/Aqua, Qt/KF/GTK plugin backends removed, each
Linux-CI-green; stages 4–5 held for an MSI baseline); a touchless
build-from-source installer (`bin/Install-LibreOfficeMaterial-FromSource.ps1`)
plus a fast `source-installer.yml` release channel that publishes on every push
independent of the 3h MSI; tabbed-UI stages 1–2 (frame-topness seam registry +
document-tab style schema/normalizer, tabs off by default); and a persisted
50–400% UI-scale control (refs tdf#101646, stored-value-only). The a11y build
fix that was blocking every MSI build also landed; the rewrite headline is
**73.46% (933/1270)** after two surfaces returned to pending under a regression
waiver. All source-implemented / build-free-verified; no runtime claim.

**2026-07-24 milestone — Material rewrite burn-down 16.06% → 73.62%:** a
source-implemented rewrite wave moved 731 registered surfaces from `pending` to
`rewritten-material` in
[`qa/windows-ui-contract/material-rewrite-ledger.json`](qa/windows-ui-contract/material-rewrite-ledger.json),
earned only through `bin/check-material-rewrite-ledger.py --evaluate` (935/1270,
in-progress 0, pending 335; `options-page`, `menu`, and `popover` closed at
100%). Menu credit is composition-code cross-referenced to
`qa/windows-ui-contract/menu-composition.json`, and a new
`notification-overlay-composition` contract closes one `native-shell` row. The
local gate is 157/157 scripts passing. This is **static source evidence only**:
no native build ran, `runtime_verified` stays `false`, and no Windows UI
inventory gate `B V I A L P C` moved. A green checker is not a verified pixel —
see [`HANDOFF.md`](HANDOFF.md) for the honesty boundary and the 335 remaining
pendings with their structural blockers.

The current delivery and verification scope is Windows. Cross-platform
acceptance gates remain recorded below as deferred future work; they are not
silently removed or treated as evidence for the current Windows milestone.
The 105-row [`Windows UI inventory`](docs/WINDOWS_UI_INVENTORY.md) is the
measurable Windows closure ledger: every future evidence credit names its stable
inventory ID rather than inheriting completion from a shared primitive.
The operator-provided design archive is pinned and interpreted in the
[`canonical Windows rewrite contract`](docs/design/00-windows-rewrite-contract.md).
Its eleven surfaces are all required; no single application or shared primitive
stands in for whole-suite completion.

## Phase 0 — reproducible foundation

**Status: in progress**

- preserve and document the exact LibreOffice upstream baseline;
- establish the Material design contract and token vocabulary;
- pin the canonical design archive by SHA-256 and map all eleven surfaces to
  the 105-row Windows acceptance inventory;
- publish an honest project site and screenshot registry;
- publish an interactive, dependency-free Material design reference on the site
  as the whole-suite visual and interaction target — 11 suite surfaces, a regex
  builder on every search bar, and a Find & Replace dialog (explicitly a
  hand-built mockup, not a build screenshot);
- guard that reference and the Windows build path in CI: a dependency-free
  validator (`bin/validate-prototype.mjs`) and `prototype-check.yml` check its
  self-containment, tokens, icons, and regex engine, while every `main` push (or
  manual dispatch) starts `windows-installer.yml`. The former Linux installer
  workflow was deliberately removed with Windows-only stages 4+5. The Windows
  workflow pins Visual Studio 2022,
  provisions Cygwin, runs the required native tests, uploads the validated MSI
  directly to an exact draft release, and only then publishes a normal public
  release. Its single-writer policy promotes that release to Latest only when
  the built commit is identical to or descends from the current stable MSI;
- define native build profiles and artifact retention rules, including a
  source-controlled local Windows bootstrap/build entry point;
- preflight the low-level computer-use driver and an off-screen desktop;
- connect that proven harness to a built LibreOffice binary and isolated profile;
- establish a repository-memory ledger for decisions, evidence, and progress.

Current evidence: the Windows harness preflight passed on 2026-07-16 using a
temporary Notepad process. On 2026-07-20, the harness advanced to the real
LibreOfficeDev MSI payload and accepted nine canonical Start Center captures:
three light, three dark, and three forced high contrast, each with a matching
bounded UNO tree and no collector errors. Every appearance profile includes one
visible keyboard Tab focus transition to the accessible `Open File` button. The local
[one-click Windows script](docs/LOCAL_WINDOWS_BUILD.md) now provisions an
isolated VS 2022 C++/CLI/C++ Clang/Cygwin profile, validates it, and creates a
clean LF source snapshot. On 2026-07-19, its first bootstrap installed the
dedicated VS 2022/Cygwin profile and a clean preflight passed; the first real
configure then exposed the absent C++ Clang compiler required by the default
Skia build. The local bootstrap now requires that component before retrying.
The hosted Windows workflow uses a clean LF checkout and a pinned runner that
supplies its prerequisites. Before the Windows-only cut removed the Linux
workflow, Linux run `29695793821` and Windows run `29695815101` both passed
`tools_test`, `extensions_test_update`, `vcl_widget_definition_reader_test`,
`vcl_file_definition_widget_draw_test`, and `vcl_treeview`; the Windows run also
passed the legacy CLI payload check and built the full LibreOfficeDev
installation set.

The local script's default remains the isolated, CI-matching VS 2022 profile.
It also has an explicit local-only VS 2026 selection through
`-VisualStudioYear 2026`. A verified existing host installation can be selected
only by also passing its exact `-VisualStudioInstallPath`; an incomplete host
path stops rather than being repaired or silently substituted. Without that
path, the opt-in profile uses its dedicated
`%ProgramData%\LibreOfficeMaterialTools\VS2026` Build Tools root. Use a distinct
build root such as `$env:USERPROFILE\lo-material-vs2026` for its first run. The
CI workflow remains pinned to VS 2022 for now.
The local checker recognizes both the VS 2022 `Llvm\bin` layout and VS 2026's
host-native `Llvm\x64\bin` Clang layout.
On 2026-07-19, the named VS 2026 Enterprise host passed no-bootstrap preflight
after C++/CLI, Clang, and VC145 merge modules were installed, then completed an
isolated configure at `a6d9f9a7dbdf10c08afe2eb03239e702ec5172ef`. Its first
native build reached third-party compilation and exposed MSVC v145's C++20
`mdds` conditional-`noexcept` incompatibility. The source now carries a
bounded v145 C++20 workaround. A fresh exact-source build at
`577059e2741185b512c184c64685c16d335d10ea` then passed all five required
native targets, validated the legacy CLI payload, completed the product, and
produced an unsigned 199,692,288-byte MSI. Windows Installer administrative
extraction returned status `0` with one `soffice.exe`, and that extracted
runtime supplied the first accepted Start Center UI and bounded UNO-tree smoke,
which remains retained as historical accepted proof.
Screenshot/docs commit `b0e3ea76639796aa5612dbce0333e394a5073f4c` is pushed,
and Pages run
[`29720519782`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/29720519782)
succeeded for that exact commit. Its two published image inputs retain SHA-256
`e4a21bd16c99ef360749dd72557a8d5a9df7c38d0a51122e8ca0058c57464501`
and `30667f9c9c8163183dc6f7d780113e52b90d710dca0ac64044afd5b5243ef378`.

Run `29695815101` did not upload an MSI: its staging script recursively matched
two retained LibreOffice working databases as well as the final installer. The
workflow now inspects only the success-only final `LibreOfficeDev\msi\install\en-US`
directory and still requires exactly one MSI plus administrative extraction and
`soffice.exe` validation. Hosted run
[`29720519794`](https://github.com/Ding-Ding-Projects/libreoffice-material/actions/runs/29720519794)
completed unsuccessfully after the build and is retained as historical workflow
diagnosis rather than publication evidence. The
local wrapper's parent process exited after successful extraction but before its
final dist staging/manifest copy. Current source waits on the exact hidden
`msiexec` client before inspecting the payload; static PowerShell 5.1/7
validation passes. Exact implementation commit `7029dccf4` then completed all
five VS 2026 native targets, full product/MSI regeneration, waited extraction,
and canonical MSI/checksum/manifest staging.

A separate normal public, non-prerelease release was published at
[`windows-msi-local-20260720-577059e274`](https://github.com/Ding-Ding-Projects/libreoffice-material/releases/tag/windows-msi-local-20260720-577059e274)
on 2026-07-20 at 06:06:42 UTC. It targets product source `577059e274`, contains
exactly the MSI, checksum sidecar, JSON build manifest, and XML update manifest,
and its unsigned 199,692,288-byte MSI has SHA-256 `437b059c…54a43`. After an
initial propagation delay, cache-busted unauthenticated Latest downloads for all
four assets matched the release sizes and SHA-256 values exactly. This is a real
historical release, but not the corrected updater candidate described below.

The corrected candidate was subsequently published as a normal public,
non-draft, non-prerelease release and was verified as Latest at that time:
[`windows-msi-local-20260720-fbba560e2`](https://github.com/Ding-Ding-Projects/libreoffice-material/releases/tag/windows-msi-local-20260720-fbba560e2)
on 2026-07-20 at 06:44:07 UTC. It targets exact product source
`fbba560e27db26de605c40aa237c554c1f0744b1` and contains exactly four public
assets. Cache-busted unauthenticated Latest downloads then matched the published
sizes and SHA-256 values: MSI 199,688,192 bytes,
`180e511c065f3e21cd9e4fd0abe31f8886b0cc5ce5ce27a48f2890f83d1afeea`;
sidecar 102 bytes,
`e82f022d06665a165b8d0145acac0aae7b39cd9f8b9cbd0f7a1cfa1105021b9e`;
JSON manifest 1,011 bytes,
`12e6495e5d5051657dd99e6c0afc6d61941144c1bcde5f792f09a9949bea0fc1`;
and XML manifest 972 bytes,
`b686d9e9641360c3962bc27b8b6517b9a76c14c06cd50efbcbcfe485724eab72`.
Those immutable release bytes remain valid evidence. A later pre-fix source
release displaced it from Latest and caused a 404; the completed one-time repair,
legacy-run cancellations, and post-cancellation recheck are recorded in the
2026-07-26 milestone above.

The local script is intentionally non-destructive: it checks safe short roots,
both tool/build-drive free space, and a clean checkout before installing
dependencies when Git is already available; it uses isolated Cygwin Git rather
than installing a global Git client. It does not normalize the development
checkout, delete a prior build root, silently use a host Visual Studio
installation, reboot Windows, or install its MSI. Its
VS 2022 default and VS 2026 build state cannot resume each other's work. A
complete successful full run removes only its verified-clean temporary LF
worktree. The completed VS 2026 build proves the selected toolchain/product path;
the wrapper now waits for administrative extraction before inspecting/staging,
and exact implementation commit `7029dccf4` passed its final
staging/manifest phase.

The source now contains a Windows-only consent-based update path. It reads the
exact GitHub Latest XML asset and accepts only one safe tag-derived GitHub URL
for the canonical MSI with exact `application/x-msi` MIME, positive size, and
lowercase SHA-256 metadata. It rejects legacy or malformed persisted state,
checks the completed download, and on confirmation copies it with `CREATE_NEW`
into protected LocalAppData staging with full-access ACEs limited to
SYSTEM/Administrators/Owner Rights,
re-verifies it, and retains a final read lock against write/delete replacement.
The visible MSI launch requires explicit default-No consent; silent install is
not implemented. An audit found that the `577059e274` binary forwarded only four
of its five generated installer arguments and omitted `REBOOT=ReallySuppress`.
Commit `fbba560e27db26de605c40aa237c554c1f0744b1` sizes the launch array from
the command and forwards all five release-binary entries, including restart
suppression. A real Sandbox update log later proved that its two `REINSTALL`
properties apply to repair, not a major update: the corrected MSI found the old
ProductCode but selected no features for its new ProductCode. Current source
uses the exact four-entry major-update vector `/i`, staged MSI,
`REBOOT=ReallySuppress`, and `MSIRESTARTMANAGERCONTROL=DisableShutdown`; the
focused suite asserts those arguments, the absence of repair-only properties,
exclusive `CREATE_NEW` staging, the protected DACL, and the retained read lock.
Automatic checks default on weekly, while automatic download is off and
download/install remain opt-in. See [`PRIVACY.md`](PRIVACY.md).
A bounded read-only UNO accessibility-tree collector now accompanies the
off-screen desktop plan. It runs with the matching built Python runtime and
records window roles, names, states, child counts, and optional bounds without
reading document text or invoking UI actions. The accepted light, dark, and
forced-high-contrast Start Center runs collected nine complete bounded trees
with no collector errors; this is a
collector smoke result, not a full accessibility audit.
The required native targets, local Windows MSI, and newest light Start Center
headless smoke have completed for exact source `393263ad9`; the older normal
release's four immutable assets and its historical Latest downloads are also
verified. The launch fix at `fbba560e2` passed
`CppunitTest_extensions_test_update`, an incremental full product/MSI build, and
Windows Installer administrative extraction. Its corrected unsigned
199,688,192-byte MSI is `180e511c…afeea`; the 4,885-file, 603,901,200-byte
extraction returned `0`, and its updater DLL matches the built DLL at
`32f80a…46a3`. The corrected extracted runtime then passed canonical off-screen
Home/Recent Documents, Tab-focus, and Templates smoke with three complete
bounded UNO trees: 96/49, 96/49, and 111/64 total/visible nodes, zero collector
errors, no partial capture, normal termination, zero remaining matching
processes/windows, and closed desktop/driver handles. The newest exact build
removes the footer Donate action, retains Help/Extensions, and repeated those
three states with atomic driver-side HWND/PID/thread/DPI ownership proof,
normal termination, and complete cleanup; its canonical light run is
[`20260720-143309-393263ad92-windows-headless-light`](docs/evidence/runs/20260720-143309-393263ad92-windows-headless-light/results.json).
The former canonical Home/Templates-only run
[`20260720-022159-fbba560e27-vs2026-msi-raster-restart-suppression`](docs/evidence/runs/20260720-022159-fbba560e27-vs2026-msi-raster-restart-suppression/)
remains historical evidence.
The newest exact payload also passed dedicated same-token dark and
forced-high-contrast Home/Tab-focus/Templates runs. Together those six states have complete
trees, normal UNO termination, zero remaining payload processes/windows,
desktop closure, and driver-process cleanup. Their manifests are
[`20260720-144200-393263ad92-windows-headless-dark`](docs/evidence/runs/20260720-144200-393263ad92-windows-headless-dark/manifest.json)
and
[`20260720-144249-393263ad92-windows-headless-highcontrast`](docs/evidence/runs/20260720-144249-393263ad92-windows-headless-highcontrast/manifest.json).
The corrected normal release's four immutable assets and its historical Latest
downloads are verified. The mutable route is repaired to MSI-123; the three
legacy unguarded runs were cancelled and the route was rechecked afterwards.
Updater download/stage/consent flow, MSI install/repair/upgrade/uninstall and
restart-suppression lifecycle proof and the remaining UI/accessibility matrix
remain pending. The wrapper's final dist staging phase passed again at exact
implementation commit `393263ad9`. This scoped runtime smoke
does not prove any MSI lifecycle behavior.
A fresh exact-tag Sandbox input run
`20260720-041140-7240676-b3777205bfb344a2977090ba35d643c3` now passes the
non-launching `Inspect` gate with both MSI sizes/hashes pinned and an empty
output mapping. Its first isolated launch then failed closed while serializing
generic PowerShell lists into the result bundle: the launcher returned `1`, no
`COMPLETE.json` or host-verification acceptance was produced, and host reboot
and LibreOffice-registration fingerprints remained identical. The harness now
serializes through typed arrays, tracks the current packaged Sandbox server and
remote-session process names, and validates retained host proof in `Verify`.
This diagnostic is not lifecycle runtime proof; a fresh run remains required.
Fresh run `20260720-043916-4641037-b451b45fa51a423c880f7092faa45274`
then proved the JSON fix and automatic packaged-client disposal, but stopped
before any MSI operation because the query helper returned all 107 Property
rows as one nested collection. It produced a hash-manifested `FAILURE.json`,
empty step/snapshot arrays, exit `1`, identical host fingerprints, and zero
remaining Sandbox processes. The helper now emits each row separately and its
exact PowerShell 5.1 source reads both pinned MSI identities correctly. This is
also diagnostic only; another fresh run is required.

An interactive, dependency-free Material design reference for the whole suite is
published at [`site/prototype.html`](site/prototype.html): a hand-built HTML
rendering of all eleven surfaces (Start Center, Writer, Calc, Impress, Draw,
Base, Math, Features, History, Components, Dialogs) with light/dark/high-contrast
themes, compact/comfortable density, classic/ribbon chrome, a regex builder on
every search bar, and a Find & Replace dialog. Its tokens mirror
`material/definition.xml` (documented in
[`docs/DESIGN_TOKENS.md`](docs/DESIGN_TOKENS.md)), and
[`bin/validate-prototype.mjs`](bin/validate-prototype.mjs) guards its invariants
(9/9), including the exact 11-surface map, notification manager/history
contract, and five shared regex-builder instances. It specifies the design the native work targets and is **not** a capture
of a compiled build, so it does not advance any acceptance gate or the
verified-capture count. The exact-source local MSI and Start Center evidence are
tracked separately. The corrected normal
`windows-msi-local-20260720-fbba560e2` release has four byte-verified public
assets and targets the five-argument updater-launch correction. It was verified
as Latest before the source-channel incident. Immutable publication is complete,
and the route has since been repaired to MSI-123; the release does not close updater runtime or
restart-suppression lifecycle gate. The older `577059e274` release remains
historical with its launch-argument warning. The historical assetless release/tag `e` contains no
build and does not satisfy any release or evidence gate. Neither package workflow
publishes unless a real package is produced and validated.

Exit gate:

- a clean checkout can reproduce the chosen build;
- the start center can be launched on a headless desktop;
- an unedited baseline screenshot and manifest can be captured and reviewed;
- documentation distinguishes current evidence from planned work.

## Phase 1 — Material foundations in VCL

**Status: in progress — native C++ targets and scoped light/dark/high-contrast Start Center smoke passed;
remaining runtime matrix pending**

Implemented source milestones:

- packaged `material/definition.xml` with matched light and dark palettes of 23
  semantic roles each, 79 definition-backed parts, and 205 control states;
- exact semantic coverage for all 72 `StyleSettings` color slots, including the
  formerly native-dependent accent, list-box collection/selection,
  alternating-row, warning, and error roles; the ten additions are optional in
  the general reader so partial legacy themes keep their native values;
- opt-in `VCL_FILE_WIDGET_THEME=material` selection behind the existing
  `VCL_DRAW_WIDGETS_FROM_FILE` gate, with safe theme names, shared immutable
  definitions, and successful-load caching keyed by theme and scheme; failed
  requests attempt `online`, which is absent from this imported desktop tree;
- unconditional Material activation for the Windows app: `soffice_main()`
  (`desktop/source/app/sofficemain.cxx`, under `#ifdef _WIN32`, before any
  consumer reads them) forces both variables on every Windows launch so the
  shipped MSI renders Material with no manual step and — per operator directive,
  Material Design is the product — with no opt-out variable and no user override
  (system high-contrast precedence remains the only accessibility bypass); locked
  by the `material-default-activation` source contract
  (`bin/check-material-default-activation.py`), which fails closed on any
  reintroduced opt-out token or `getenv` override. This corrects the prior
  releases that packaged the assets but left them dormant; it is
  source-implemented wiring only (`runtime_verified: false`) and claims no build
  or pixel evidence — the first release built after it is the first with Material
  active by default;
- source-level profile selection from resolved dark mode, with high contrast
  taking precedence and bypassing Material colors for native or generic
  fallback drawing;
- capture/restore of the pre-Material native style/framework baseline, plus
  dynamic focus-policy refreshes so a switch to generic high-contrast fallback
  does not retain Material colors or suppress VCL focus indicators;
- semantic `body`, `label`, and `title` typography roles with strict parsing,
  100–200% nonshrinking scale bounds, explicit minimum weights, and native
  font identity preservation across app, help, field, control, menu, tab, and
  title slots;
- eight semantic corner roles with strict, order-independent native reader
  resolution; 159 rounded Material rectangles now use one role reference each,
  11 square rectangles remain implicit, and legacy numeric `rx`/`ry` themes
  retain their existing path;
- 15 semantic native integer metric roles with strict, order-independent native
  reader resolution; 346 current integer uses reference those roles—307 drawing
  strokes, 34 explicit part dimensions/margins, and 5 numeric settings—while
  generic legacy themes retain literal numeric compatibility;
- exact geometry preservation across that conversion: the 684 normalized
  fractional drawing coordinates stay literal, implicit dimensions remain
  implicit, and typography scale and corner radius keep their separate token
  contracts;
- Qt proxy/no-native high-contrast signal handling and explicit dark-profile
  selection when headless VCL has no operating-system appearance signal;
- support reporting limited to definition-backed parts so unsupported parts
  preserve their existing fallback;
- order-independent semantic color, shape, and metric `@token` resolution with
  strict rejection of invalid colors, radii, or integer metrics, invalid
  or duplicate token sections, mismatched palette schemas, ambiguous radius
  attributes, unknown references, and unknown or duplicate parts;
- expanded mixed/disabled controls, flat buttons, selected-hover/focus tabs,
  toolbar buttons and grips, list nodes, edit variants, scrollbars, sliders,
  menus, progress, surfaces, and standalone vertical/horizontal spin buttons;
- full-track progress indicators and value-sensitive level indicators in the
  shared file-widget renderer: the optional track spans the control, the fill
  remains clipped to the caller's numeric value, and level states preserve the
  four existing 25% semantic bands without changing legacy fill-only themes;
- native anatomy for the two reader-recognized controls the theme had not yet
  defined: an outlined frame (`Frame`/`Border`) drawn as one shared container
  rectangle and reported through a new native frame region so `decoview` issues
  its border draw, and a net-less tree connector (`ListNet`/`Entire`) that is
  supported but draws nothing so VCL suppresses its own connector nets; both add
  no new tokens and only one `stroke-thin` reference and one rounded rectangle;
- disabled-affordance state completeness: a dimmed disabled `SubmenuArrow`, a
  dimmed-but-checked toolbar button, and a disabled-but-selected tab (`Entire`
  and `MenuItem`), closing three cases where a disabled tuple VCL passes
  previously collapsed onto a generic state and lost its meaning;
- composite combo/RTL geometry, native-region and slider sizing corrections,
  exact standalone spin geometry/direction, and native graphics line/fill cache
  invalidation;
- local static validation for color/shape/metric token discipline, an exact
  72-slot Material style schema, required parts/states, unused tokens,
  light/dark schema parity, exact geometry closure, and selected contrast pairs,
  with reader and headless drawing C++ targets plus negative fixtures; the
  headless target includes source coverage that dispatches settings through the
  real file renderer.

The standalone validator passes with 2 schemes, 23 color tokens each, 3
typography roles, 8 shape tokens, 15 metric roles, 72 style slots, 79 parts, and
205 states. The five required native C++ targets have compiled and executed in
current Linux and Windows runs, including definition parsing and state-dispatch
command/region assertions. The corrected `fbba560e2` administratively extracted
runtime also launched Home/Recent Documents and Templates on an off-screen
Windows desktop with both Material opt-in variables set. That scoped application
smoke does not prove that each visible control consumed the definition, does not
individually exercise the 79 parts or 205 state tuples, and is not a pixel-test
suite. The metric roles preserve the current integers and existing downstream
native conversions; they add no density profile or new DPI-aware, `dp`,
fractional-scale, or touch-sizing policy.

- build/runtime verification of system-driven high-contrast routing, deeper
  keyboard focus traversal, plus complete forced-color and platform-signal coverage;
- remaining typography properties (line height and letter spacing),
  density-aware spacing/metric profiles, density-aware/full shape semantics,
  elevation, opacity, motion, and density selection;
- remaining dragged, read-only, invalid, and platform-specific state layers;
- reusable focus rings and keyboard modality handling;
- core button, icon button, checkbox, radio, switch, text field, list, tab,
  tooltip, menu, progress, and surface primitives;
- extend the executed definition/state command/region C++ coverage with missing
  build-backed pixel comparisons on Windows; equivalent cross-platform proof is
  retained as a deferred gate outside the current delivery scope.

Exit gate:

- primitives render through native VCL paths on Windows for the current delivery
  scope; equivalent supported-platform evidence remains a deferred gate;
- token values are centralized and application code does not hard-code Material
  colors;
- every state is keyboard reachable and has accessible semantics;
- headless light, dark, high-contrast, and scaling evidence is recorded.

## Phase 2 — shared shell and common surfaces

**Status: in progress — initial Start Center source, native builder coverage,
and light/dark/high-contrast launch/navigation/focus smoke passed; broader shell runtime pending**

The Start Center source slice adds spacing, a Home header/subtitle, distinct
navigation/content/container surfaces, and VCL-derived recent/template colors.
Its `open_all` button now uses the standard `suggested-action` semantic, which
`VclBuilder` preserves as the push-button action state selecting the existing
Material `extra="action"` styling. Its focused `VclBuilder` fixture passed in
the current Linux, Windows, and local VS 2026 native runs. The exact-source MSI
payload has now displayed and captured light, dark, and forced-high-contrast
Start Center Home and Templates states plus a visible `Open File` Tab-focus state
in every appearance profile. Deeper keyboard traversal, visible action-state
exercise, and broader shared shell scenarios remain open.
Current source also removes the bottom Donate action and its native/accessibility
wiring, leaving the Help and Extensions footer actions in contiguous positions;
a focused source validator and six tests pass. Exact commit `393263ad9` also
passed the VS 2026 product build, five-target native regression phase, MSI
staging/extraction, and accepted light Home/focus/Templates UI and accessibility
smoke. Exact-source dark and forced-high-contrast Home/focus/Templates runs
then passed the same visual, interaction, accessibility, and cleanup gates.
The next source slice removes the archive-external periodic donation banner and
clickable legacy brand artwork as well. This newer source has focused validator
coverage but does not inherit the earlier `393263ad9` build or screenshot proof.

After the no-nag slice removes the file-association and Welcome dialog roots,
the exhaustive Windows dialog contract now registers all 599 top-level
`GtkDialog`, `GtkMessageDialog`, and `GtkAssistant` roots for migration to a
customizable bottom-right notification form. The registry validator fails on
new, removed, duplicated, reclassified, or implicitly governed roots. Current
native source also adds the shared Windows-only post-layout placement seam:
every VCL `Dialog` reaching final `InitShow` is anchored to the bottom-right of
the visible owner/work area with a bounded 16 px inset and decorated-window
clamping; LibreOfficeKit and other operating systems are unchanged. Its source
contract and eleven mutation regressions pass. This is placement infrastructure,
not a complete notification form: hosting, event routing, customization,
stacking, visible management, and exact-build runtime proof remain open.

The storage layer now provides a local bare Git notification
repository with a fixed `main` ref, a process mutex plus permanent OS-held
cross-process operation guard, CAS ref updates, metadata-only privacy default,
bulk read/archive/delete/restore transitions, pinning, deduplication,
purge/empty-trash maintenance, history, and inverse-commit undo. Parentless
checkpoints compact before a user mutation; their durable pending gate blocks
later writes until pruning succeeds, bounds reachable history, and preserves
the exact action commit for undo. A failed-prune retry validates and reuses the
installed checkpoint, so repeated failure neither advances `main` nor adds
objects. A lazy application-owned asynchronous facade now constructs, accesses,
and destroys the store only on one serialized worker. Requests receive monotonic
IDs, UI consumers receive immutable generation-stamped record/history snapshots,
profile completions return through a cancellable VCL event queue, conflict
results refresh to the winning ref, and shutdown closes admission before it
cancels callbacks, drains accepted mutations, and joins. Pending raw VCL events
self-retain their queue, and the injectable repository factory requires
off-worker completion dispatch while keeping focused tests independent of the
user profile. A generated office-configuration adapter maps all display and
retention preferences. Twenty-one native CppUnit cases cover the model, service
ordering/shutdown/reentrant destruction/conflict/bulk-action-commit/privacy
behavior, initialization/races, permanent-lock contention, the 129-commit
threshold, forced repeated prune failure, crash recovery, reload, and exact
undo; they are wired but not yet compiled. The static contract and all 24 Python
mutation tests pass. See
[`docs/design/02-notification-service-architecture.md`](docs/design/02-notification-service-architecture.md).
On 2026-07-21 the visible layer landed in source: a snapshot-consuming
presenter with a bottom-right per-work-area overlay stack, severity-styled
cards, a folder/bulk/preferences manager window, and a `NotificationRouter`
facade whose classification keeps input, destructive, credential, and security
prompts modal. Two producers route through it (help-search no-matches,
printer-busy), the shared `sfx2::ConfirmDestructiveAction` helper converted
five real destructive confirmations under a new fail-closed dialog-anatomy
contract with the safe action holding both initial focus and the Enter
default, and the dialog policy registry was reconciled so input/destructive/
credential/security roots carry explicit modal exclusions. Broad producer
migration across the remaining policy registry, customization controls, and
all build/runtime proof remain open.

The companion search contract registers 30 audited shipping text-query fields,
no planned fields, and 16 explicit non-search exclusions. It fails
on missing, duplicated, stale, or newly unclassified candidates and requires an
adjacent advanced builder policy on every shipping field. The reusable native
foundation now supplies ICU/LibreOffice literal and regex evaluation, `i/g/m/s`,
live syntax/error and bounded match testing, token insertion, embedded
Build/Test/Reference/Examples guidance, and Apply/Cancel/click-away semantics in
a `GtkPopover` anchored to the adjacent builder button. Its source contract,
mutation coverage, UI lint, and accessibility lint pass; fourteen native
CppUnit cases are wired but not compiled in the current checkout.
Build/Test/Reference/Examples are
scroll-backed, close cancellation is backend-independent, and Qt placement is
work-area clamped. Sixteen of the 30 shipping fields are source-integrated and
14 carry explicit architectural gap evidence. The document Find toolbar now
hands validated effective patterns and literal/regex algorithms through its
existing UNO dispatch while preserving Match Case and Find All ownership. Calc Go to Sheet preserves its
legacy `OUString::indexOf` default; Forms, Find & Replace, and Writer Quick Find
now route effective patterns and flags into their native matcher paths. The
implementation registry, focused validator, and 100 shared plus 10 Find-toolbar
mutation regressions pass.

By 2026-07-21 the integration contract generalized twice into a strict
parameterized form: four matcher strategies (in-handler legacy literal,
options-handoff, native-regex-option-sync, and controller-driven declared
search sites), four cross-validated default modes including a
regex-native-case-insensitive seed, per-entry match subjects, and a 67-test
fail-closed mutation suite. Twelve of the 27 registered shipping fields are
now source-integrated with the adjacent accessible builder (Calc Go to Sheet,
Start Center document search, Form record search, Find & Replace, Writer Quick
Find, Template Manager, Keyboard customization, Options search, Manage Changes
comment filter — whose legacy case-insensitive-regex default is preserved
exactly — Writer Find Entry, Extension Manager, and the Gallery sidebar). The
other 15 fields carry reviewed, documented honest-gap analyses (stacked
auto-dismiss popovers, a typeahead index selector, bidirectional similarity
matchers, a remote threaded catalog, split UNO toolbar ownership, a stub
surface, multi-collection branching filters, and URL-based help engines) and
stay registered as unintegrated targets. Native build and behavior proof
remain open for every integration.

The rewrite now removes automatic donation/Get Involved/What’s New promotion,
first-start Welcome, Tip scheduling, Windows file-association solicitation,
AutoCorrect explanation, and crash-report submission prompts in source. Dead
prompt controllers, factories, options (including the now-unreachable
crash-report opt-in), resources, and configuration are
removed rather than hidden. Explicit Tip/What’s New/file-association commands
remain, crash dumps remain available to the explicit crash-report service, and
document recovery, Safe Mode, incompatible-extension, macro/security,
hidden-metadata, signature, read-only, and credential warnings remain intact.
The fail-closed validator covers 35 forbidden prompt markers, nine removed
surfaces, and 16 required suppressions/safeguards/manual actions; all four
mutation tests pass. A dedicated exact-build headless harness now implements the
fresh plus seeded legacy-profile startup matrix without `--nologo`,
`--norestore`, or other GUI-suppression switches. It binds the payload build ID,
exact PID/HWND ownership, bounded window polling, screenshots, complete UNO
trees, former-nag text denial, and the retained safety/manual allowlist. The
adversarial source pass additionally enforces batch-safe encoded profile URIs,
clears inherited crash-dump enablement in both modes, binds PID/HWND/thread/DPI
and exactly one total stable window, validates the dedicated listener identity
and endpoint cleanup, and independently rescans retained poll/a11y artifacts.
Its 63-safeguard source validator and four mutation families pass. No new native
payload was launched for this harness slice, so both runtime scenarios, visual
review, and accepted evidence remain open. Because an administratively extracted MSI lacks
the installed-product `HKLM` registration used by the historical automatic
association check, that registry-gated branch requires an MSI-installed
disposable Windows Sandbox or VM and cannot be claimed from extracted-payload
startup alone.

On 2026-07-21, wave-2 Batch A added eight shared-shell, navigation, and feedback
surfaces at source level, each guarded behind the Material file-widget theme and
each locked by a new fail-closed build-free contract (checker + JSON registry +
mutation suite). Three reached whole-row source scope: the menubar/drop-menu
anatomy carried through the settings->NWF->`Menu::ImplCalcSize` channel with the
disabled-arrow `@outline` plumbing (`menu-composition`, 18 tests over 24 code
markers); the warning/error infobar's four-severity Material container/on-container
resolution with a code-painted corner-container radius, high-contrast square
bypass, and polite `AccessibleRole::NOTIFICATION` announcement (`material-infobar`,
16 tests); and the native `FixedHyperlink` + `weld::LinkButton` interaction
contract with a `@primary` corner-focus ring, tintless-underline hover, plain
disabled text, and a tracked/rendered/queryable visited state (`link-contract`,
25 tests). Five landed as partial source with named residual deltas: the 48px
`@surface-container` sidebar rail via the sfx2 sidebar `Theme` slots consumed by
`TabBar` (`sidebar-rail`, 14 tests); the 28px status band with `@outline-variant`
top rule and accessible owner-draw value changes (`statusbar-composition`, 21
tests); the Recent/Template Start Center card anatomy (`startcenter-cards`, 18
tests); the Find & Replace Material field set driving one `SvxSearchItem` ICU
descriptor with a loop-safe regex-toggle sync (`find-replace-fieldset`, 25 tests);
and the Calc `ScTabControl` strip top rule and selection-independent tab-colour
accent (`calc-sheet-tabs`, 22 tests). No build or runtime evidence exists for any
of it: the `B V I A L P C` inventory gates are untouched and every row's pixel,
interaction, and accessibility proof stays pending a native build.

Wave-2 Batch B then assessed nine more rows across shell navigation, application
chrome, surfaces, and feedback, again each locked build-free by a new or extended
checker plus JSON registry plus mutation suite. Five landed as new fail-closed
contracts: the Calc classic-chrome composition (command identity/order, separator
placement, nine-state toolbar Button at `@corner-toolbar`, with density and combo
geometry recorded spec-only) (`calc-chrome`, WIN-CA-001); the `ScInputWindow`
formula row additively painted over `ToolBox::Paint` with guarded
`@corner-container` token consumption and `@surface`/`@on-surface` centralization,
RTL specified-not-built (`calc-formula-bar`, WIN-CA-002); the Components-gallery
coverage ledger binding every state generated from `material/definition.xml` (205
cells, reusing the theme validator) with a 14-test suite
(`component-gallery-coverage`, WIN-CONCEPT-003); the audited `NotificationRouter`
producer seam — the Find & Replace Replace-All Success card and no-match
Information card folded into the bottom-right notification stack (design 07 §7.5,
no standalone snackbar plate) with wiring-marker reachability
(`notification-producer`, WIN-FBK-005/WIN-FBK-008); and the sidebar deck /
side-pane Material layout (deck `@surface` fills, 14 px inset, deck-title role,
12 px scrollbar, collapse-to-rail and below-medium overlay-degrade)
(`sidebar-panels`, WIN-CON-007). Two existing contracts were extended:
menu-composition gained 18 context-menu markers (keyboard-first highlight,
placement feed, focus save/return, Esc dismiss) for WIN-NAV-002, and
impress-draw-surfaces gained the shared svx Position-and-Size and Shadow panels
plus the Draw/Impress object bars for WIN-WR-004/WIN-IM-002. Two of the nine rows
landed with deliberately narrowed scope: WIN-WR-004 covers only the shared svx
field anatomy — the planned `writer-surface-sidebar` checker was not built and
the Writer deck composition is untouched — and WIN-FBK-008 covers only the §7.8
empty-state outcome of those two routed producers, not the general
empty/no-results pattern. As with Batch A, no build or runtime evidence exists
for any of it: the `B V I A L P C` inventory gates stay untouched and every row's
pixel, interaction, and accessibility proof remains pending a native build.

Wave-2 Batch C then landed the twelve staged system-dialog and design-concept
rows at source level, each locked build-free by a new fail-closed checker plus
JSON registry plus mutation suite (290 mutation tests total). Eleven are
Windows system flows: file open/save delegation (WIN-SYS-001 — the Windows
`IFileDialog`/`FOS_OVERWRITEPROMPT` platform boundary, the
`SystemFilePicker`→`OfficeFilePicker` selection seam, and three no-`.ui`
call-site message boxes classified decision/security/credential, all modal and
none routed); the PDF export tabbed dialog (WIN-SYS-002); the Document
Properties icon-rail notebook (WIN-SYS-003); template manager and
save-as-template (WIN-SYS-004); extension manager (WIN-SYS-005); macro
manager/organizer/security (WIN-SYS-006); certificate/signature/macro-security
prompts (WIN-SYS-007); recovery/crash/Safe-Mode with a fail-closed SAFE-default
invariant (WIN-SYS-009); migration/profile-compat with a silent-migration
positive path paired to a forbidden-nag blocklist (WIN-SYS-010); uui
authentication/conflict/error interaction (WIN-SYS-011); and the Help/About
family (WIN-SYS-015). The twelfth is WIN-CONCEPT-001, a deterministically
regenerable Features command-catalog coverage ledger that binds all 2,433
prototype rows to real `.uno` command nodes across the ten officecfg command
XMLs with zero unresolved. Four real destructive confirmations were migrated
onto the shared `sfx2::ConfirmDestructiveAction` helper: three registered in
`dialog-anatomy-policy.json` (Save-As-Template overwrite, delete template
category, remove extension — taking that registry to its 8-migration cap,
unraised) and one (the shared basctl `QueryDel` funnel, five callers)
registered in `macro-surface.json` because the anatomy registry is full; all
four are compile-plausibility-checked, not compiled. The WIN-SYS-015 row also
moved 15 unassigned cui Help/About surfaces into the WIN-SYS-016 closure
override table and regenerated the ui-registry ledger (unassigned 449→434,
assigned 821→836, total 1270 unchanged). As with Batch A and B, no build or
runtime evidence exists for any of it: every registry carrying a
`runtime_verified` field keeps it `false`, every carve-out stays
`status: specified`, and the `B V I A L P C` inventory gates stay untouched —
the row credits move only `D` (`△`→`✓` where design detail was the gap) and `M`
(`·`→`△` for the new source contracts).

The 2026-07-23 mega wave then advanced 43 rows in parallel — reaching beyond the
shared-shell scope of this phase into the foundations of Phase 1 and the Writer,
Calc, Impress/Draw, Base, Math, and chart surfaces of Phases 3–6 — as 33 new
fail-closed build-free triads plus five in-place contract extensions, 562 new
mutation tests, all green. Foundations gained regression/precondition pins for
theme-resolution routing, elevation, reduced motion, density, adaptive layout, the
icon-theme pipeline, render/scale neutrality, and a version-history seeded-state
ledger; the widget and dialog layer gained pushbutton, icon-button, Options,
file-picker, print, and Find & Replace closure contracts; navigation chrome gained
notebookbar (a guarded `@surface` group-area edit), title-bar, and command-overflow
pins; and Writer, Calc, Impress, Base, Math, and the embedded chart editor each
gained composition or source-consumption contracts. Genuine guarded-material-source
edits landed in `notebookbar.cxx`, the two svx overlay files
(`viewobjectcontactofsdrpage.cxx`, `sdrpaintwindow.cxx` — cross-application blast
radius, both sequenced to lose to high contrast), the four dbaccess rail surfaces,
five acknowledgement-modal→`NotifyInfo` conversions, two more
`sfx2::ConfirmDestructiveAction` migrations (raising `MAX_MIGRATIONS` 8→10), and a
`certificatechooser.cxx` search predicate split (a 13th source-integrated search
field). The registry-closure campaign moved 184 surfaces out of the `unassigned`
baseline (836→1020 assigned, 434→250 unassigned, 1270 total unchanged) via four new
prefix rules and per-cluster overrides. Honesty held: `M` advanced `·`→`△` only
where a genuine Material source or `definition.xml`-grounded composition contract
landed, while the presence-marker and upstream/D-gate pins (command overflow, the
upstream Calc TabBar, the Math substrate, render/scale neutrality, the Impress
pane/slideshow/presenter surfaces, the Base Add-Table tree, reduced motion,
adaptive layout, and the icon-theme pipeline) explicitly did **not** advance `M` —
existing upstream, non-Material-guarded source never satisfies it. A calibration
correction landed on WIN-FND-002 (the theme-resolution chain is compiled and now
pinned; its remaining gap is build/matrix, not source), and three rows were parked
with honest reasons in the inventory (WIN-SEL-003 switch design-detail-only,
WIN-SEL-004 filter chips and WIN-SHL-001 shell chrome as none-feasible build-free).
The build-free static gate now stands at **147** scripts, all green. As with every
prior wave, no build ran and no pixel/screenshot/runtime evidence is claimed: every
`runtime_verified` stays `false`, every carve-out stays `status: specified`, and the
`B V I A L P C` inventory gates stay untouched.

The Stage-1 ground-up Start Center rewrite then landed in source (six single-owner
clusters plus an integrator, all behind the existing Material guards):
`startcenter.ui` and `backingwindow.cxx` were rebuilt to the chapter-9
navigation-column and search-pill anatomy (236 px rail, Open File/Remote Files
pills, Recent/Templates toggle pills, a CREATE heading with six app-chip create
rows, and a search pill with an inline clear button and `.*` regex-mode toggle);
the recent grid gained a guarded first-run invitation card replacing the legacy
Welcome bitmap on the Material path; `RegexSearchController` gained the inline
`ToggleMode`/`SetMode` API; ten accent palettes plus an Options › Appearance
accent/density/reduced-motion control set (committed through the existing
restart path) were added; and eight bespoke Start Center glyphs shipped in both
icon themes. It is source-implemented only — no build ran, `runtime_verified`
stays `false`, and no inventory glyph moved. One cross-cluster contract remains
red pending its owner's migration (the regex-search-integrations checker still
pins the pre-rewrite adjacent search-row layout and fails on the new pill); the
rest of the build-free gate — 147 of 149 scripts — is green.

- start center, window chrome integration, menubar/command surfaces, status bar,
  sidebar shell, notebookbar variants, infobars, snackbars, and notifications;
- common file, print, export, properties, options, extension, and template flows;
- adaptive command layout for compact, medium, and expanded window widths;
- shared empty, loading, error, and destructive-confirmation states.

Exit gate:

- shared surfaces no longer require application-specific Material forks;
- shortcuts and menu mnemonics remain intact;
- common flows pass headless keyboard and screenshot matrices.

## Phase 3 — Writer

**Status: planned**

- document canvas framing, rulers, navigation, styles, properties, review, and
  collaboration surfaces;
- formatting, tables, images, references, mail merge, and page-layout flows;
- comments, tracked changes, search, accessibility checks, and error states.

Exit gate:

- the agreed Writer workflow suite passes with keyboard-only operation;
- no regression is detected in document rendering or round-trip compatibility;
- representative widths, locales, themes, and scaling factors have evidence.

## Phase 4 — Calc

**Status: planned**

- formula bar, sheet tabs, headers, selection affordances, filters, sort, data,
  pivot, chart, and conditional-formatting surfaces;
- dense-grid interaction rules that preserve spreadsheet throughput;
- large-sheet performance and assistive-technology navigation checks.

Exit gate:

- core spreadsheet workflows pass at performance and accessibility budgets;
- formula and grid behavior remain independent of visual token changes;
- dense and touch-friendly profiles have recorded evidence.

## Phase 5 — Impress and Draw

**Status: planned**

- slide/page panes, canvas controls, object properties, master views, animation,
  transitions, presenter console, and drawing tool surfaces;
- drag, resize, rotate, selection, alignment, layering, and multi-object states;
- presentation and multi-display regression coverage.

Exit gate:

- authoring and presenting workflows pass on supported display configurations;
- pointer, keyboard, and assistive selection paths are equivalent;
- animation honors reduced-motion preferences.

## Phase 6 — Base, Math, charts, and remaining UI

**Status: planned**

- Base database, query, form, and report workflows;
- Math formula editor and symbol selection;
- chart editing, macros, extensions, certificates, recovery, onboarding, and
  legacy dialogs not covered by shared-shell work;
- complete inventory closure for every registered UI surface.

Exit gate:

- the UI inventory contains no unclassified or silently excluded surface;
- platform-specific and optional-feature dialogs have owners and evidence;
- fallback rendering is explicit where Material behavior is unavailable.

## Phase 7 — suite-wide hardening

**Status: planned — Windows hardening is in current scope; equivalent
cross-platform matrices are deferred**

- screen-reader and keyboard audits on Windows, followed by the retained,
  deferred cross-platform audits;
- high contrast, forced colors, color-vision, reduced-motion, and zoom checks;
- bidirectional text, long translations, CJK/CTL fonts, and locale formatting;
- startup, memory, paint, input-latency, and large-document performance budgets;
- GPU/software rendering, remote desktop, fractional scaling, and multi-monitor
  matrices;
- migration, safe mode, crash recovery, and profile compatibility.

Exit gate:

- defined accessibility and performance budgets pass in CI or recorded labs;
- P0/P1 visual defects are closed and no critical workflow lacks evidence;
- release notes identify known exceptions without hiding them.

## Phase 7.5 — Settings dialog search bars (COMPLETED)

Material Design search bars added to AutoCorrect, Spelling, Dictionary, and Security settings dialogs with inline regex builder support. All follow existing treeopt.cxx pattern.

---

## Phase 8 — release readiness and upstreamability

**Status: in progress — Latest repaired to MSI-123 and legacy runs contained;
revised publisher proof, updater, and MSI lifecycle proof pending**

- complete native validation of the Windows updater and stable packaging path;
- preserve the exact GitHub Latest XML, strict MSI metadata/hash checks,
  protected staging, explicit consent, and no-silent-install contract;
- retain the completed 2026-07-26 repair evidence after a source-installer
  release displaced the stable MSI from Latest: MSI-123 restored, four assets,
  and HTTP-200 canonical MSI/XML/checksum routes at the expected lengths; the
  three old-policy runs were cancelled and the check repeated afterwards;
- keep source-installer releases explicitly non-Latest and verify after each
  publication that Latest still contains the canonical MSI; serialize stable
  MSI publishers and promote only a commit identical to or descended from the
  current stable commit;
- keep all eligible build-free checkers and mutation suites closed under CI
  fleet-coverage validation, and keep release tags from duplicating the Windows
  UI contract's branch-push run;
- execute the statically validated disposable Windows Sandbox harness that pins
  old/corrected MSI hashes and requires exact-zero install, same-version update,
  repair, and uninstall results with no restart indicators or host mutation;
- resolve the retained third-run sequencing gap: old install and corrected
  same-version commands returned `0` without restart-state changes, but the old
  ProductCode remained registered and the run correctly rejected lifecycle
  acceptance before repair/uninstall;
- publish through the draft-first workflow only after exact target, asset,
  digest, and normal-release checks pass; a release that is not a proven
  ancestry-forward stable candidate remains public but non-Latest. Current
  source handles GitHub's temporary `untagged-*` draft URL and still needs a
  post-change pushed-run proof;
- contributor, design-review, and regression-triage documentation;
- licensing, attribution, trademark, privacy, and security reviews;
- split generally useful improvements into reviewable upstream proposals;
- publish a signed evidence index and supported-platform statement.

Exit gate:

- every whole-GUI requirement maps to accepted evidence or a documented,
  user-visible exception;
- release artifacts reproduce from tagged source;
- the project no longer needs a milestone disclaimer to explain unfinished core
  surfaces.

## Cross-phase acceptance matrix

Every visible component or workflow must be checked against:

| Dimension | Minimum evidence |
| --- | --- |
| Build | exact commit, platform, configuration, and successful artifact |
| Visual | genuine capture at agreed themes, scale factors, and widths |
| Interaction | pointer and keyboard path with expected state transitions |
| Accessibility | role/name/state, focus order, contrast, zoom, and motion behavior |
| Localization | long-string, bidirectional, and representative CJK/CTL coverage |
| Performance | comparison against an agreed upstream baseline |
| Compatibility | document results and user profile behavior unchanged unless specified |

The live evidence contract is in [`docs/HEADLESS_UI_EVIDENCE.md`](docs/HEADLESS_UI_EVIDENCE.md).

