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
| [`document-tabs.md`](document-tabs.md) | The Material document-tab strip (`SfxDocumentTabBar`), its per-tab appearance editor, `officecfg` config, and clamp-on-read style normalizer. Stages 1-3. | Source-implemented, guarded off by default; **runtime UNVERIFIED**. |
| [`ui-scale.md`](ui-scale.md) | The persisted 50-400% UI-scale control on Tools > Options > Appearance (refs tdf#101646). | **Stored-value only**; no live rescale; runtime UNVERIFIED. |

There is no HTTP or API surface in this category, so no Postman collection
applies to it.

## Related documentation

- Build and distribution: [`../build/README.md`](../build/README.md)
- Target design specification: [`../design/README.md`](../design/README.md)
- Contracts these features are cross-checked against: `qa/windows-ui-contract/`
