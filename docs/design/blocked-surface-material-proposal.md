# Blocked-surface Material proposal

This proposal covers the six remaining non-static surfaces that cannot be
made conforming by editing a `.ui` file alone. It is a design artifact, not a
claim that these surfaces are implemented or verified. The authoritative
reference remains the pinned LibreOffice design archive.

## Shared Material shell

When the owning runtime surface is available, use the existing Material
surface tokens: `surface-container` for the body, `surface-container-high` for
anchored overlays, 12 px content insets, 6 px internal spacing, 12 px corner
radius, visible keyboard focus, and the existing semantic text roles. Native
ownership remains unchanged: runtime-created controls stay runtime-created,
and OS-owned chrome is never duplicated by a GTK child.

## Surface proposals

| Surface | Material treatment | Non-negotiable behavior gate |
| --- | --- | --- |
| `native:find-toolbar` | Runtime Material toolbar band with an outlined search field, adjacent regex affordance, match-count supporting text, and a compact action cluster. | Preserve the existing `FindTextFieldControl` ownership, keyboard routing, and live-search timing. |
| `native:msi-install-lifecycle-ui` | Installer-owned Material-compatible branding and progress hierarchy where Windows Installer permits it; keep destructive/restart decisions in explicit native confirmation steps. | Do not replace or fake Windows Installer dialogs; validate a real MSI lifecycle. |
| `native:updater-lifecycle-ui` | Material update card with version, release code name, progress, retry, and rollback status; notifications remain non-blocking except for install consent. | Preserve staged-MSI verification, default-No consent, and restart suppression. |
| `native:window-title-bars` | OS title-bar integration using the app seed color, contrast-safe caption buttons, and system high-contrast/reduced-motion settings. | The OS owns hit testing, caption buttons, DPI, and accessibility semantics. |
| `native:writer-document-canvas` | Material document surface around the custom canvas: tokenized margins, selection/insert focus treatment, and overlay affordances that never paint into document content. | Preserve document pixels, custom drawing, zoom, selection, and input coordinates. |
| `vcl/uiconfig/ui/wizard.ui` | Material assistant shell around runtime pages: `surface-container`, 12 px page inset, progress/step indicator, and a footer whose primary action is supplied by the assistant owner. | Preserve `RET_*` responses, page order, default action, cancellation, and C++ ownership. |

## Acceptance gates

Each proposal becomes implementation only after its owning runtime contract
exists and can prove source, Windows build, headless interaction, pixels,
accessibility, localization, and performance evidence. Until then these rows
remain pending in the fail-closed ledger; this file deliberately does not
convert a design proposal into coverage credit.

