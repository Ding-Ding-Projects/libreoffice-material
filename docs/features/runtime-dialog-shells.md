# Runtime-composed Material dialog shells

## Behavior

Eighteen modal notebook dialogs create their page labels and page bodies in C++
after the `.ui` shell loads: Chart **3D View**, **Character**, and **Paragraph**;
plus shared **Area**, **Border/Area/Transparency**, **Border/Background**,
**Callout**, **Customize**, and **Format Cells**; and Writer **Envelope**,
**Footnote/Endnote**, and **Format Section**; plus **PDF Export**, **Document
Properties**, and Writer **Character**, **Paragraph**, **Picture**, and **Table
Properties**. Each shell places its empty, scrollable left-tab
notebook inside a Material content grid: 12 px on every edge, 6 px row spacing,
and 12 px column spacing. Titles, welded IDs, page factories, button responses,
Enter default, and cancellation behavior are unchanged.

The burn-down ledger classifies these eighteen resources as
`runtime-dialog-shell`/`dialog-composition`. That family does not weaken the
ordinary static-dialog predicate; a surface joins only through the explicit
allow-list and a contract proving both its `.ui` shell and its C++ page host.

## Configuration

There is no user setting. The active Material theme supplies native tab and
control rendering; the shell contributes only layout metrics and the existing
runtime controllers contribute the pages. The feature is scoped to:

- `chart2/uiconfig/ui/3dviewdialog.ui` with
  `chart2/source/controller/dialogs/dlg_View3D.cxx`;
- `chart2/uiconfig/ui/chardialog.ui` and `paradialog.ui` with their
  `dlg_ShapeFont.cxx` and `dlg_ShapeParagraph.cxx` controllers;
- `cui/uiconfig/ui/areadialog.ui` with `cui/source/tabpages/tabarea.cxx`;
- `cui/uiconfig/ui/borderareatransparencydialog.ui` and
  `borderbackgrounddialog.ui` with `cui/source/tabpages/bbdlg.cxx`;
- `cui/uiconfig/ui/calloutdialog.ui` with `cui/source/tabpages/labdlg.cxx`;
- `cui/uiconfig/ui/customizedialog.ui` with
  `cui/source/customize/cfg.cxx`;
- `cui/uiconfig/ui/formatcellsdialog.ui` with
  `cui/source/dialogs/sdrcelldlg.cxx`;
- `sw/uiconfig/swriter/ui/envdialog.ui`, `footendnotedialog.ui`, and
  `formatsectiondialog.ui` with their owning Writer controllers;
- PDF Export and Document Properties with their existing specialized contracts;
- Writer Character, Paragraph, Picture, and Table Properties with
  `writer-format-dialogs.json` and their owning controllers.

Adding another shell requires an intentional contract row, classifier allow-list
entry, source host markers, mutation coverage, and independent evidence. An
empty notebook alone is never sufficient.

## Failure modes

- Missing or zeroed grid metrics fail the source gate.
- A static page added to the notebook conflicts with the runtime-shell contract
  and must be reclassified or deliberately redesigned.
- A removed, duplicated, or reordered controller marker fails closed rather
  than crediting an empty dialog.
- Footer response or default-action drift fails before it can be counted as
  Material.
- Native clipping, focus, scale, localization, or accessibility defects can
  still exist despite source conformance; those require built-runtime evidence.

## Security considerations

All eighteen dialogs remain modal and retain their existing primary/Cancel response semantics.
No data source, persistence path, privilege boundary, network request, or page
factory changes. The checker strips C++ comments before locating host markers,
so a commented-out page constructor cannot masquerade as live implementation.

## Verification status

Build-free verification is provided by:

```sh
python bin/check-runtime-dialog-shell-composition.py
python -m unittest bin/test_runtime_dialog_shell_composition.py
python bin/check-material-rewrite-ledger.py
python -m unittest bin/test_material_rewrite_ledger.py
```

The contract and 20 mutation tests prove source composition only.
`runtime_verified` is `false`; no new native dialog capture, keyboard trace,
screen-reader transcript, or scale matrix is claimed.

## Related documentation

- [Dialog design and runtime-shell anatomy](../design/08-dialogs.md#runtime-composed-dialog-shells)
- [Windows UI contract index](../../qa/windows-ui-contract/README.md#runtime-composed-dialog-shells)
- [Material rewrite ledger](../../qa/windows-ui-contract/material-rewrite-ledger.json)
