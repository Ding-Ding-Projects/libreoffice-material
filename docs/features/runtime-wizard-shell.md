# Runtime wizard shell

## Behavior

LibreOffice's shared `GtkAssistant` file is intentionally an empty shell. VCL
creates each wizard page and the Help, Previous, Next, Finish, and Cancel
buttons at runtime. Under `VCL_FILE_WIDGET_THEME=material`, every generated
page now receives the Material `space-list-entry` metric on all four margins
and both grid axes. Next and Finish are the only forward actions marked as
Material primary actions; the wizard continues to choose which one is visible
for the current step.

The static shell remains modal and title-free because individual wizard owners
supply the real title at runtime. Its legacy six-pixel `border-width` override
is removed so the shared Material renderer owns the outer container.

## Configuration

The treatment activates only for the Material file-widget theme. There is no
new user preference and no persisted wizard-specific state. System forced
colors take precedence: high-contrast mode keeps the stock action treatment
and page geometry.

## Failure modes

If the Material definition cannot be loaded or the spacing metric is absent,
VCL falls back to the existing runtime layout instead of blocking the wizard.
The fail-closed contract rejects an invented static title, a restored legacy
border, missing page margins, theme-gate drift, or any primary-action set other
than Next and Finish.

## Security and accessibility

The change does not alter response codes, decision order, modal behavior,
keyboard navigation, page membership, or help routing. Forced-colors
precedence prevents Material styling from overriding the user's system
contrast scheme. Runtime focus order and screen-reader output still require an
installed-build check.

## Verification

`qa/windows-ui-contract/runtime-wizard-composition.json` is enforced by
`bin/check-runtime-wizard-composition.py` and six mutation tests. The contract
pins the checked-in shell, the runtime page host, token lookup, theme and
high-contrast guards, and action construction. Source verification is passing;
`runtime_verified` remains `false` until the Windows MSI is exercised through
the headless harness.

## Suggested articles

- [Runtime dialog shells](runtime-dialog-shells.md)
- [Host-composed surfaces](host-composed-surfaces.md)
- [Dialogs design](../design/08-dialogs.md)
