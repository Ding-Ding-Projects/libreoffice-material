# Material Writer document canvas

## Behavior

Writer's workspace outside visible document pages now resolves the Material
`surface-container-low` color in light and dark Material modes. `PaintDesktop`
subtracts every visible page rectangle before drawing that color, so the change
applies to application chrome around the document rather than to document
content. The page-shadow bitmap helper clears its four edge seams with the same
resolved canvas color.

The document page, text, selection, insertion cursor, object overlays, rulers,
zoom, print preview, printer/metafile output, and LibreOfficeKit tile rendering
retain their existing owners and coordinate paths. This contract does not claim
that document content itself has been recolored.

## Configuration

The composition is active only with the existing Material file-widget gate:

```text
VCL_DRAW_WIDGETS_FROM_FILE=1
VCL_FILE_WIDGET_THEME=material
```

Material light and dark palettes must both define
`surface-container-low`. Non-Material themes retain the configured Writer
application-background color and optional background bitmap. High contrast is
checked before the Material gate and continues to use the configured/system
fallback.

## Failure modes

- An absent or invalid Material palette falls back to Writer's configured
  application-background color.
- A missing light or dark `surface-container-low` role, reordered
  high-contrast/theme gate, lost page subtraction, document-paint ordering
  drift, or inconsistent shadow-seam consumer fails the source contract.
- Material mode deliberately bypasses the optional decorative workspace bitmap
  so the local token fill remains deterministic; the bitmap path is unchanged
  for every other theme.
- Source composition does not prove native compilation, pixels, clipping,
  scaling, or interaction in an installed build.

## Security and accessibility

The implementation reads only bundled theme data and an existing process-level
theme selector. It performs no network access, persistence, document mutation,
input interception, or coordinate remapping. Document and assistive-technology
semantics are unaffected because this is a workspace paint decision, not a new
widget or accessible object. Forced colors retain precedence.

## Verification

`qa/windows-ui-contract/writer-canvas-composition.json` is enforced by
`bin/check-writer-canvas-composition.py` and thirteen focused tests (twelve
mutations plus the production contract). The checker parses every bundled
Material palette, follows the workspace slot to `surface-container-low`, and
pins the high-contrast-first resolver, visible-page subtraction, background
bitmap gate, desktop/document paint order, shared shadow-seam color, four edge
consumers, and preserved rendering/input paths.

`runtime_verified` remains `false`. A native Windows Writer build and focused
light/dark/high-contrast captures are still required before rendered behavior
is claimed. Immutable source commit
`d48a2a57d90910174ad3c364af713d862c61a00e` carries the implementation and its
native-shell ledger credit.

## Suggested articles

- [Writer and Calc specification](../design/10-writer-calc.md)
- [Windows UI contracts](../../qa/windows-ui-contract/README.md)
- [Headless UI evidence](../HEADLESS_UI_EVIDENCE.md)
