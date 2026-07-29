# Document tabs

A Material document-tab strip that lets a user switch between open documents
from a horizontal tab row, with a per-tab appearance editor. The feature is
built in three stages and is **guarded OFF by default**.

- Stage 1 — `a0cefa50a` — fail-closed frame-topness seam registry (analysis
  only, no runtime capability).
- Stage 2 — `508740c16` — the `officecfg` document-tab style schema, the
  clamp-on-read normalizer, and their contract.
- Stage 3 — restored at `af689a470` after the initial attempt and its reverts —
  the Material document-tab strip (`SfxDocumentTabBar`) and its per-tab
  appearance editor, with both compile errors corrected.

## Behavior

### The strip

`SfxDocumentTabBar` (`sfx2/inc/SfxDocumentTabBar.hxx`,
`sfx2/source/appl/documenttabbar.cxx`) is a real `svtools::TabBar` subclass, so
it inherits the already-shipped Material `TabBar` paint path — the same anatomy
the Calc sheet-tabs already use (`calc-sheet-tabs.json`). Material tokens are
resolved from `vcl::MaterialTokens` over `definition.xml`, gated on
`VCL_FILE_WIDGET_THEME=material` and disabled under high contrast
(`GetHighContrastMode`). The per-tab accent colour is drawn as an overlay
strip (`PaintMaterialDocTabOverlay`) that is deliberately independent of the
selection state (it never consults `IsPageSelected` / `GetCurPageId`).

### Tab activation raises an existing window — it does not host documents

On tab activation, `SfxDocumentTabBar::RaiseFrameForPage` reuses the **exact**
frame-activation path the Window menu uses
(`WindowListMenuController::itemSelected` in
`framework/source/uielement/resourcemenucontroller.cxx`):
`VCLUnoHelper::GetWindow(xFrame->getContainerWindow())`, then
`pWin->GrabFocus()` and `pWin->ToTop(ToTopFlags::RestoreWhenMin)`.

This **raises an already-existing top-level window**. It never hosts multiple
documents inside one window, never touches a frame-topness seam, and performs
no `WorkWindow` cast. True in-window multi-document hosting is a later,
CI-gated stage and is **not implemented**.

### Frame-topness seam registry (stage 1)

Stage 1 ships no runtime tabs. It is an add-only static guardrail:
`qa/windows-ui-contract/frame-topness-seams.json` inventories the 84 code
sites that assume a document frame is a top-level `WorkWindow`/`SystemWindow`
(the historical tdf#37134 failure mode), each classified `host-owned`,
`tab-owned`, or `audited-safe`. An `unaudited` entry, a new call site absent
from the registry, or a removed one fails `bin/check-frame-topness-seams.py`
closed — so a later change that violates a topness assumption fails the checker
instead of shipping a latent crash.

### Per-tab appearance editor

Reachable from the strip's right-click context menu
(`CommandEventId::ContextMenu`), a weld dialog over
`sfx2/uiconfig/ui/documenttabappearance.ui` (dialog id
`DocumentTabAppearanceDialog`) edits a tab's custom label, colour, pin,
favorite, and font. Every value is re-validated through the normalizer before
being persisted via `officecfg`. The `.ui` is gla11y-clean (0 FATALs).

## Configuration

Two `officecfg` locations, both in
`officecfg/registry/schema/org/openoffice/Office/Common.xcs`:

### `Appearance/DocumentTabs` — app-level strip settings

| Property | Type | Default | Values |
| --- | --- | --- | --- |
| `TabsEnabled` | `xs:boolean` | **`false`** | on/off master guard |
| `TabWidth` | `xs:short` | `1` | `0`, `1`, `2` |
| `TabCloseButtons` | `xs:short` | `0` | `0`, `1`, `2` |
| `TabDensity` | `xs:short` | `0` | `0`, `1` |

### `Histories/DocumentTabStyles` — per-document style

A set node-type with **one entry per document URL**. Properties include
`CustomLabel`, `Pinned`, `Favorite`, `Order`, `GroupId`, `FontSize`
(`xs:short`, default `13`, clamped `10`-`32`), `TextColor`, `BackgroundColor`,
`FontFamily`, `Bold`, `Italic`, `Underline`. Every rendered attribute comes
from this persisted style passed through `SfxDocTabStyle::Normalize` — the
strip contains no hardcoded colour or label.

## Failure modes

- **Guarded off by default.** The static `SfxDocumentTabBar::Create` factory is
  the only way to obtain a strip and returns `nullptr` unless
  `DocumentTabs::TabsEnabled` is true. The widget cannot even be constructed
  when tabs are off, so the default (tabs-off) build path is byte-identical to
  stock.
- **Clamp-on-read of untrusted persisted values.** `SfxDocTabStyle::Normalize`
  (`sfx2/source/appl/doctabstyle.cxx`) validates every style property on read:
  `FontSize` is clamped to 10-32 pt, colours are accepted only as hex strings,
  and font family is allow-listed. The schema and normalizer are cross-checked
  property-for-property in both directions by
  `qa/windows-ui-contract/doc-tab-style-schema.json`; any drift (a schema
  property with no normalizer branch or vice-versa, a wrong type/default/enum/
  clamp, or `TabsEnabled` defaulting to anything but `false`) fails the checker
  closed.

## Security considerations

- The per-document style is persisted **keyed by the document URL**, in the
  user's own registry (`Histories/DocumentTabStyles`). No tab id or style is
  ever written into the user's document file.
- Because every persisted value passes through `SfxDocTabStyle::Normalize`
  before use, a roaming profile or a hand-edited registry cannot inject an
  unsafe style (oversized font, non-hex colour, arbitrary font family) into the
  UI — the normalizer clamps or rejects it on read.
- Tab activation reuses the existing, audited window-raise path and performs no
  unchecked `static_cast<WorkWindow*>`, avoiding the tdf#37134 crash-on-null
  class of bug.

## Verification status

**Source-implemented and guarded; current follow-up compile rerun and RUNTIME UI
verification remain pending.**

- Cross-checked build-free by three fail-closed contracts:
  `qa/windows-ui-contract/frame-topness-seams.json` (stage 1),
  `doc-tab-style-schema.json` (stage 2), and `document-tab-strip.json`
  (stage 3). All three carry `"runtime_verified": false`.
- Restored Stage 3 commit `af689a470` is an ancestor of successful MSI-123 at
  `952090ce2`; that workflow is historical compile evidence for the restored
  Stage 3 source. The 2026-07-29 follow-up subsequently changed the strip, and
  exact-source run `30423589955` failed its first critical desktop-library link
  because `MapUnit::MapPoint` had only a forward declaration. Current source
  includes `tools/mapunit.hxx` and pins that requirement in the fail-closed
  contract, but its corrected hosted rerun remains pending. Neither run proves
  construction, painting, activation, persistence, or accessibility at runtime.
- **Tabs do not render until an MSI exercises them.** No tab pixels and no
  window switching are claimed here.
- True in-window multi-document hosting is a later, CI-gated stage and is
  **not implemented**. Stage 3 tab activation is only the existing
  `pWin->ToTop()` window raise, not a frame-topness change.
