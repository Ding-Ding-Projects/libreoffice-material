# Windows UI coverage contracts

These registries turn the whole-application dialog and search requirements into
fail-closed source inventories. They establish migration scope; they do not
claim native implementation, a successful build, or runtime evidence.

## Dialog notification forms

`dialog-notification-policy.csv` is the exhaustive native dialog registry for
the Windows notification-form migration. It inventories every top-level
`GtkDialog`, `GtkMessageDialog`, and `GtkAssistant` object found in a Git-tracked
or untracked, non-ignored `.ui` file.

Each row must explicitly choose one of these policies:

- `bottom-right-notification-form` routes the dialog through the new
  bottom-right notification surface. `notification_profile` selects its
  customizable form profile; the initial profile is `default`.
- `native-exclusion` keeps a dialog outside that surface. It must have a
  non-empty `exclusion_reason` and cannot silently inherit a profile.

The contract intentionally does not claim that a registered dialog has already
become a complete notification form or been runtime verified; it establishes
complete, reviewable migration coverage. A separate source contract now guards
the first shared implementation seam: Windows VCL dialogs are repositioned only
after their final `InitShow` layout, relative to the visible owner/work area,
with bounded Material inset and work-area clamping. That seam is geometry only.
The current total is 598 roots (`GtkDialog` 521, `GtkMessageDialog` 76,
`GtkAssistant` 1) after the no-nag source slice deleted the automatic Windows
file-association and Welcome dialogs and the shared destructive-confirmation
dialog was added.

### Classification heuristic

The policy column mirrors the runtime router
(`sfx2::NotificationRouter::Classify`, `sfx2/source/notification/NotificationRouter.cxx`),
which keeps a prompt **modal** iff it collects input, confirms a destructive
act, handles credentials, or enforces security, and lets only purely
informational messages route to a notification. A static `.ui` scan **cannot**
prove a dialog is purely informational: most LibreOffice dialogs build their
entries, trees, and even their buttons at the C++ call site (e.g.
`ChartDataDialog`, `DataFormDialog`, and `RetypePass` carry only empty
container shells in their `.ui`). The ledger is therefore deliberately
conservative in the **safe** direction — a dialog stays `native-exclusion`
unless it shows affirmative static evidence of an acknowledgment-only message
box. `bin/check-windows-dialog-notification-contract.py --reclassify`
regenerates the whole column from these `.ui` content signals, in this
precedence:

1. **credential** — a password entry (`GtkEntry` with `visibility=False`) or a
   `password`/`login`/`credential`-family token in the path or id.
2. **security** — a `security`/`macrosecurity`/`certificate`/`signature`/
   `trust`-family token.
3. **destructive** — a `delete`/`remove`/`overwrite`/`discard`/`reset`-family
   token.
4. **input** — any value-entry or selection widget class (`GtkEntry`,
   `GtkSpinButton`, `GtkComboBox*`, `GtkTreeView`, `GtkTextView`,
   `GtkCheckButton`, `GtkRadioButton`, `GtkNotebook`, LibreOffice custom
   `*Entry`/`*ComboBox`/`*TreeView`/`*Edit`/`*Metric` widgets, …).
5. Otherwise a `GtkMessageDialog` routes to
   `bottom-right-notification-form` **only** when its button set is a built-in
   acknowledgment (the `buttons` enum `ok`/`close`, or `<action-widgets>`
   limited to `ok`/`close`/`help`). A message dialog whose buttons come from
   the call site (no `buttons` property and no `<action-widgets>`) cannot be
   cleared and stays modal, as do all `GtkDialog`/`GtkAssistant` shells.

That yields 9 `bottom-right-notification-form` acknowledgment message boxes and
589 `native-exclusion` rows (input 459, interactive 55, destructive 27,
decision 26, credential 14, security 8). Regenerating is idempotent; review any
new acknowledgment message added to the notification set before closing its
surface. The classifier is unit-tested per signal in
`bin/test_windows_dialog_notification_contract.py`
(`RoutingClassifierTest`).

`--update` remains the incremental workflow (below): it defaults **new**
dialogs to `bottom-right-notification-form` for explicit review, so run
`--reclassify` or hand-review after adding an input/destructive/credential
dialog.

`ui_path` plus `object_id` is the stable locator. The two source roots that do
not define a GTK object ID use an empty `object_id`, so their repository path is
the locator; duplicate paths remain forbidden.

Validate the checked-in registry and its regression suite:

```sh
python bin/check-windows-dialog-notification-contract.py
python bin/test_windows_dialog_notification_contract.py
python bin/check-windows-dialog-placement.py
python bin/test_windows_dialog_placement.py
```

After deliberately adding, removing, or changing a root dialog, regenerate the
inventory before reviewing the resulting diff:

```sh
python bin/check-windows-dialog-notification-contract.py --update
```

The update operation preserves policies for exact existing dialog identities
and assigns every new dialog the explicit `bottom-right-notification-form`
policy with the `default` customization profile. Review any intentional native
exclusion by editing that row and documenting a concrete rationale.

## Modal dialog anatomy (WIN-DLG-001)

`dialog-anatomy-policy.json` registers the shared Material
destructive-confirmation dialog and every real `weld::MessageDialog`
destructive confirmation migrated onto it, per
[`docs/design/08-dialogs.md`](../../docs/design/08-dialogs.md) §8.1. The helper
(`sfx2::ConfirmDestructiveAction`,
`include/sfx2/destructiveconfirmation.hxx` /
`sfx2/source/dialog/destructiveconfirmation.cxx`, over
`sfx2/uiconfig/ui/materialdestructiveconfirmdialog.ui`) composes the modal
footer in the shared order `Help | spacer | safe secondary | destructive
primary`, carries the `destructive-action` role (Material `@error-container`)
and a verb-named label on the primary, and binds the **safe** action as both
the initial focus and the Enter default so Enter/Space activation can never
destroy data. Native pixel rendering of the error-container fill and
keyboard-default emphasis remain deferred (MATERIAL_DESIGN milestone 10); this
is source composition/behavior evidence only.

The initial wave converts five confirmations off ad-hoc message boxes:
overwrite a style (`sfx2`), delete sheets with a pivot table and delete sheets
with data (`sc`, previously defaulting Enter to the destructive action), delete
a layer (`sd`), and delete an AutoText category (`sw`).

```sh
python bin/check-material-dialog-anatomy.py
python bin/test_material_dialog_anatomy.py
```

The validator fails closed on a reordered footer, a missing destructive-action
role, a non-verb ("OK") destructive label, a destructive Enter default or
destructive initial focus, a non-warning message type, a migrated call site
that drops the helper header or dispatch, or a registry outside the 3–8
migration wave. It claims no native build, dialog pixels, or runtime
interaction.

## Registered UI inventory closure (WIN-SYS-016)

`ui-registry.json` is the generated, checked-in closure ledger for the
`WIN-SYS-016` registry gate. It enumerates every registered UI surface exactly
once and maps each to one owner and one `WIN-` inventory row (or the explicit
`unassigned` bucket). It is a source-level ledger only: it makes no claim of
native implementation, a successful build, or any runtime evidence.

Two enumeration sources are combined:

- **`.ui` surfaces.** Every tracked or untracked, non-ignored `*.ui` file found
  by the same Git walk `check-windows-dialog-notification-contract.py` uses
  (cached plus non-ignored other files, filtered to paths that still exist).
  One `.ui` file is one surface. This includes the three notification `.ui`
  files (`notificationcard.ui`, `notificationmanager.ui`, `notificationstack.ui`).
- **Native surfaces.** A maintained explicit list of native-only, custom-drawn,
  optional, and platform surfaces the `.ui` walk cannot see: the Start Center
  thumbnail view, the inline Find toolbar, the Writer/Calc/Impress/Draw
  canvases, the MSI install lifecycle UI, the native updater UI, the bottom-right
  notification overlay window, and native window title bars. Each declares its
  own owner, inventory row, and a note explaining why it has no `.ui`.

The owner is the module (first path segment) for `.ui` surfaces and an explicit
declaration for native surfaces. Inventory-row mapping is an explicit,
reviewable table defined in the checker and mirrored into the registry's
`mapping` section: exact-path `overrides` win, then the longest matching
`prefix_rules` entry, otherwise the surface is recorded as `unassigned`. Prefix
attribution is deliberately owner-level: it records which inventory row owns the
surface, not that every dialog in that subtree is that row's exact anatomy.
Per-surface refinement of the `unassigned` bucket is the remaining WIN-SYS-016
work.

The `unassigned` count is an honest ledger figure, not a silent gap: the current
baseline is 449 of 1270 surfaces (chiefly the shared `cui`, `svx`, `svtools`,
`extensions`, and `vcl` dialog sets that no single inventory row owns). The
validator reports the count and does not fail merely because it is non-zero. It
fails closed on any drift from a fresh enumeration: an added, removed, or
renamed `.ui`; a newly `unassigned` surface not already in the checked-in
baseline; an unknown inventory ID; a duplicated surface; or any hand edit.

```sh
python bin/check-windows-ui-registry-closure.py
python bin/test_windows_ui_registry_closure.py
```

After a deliberate `.ui` addition, removal, or rename, or after editing the
mapping table in the checker, regenerate before reviewing the diff:

```sh
python bin/check-windows-ui-registry-closure.py --regenerate
```

Regeneration is deterministic: stable sort, no timestamps. Because other work
may add or modify `.ui` files concurrently, the final integration step
regenerates this registry again; a new surface that lands in an unmapped module
appears in the diff as an added `unassigned` row for review.

## Search fields and regex builders

`search-field-coverage.json` records the audited Windows text-query controls:

- 26 existing shipping search fields, each assigned the
  `adjacent-advanced-builder` contract;
- one planned Start Center `start_search` field, required to remain absent until
  it moves into shipping coverage; and
- 16 explicit exclusions for categorical selectors, range inputs,
  transformation parameters, object names, non-shipping QA controls, and the
  shared builder's own pattern editor.

The validator also scans `.ui` objects for search-like IDs, accessible text,
placeholders, tooltips, and `gtk-find` icons. A new unclassified candidate,
missing or duplicate widget, stale exclusion, wrong widget type, count drift,
or incomplete builder declaration fails the contract.

```sh
python bin/check_search_field_coverage.py
python bin/test_search_field_coverage.py
python bin/check-windows-regex-builder-foundation.py
python bin/test_windows_regex_builder_foundation.py
python bin/check-windows-regex-search-integrations.py
python bin/test_windows_regex_search_integrations.py
```

This is the minimum audited native inventory, not permission to ignore a new
app-owned search bar that the conservative scanner does not infer. Any newly
identified search field must be added and receive the same adjacent advanced
builder before its owning UI surface can close.

The shared native foundation now provides an ICU/LibreOffice search service,
literal and regex modes, `i/g/m/s`, bounded match testing, live errors, token
insertion, and embedded Build/Test/Reference/Examples content. Its
`GtkPopover` is anchored to the adjacent builder button and deliberately is not
a modal or bottom-right dialog.

`regex-search-integrations.json` is the separate source-implementation ledger.
It currently records Calc Go to Sheet as 1 of 26 shipping fields. Its validator
requires direct entry/button adjacency, translated accessible metadata,
controller-owned change dispatch, controller-first destruction, exact legacy
`OUString::indexOf` behavior in the literal case-sensitive default, and one
`utl::TextSearch` construction before the item loop for non-legacy modes.
Comment-only wiring cannot satisfy the source contract. Ten mutations prove
those requirements fail closed. The remaining 25 shipping integrations and
native build/runtime proof remain open; `runtime_verified: false` is intentional
until exact-build interaction evidence exists.

## No unsolicited startup or promotion prompts

The Windows no-nag contract forbids the automatic file-association, Welcome /
What’s New, Tip, donation/Get Involved, AutoCorrect-explanation, and
crash-report submission paths and the misleading crash-report opt-in. It also
requires the explicit Tip, What’s New,
feedback, and Windows association actions plus recovery, Safe Mode, incompatible
extension, read-only, macro, metadata, and credential safeguards to remain.
Mutation tests exercise every forbidden marker, removed surface, and retained
safeguard. This is source evidence; only a current native build and fresh plus
seeded legacy-profile startup runs can establish runtime behavior.

```sh
python bin/check-windows-no-nag-contract.py
python bin/test_windows_no_nag_contract.py
python bin/check-notification-store-contract.py
python bin/test_notification_store_contract.py
```

The notification-store contract covers the public state model, metadata-only
privacy default, deterministic redaction, genuine bare loose-object Git format,
fixed local `main`, process plus OS-held operation guarding, lock/CAS behavior,
atomic bulk transitions, recoverable tombstones, inverse-commit undo, bounded
preferences, pending-checkpoint retry without ref/object growth, schema
registration, and focused CppUnit wiring. It does not claim a visible manager
or runtime proof.

## Material token accessor

`vcl::MaterialTokens` (`include/vcl/MaterialTokens.hxx`,
`vcl/source/gdi/MaterialTokens.cxx`) is the public, queryable named-token table
over the Material widget definition's palette, shape and metric data. It reads
values exclusively from
`vcl/uiconfig/theme_definitions/material/definition.xml` through the existing
`WidgetDefinitionReader` reading path (the additive `readTokenTables` method
reuses `readColorPalette` plus the shape/metric readers). No hex, radius or
metric literal is duplicated in C++: only the semantic token *names* live there,
and the accessor rejects any file whose names diverge from that vocabulary.

`bin/check-material-token-accessor.py` proves 1:1 fidelity: the published name
vocabulary equals the definition's `<palette>` / `<shapes>` / `<metrics>` names
(both schemes identical, declared `std::array` sizes correct), the accessor
restates no hex literal, and it genuinely sources data through the reader path
and is registered as a compiled public VCL export.

```sh
python bin/check-material-token-accessor.py
python bin/test_material_token_accessor.py
```

The 16 mutation tests fail closed on a missing/extra/renamed token, an array
size mismatch, a definition drift, a hard-coded hex literal, a dropped reader
call, or a lost public export/registration. This is source evidence only; no
native build or runtime capture is claimed.

## Impress/Draw shell surfaces

`impress-draw-surfaces.json` registers the Draw shell surfaces from
[`docs/design/11-impress-draw.md`](../../docs/design/11-impress-draw.md) §11.2 --
`draw.tool-rail`, `draw.property-panel`, and `draw.status-bar`. Each surface
declares its owner source(s), the required `definition.xml` parts (with exact
fill/stroke/radius/stroke-width tokens and part sizing), any Material token
consumption, the status text model, and the no-selection/disabled policy.

`bin/check-impress-draw-surface-contract.py` cross-validates every declaration
against the tree:

- the docked tool rail's `toolbar/DrawBackgroundVert` fill, `ThumbVert` grip and
  `toolbar/Button` checked/hover/pressed/focused/disabled-checked states resolve
  to the exact definition tokens (token drift fails closed);
- the property panel's outlined `listbox` field and the normative 28 px
  (`size-compact-control`) `slider/Button` thumb plus horizontal track parts are
  the declared tokens, and `ApplyNoSelectionDisabledPolicy` keeps every
  Fill/Line control `set_visible(true)` + `set_sensitive(false)` (visible but
  disabled, no layout jump) in both the shared `LinePropertyPanelBase` and
  `AreaPropertyPanelBase`;
- the status bar composes `Page N of N · K objects selected`
  (`STR_SD_DRAW_OBJECTS_SELECTED`) in `drviewsa.cxx`, and the zoom control routes
  its Material text color through `vcl::MaterialTokens`, inert under the native
  theme.

```sh
python bin/check-impress-draw-surface-contract.py
python bin/test_impress_draw_surface_contract.py
```

Markers are checked in comment-stripped code, so comment-only wiring, a missing
policy control, a renamed policy method, a dropped status marker, wrong status
copy, or token drift each fail the 18 mutation tests. The dotted canvas grid /
workspace fill (a decorative custom-draw per the §11.2 accessibility note) is
deliberately out of scope and is not faked here. The surfaces are
source-declared for the Windows-first migration target; `runtime_verified` stays
`false` until an exact-build capture exists, and the contract claims no native
build, screenshot, or runtime evidence.
