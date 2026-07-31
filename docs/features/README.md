# Features

This category documents discrete user-facing features shipped into the
LibreOffice Material fork. Each feature has its own document covering its
behavior, configuration, failure modes, security considerations, and an
honest verification status.

Every feature below is **source-implemented and guarded**, cross-checked by a
build-free `qa/windows-ui-contract/*.json` contract plus its fail-closed
checker. None is runtime-proven in this repository: the C++ is compiled only by
the ~3h Windows MSI CI leg, not here, and no pixels or live behavior are
claimed until an MSI exercises them. Each document states this plainly in its
own "Verification status" section.

| Document | Covers | Runtime status |
| --- | --- | --- |
| [`document-tabs.md`](document-tabs.md) | The Material document-tab strip (`SfxDocumentTabBar`), its per-tab appearance editor, `officecfg` config, and clamp-on-read style normalizer. Stages 1-3. | Historical Stage 3 compiled in MSI-123; the `MapUnit` fix is hosted-compile-confirmed, while the owner complete-type correction awaits a further rerun. Guarded off by default; **runtime UI UNVERIFIED**. |
| [`ui-scale.md`](ui-scale.md) | The persisted 50-400% UI-scale control on Tools > Options > Appearance (refs tdf#101646). | Compiled in MSI-123; **stored-value only**, no live rescale; runtime UNVERIFIED. |
| [`runtime-dialog-shells.md`](runtime-dialog-shells.md) | Material inset grids and fail-closed C++ page-host ownership for twenty-one runtime-composed notebook shells. | Source contract + 23 mutation tests; **runtime UI UNVERIFIED**. |
| [`runtime-wizard-shell.md`](runtime-wizard-shell.md) | Token-spaced runtime pages and Material primary Next/Finish actions for the shared VCL wizard shell. | Source contract + 6 mutation tests; **runtime UI UNVERIFIED**. |
| [`find-toolbar.md`](find-toolbar.md) | Adjacent advanced regex builder and validated ICU/UNO handoff for the document Find toolbar. | Source contract + 10 focused and 100 shared mutations; **runtime UI UNVERIFIED**. |
| [`msi-lifecycle-branding.md`](msi-lifecycle-branding.md) | Deterministic token-derived installer branding across install, maintenance, progress, completion, and safe-decision MSI stages. | Generator check + 10 mutations; **real MSI lifecycle UNVERIFIED**. |
| [`material-title-bars.md`](material-title-bars.md) | Active/inactive Material slot consumption in VCL floating title bands and Windows DWM top-level chrome. | 19 focused tests (18 mutations + production); **runtime UI UNVERIFIED**. |
| [`writer-canvas.md`](writer-canvas.md) | Token-derived Writer workspace fill and page-shadow seams outside page-subtracted document content. | 13 focused tests (12 mutations + production); **runtime UI UNVERIFIED**. |
| [`updater-lifecycle.md`](updater-lifecycle.md) | Versioned update states, progress/retry summaries, and installer/rollback ownership through the shared Material notification stack while verified default-No install consent remains intact. | 21 focused tests (20 mutations + production); **runtime lifecycle UNVERIFIED**. |
| [`host-composed-surfaces.md`](host-composed-surfaces.md) | Hash-locked shared-renderer ownership for 195 audited dialog variants and host/atomic fragments whose static form predicate is structurally inapplicable. | Source contract + 12 mutation tests; **runtime UI UNVERIFIED**. |

There is no HTTP or API surface in this category, so no Postman collection
applies to it.

## Related documentation

- Build and distribution: [`../build/README.md`](../build/README.md)
- Target design specification: [`../design/README.md`](../design/README.md)
- Contracts these features are cross-checked against: `qa/windows-ui-contract/`
