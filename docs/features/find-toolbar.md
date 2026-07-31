# Document Find toolbar

## Behavior

The document Find toolbar now places the shared advanced regular-expression
builder directly beside its editable history combo. Plain text remains the
default. When the user opts into regular-expression mode, the shared ICU-backed
controller validates the pattern, applies multiline and dot-all modes to the
effective expression, and hands the resulting search string and algorithm to
the existing `.uno:ExecuteSearch` dispatch.

Find Next, Find Previous, and Find All remain separate toolbar actions. Their
scope is not duplicated as a misleading Global checkbox in the builder.
Likewise, the existing Match Case control remains authoritative; its state is
synchronized into the builder before preview and dispatch. Match Diacritics
and Search Formatted retain their existing toolbar ownership.

The old empty, hidden label that existed only to satisfy a static form scan has
been removed. The entry and builder are real adjacent, keyboard-focusable
siblings with translated accessible names and descriptions.

## Configuration

There is no new persisted preference. Search history continues to use the
existing `FindReplaceRememberedSearches` setting. Regex mode and preview state
live in the toolbar controller for the current item-window lifetime. Pattern
and sample text stay local; the builder does not transmit them.

## Failure modes

- An invalid regular expression is shown as an entry error and never reaches
  `.uno:ExecuteSearch`.
- A pattern beyond the bounded live-preview budget skips preview work without
  truncating the actual document query.
- If the toolbar is destroyed, the shared controller is released before its
  entry and button, preventing callback use-after-free.
- If no dispatch provider is available, the existing search action remains a
  no-op; the builder does not invent an alternate matcher.

## Security and accessibility

Evaluation uses LibreOffice's local ICU/TextSearch path and the existing UNO
document-search dispatch. No query or sample text is persisted beyond existing
search history or sent over the network. The builder button is reachable by
keyboard, has a visible label, translated accessible metadata, and returns to
the owning toolbar workflow when its anchored popover closes.

## Verification

`qa/windows-ui-contract/find-toolbar-composition.json` is enforced by
`bin/check-find-toolbar-composition.py` and ten focused mutations. The shared
search registries additionally run 22 coverage and 100 integration mutations.
The contract pins adjacency, accessibility, callback ownership, destruction
order, invalid-pattern suppression, effective-pattern/algorithm handoff,
Match Case synchronization, Find All scope, and the removal of the fake label.
Source verification passes at commit
`5f9bc77fc35901bfe9f355c483409302bb642b34`; `runtime_verified` remains `false`
until a Windows MSI exercises the toolbar through the headless harness.

## Suggested articles

- [Host-composed surfaces](host-composed-surfaces.md)
- [Dialogs and search inputs](../design/08-dialogs.md)
- [Windows UI contract index](../../qa/windows-ui-contract/README.md#search-fields-and-regex-builders)
