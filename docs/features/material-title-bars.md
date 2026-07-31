# Material window and floating title bars

## Behavior

Material mode now consumes the six existing active/deactive frame slots at both
title-bar owners. VCL-rendered normal, small, and tear-off title bands choose
their fill, text, border, and caption-symbol colors from the active state of the
owning border window. Windows top-level frames pass the same active or inactive
colors to DWM for the caption, border, and title text.

`WM_NCACTIVATE` refreshes the DWM values whenever a top-level window becomes
active or inactive. LibreOffice does not draw or resize the Windows non-client
frame: DWM continues to own caption buttons, close-hover red, hit testing,
dragging, snapping, system menus, DPI, and accessibility semantics.

## Configuration

The composition is active only with the existing file-widget Material gate:

```text
VCL_DRAW_WIDGETS_FROM_FILE=1
VCL_FILE_WIDGET_THEME=material
```

The bundled definition supplies `height-window-title` (18),
`height-floating-title` (14), and the six frame slots. Active fill/border uses
`primary`, active text uses `on-primary`, and inactive fill/text/border uses
`disabled-container`, `outline`, and `outline-variant` respectively. No new
parallel palette is introduced in the Windows backend.

## Failure modes

- If the Material theme is not selected, both renderers retain their previous
  native-compatible behavior.
- If high contrast is active, VCL skips the Material title treatment and the
  Windows backend resets all three DWM color attributes to
  `DWMWA_COLOR_DEFAULT`.
- Windows versions that do not support the newer DWM color attributes ignore
  those calls; no client-side frame replacement is attempted.
- A missing metric, token mapping, activation hook, DWM attribute, forced-color
  reset, or VCL slot consumer fails the source contract.

## Security and accessibility

The implementation changes colors only. It does not add hooks, replace hit
testing, intercept system commands, change accessible names, or modify window
ownership. The document/application title remains the platform window name,
caption controls retain their system roles and targets, and forced colors remain
system-owned.

## Verification

`qa/windows-ui-contract/titlebar-composition.json` is enforced by
`bin/check-windows-titlebar-composition.py` and nineteen focused tests (eighteen
mutations plus the production contract). The
contract checks the token source, both consumers, active/inactive selection,
caption-symbol color, all three DWM attributes, the `WM_NCACTIVATE` refresh,
high-contrast reset, and absence of client-side non-client hit testing.

`runtime_verified` remains `false`. A Windows build plus focused active/inactive
captures of both a top-level frame and a VCL floating title are still required
before rendered behavior is claimed.

## Suggested articles

- [Material design direction](../../MATERIAL_DESIGN.md)
- [Navigation specification](../design/05-navigation.md)
- [Headless UI evidence](../HEADLESS_UI_EVIDENCE.md)
