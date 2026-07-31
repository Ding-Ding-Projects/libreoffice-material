# Host-composed Material surfaces

## Why this family exists

The ordinary rewrite-ledger predicates are intentionally strict for complete,
static forms. A normal dialog must expose a safe footer/default, Material
content spacing, a real ellipsized label, a real mnemonic target, a title, and
modal behavior. A normal panel body must expose Material spacing plus a real
label and mnemonic target. Those checks are useful only when the resource owns
those regions.

The family now contains 195 resources. It comprises 64 runtime-filled,
modeless, progress, close-only, or choice-dialog resources and 131 host-composed
fragments such as toolbar roots, notebookbars, atomic controls, embedded
canvases, and child containers. Their labels, insets, lifecycle actions, or
geometry belong to a C++ host, a wrapping page, or a specialized composition
contract. Their controls still render through the shared Windows Material
definition.

The 2026-07-28 adversarial audit independently confirmed 184 of these cases.
It found that satisfying the static predicate would require at least one real
regression: inventing a visible label, making a modeless tool modal, changing a
Cancel/Close/progress lifecycle into an affirmative action, shifting a
caret-anchored popup with wrapper margins, or changing the root class a host
loads by ID. Eleven later/current cases were re-audited from live source under the
same rule.

## Composition contract

[`host-composed-surfaces.json`](../../qa/windows-ui-contract/host-composed-surfaces.json)
is an explicit allow-list, not a relaxed heuristic. Each row records:

- the exact resource, owner, inventory ID, and former static family;
- the live ordinary-predicate failure and a semantic composition variant;
- a normalized source SHA-256, top-level object IDs/classes, and complete marker
  snapshot;
- whether the earlier audit supplied a `blocked-confirmed` verdict or the
  current source was re-audited; and
- ledger ownership by `host-composed-surface` / `host-composition`.

The contract also requires three independent renderer contracts:

1. `material-default-activation.json` proves the Material file renderer is
   unconditionally selected on Windows;
2. `component-gallery-coverage.json` proves every declared Material widget part
   and state remains indexed; and
3. `theme-resolution-routing.json` proves light/dark/high-contrast routing still
   reaches the same Material definition with native high-contrast fallback.

Any resource-byte change invalidates its digest. If a resource evolves until
the ordinary predicate genuinely passes, the checker fails and requires it to
leave this exception family. A new resource cannot enter by filename or by
merely failing a predicate: the surface-set digest, count, contract row, audit
status, classifier, and ledger must all change together with mutation coverage.

The first explicit post-wave promotion is `svx/uiconfig/ui/findbox.ui`. Its
previous panel credit depended on an empty hidden mnemonic label. The native
Find toolbar now owns a real adjacent builder and validated UNO handoff, so the
fake label was removed and the item-window resource moved into this composition
family with current-source audit provenance.

## What this does not claim

This family proves source composition and correct ownership. It does not prove
native pixels, host insertion at runtime, keyboard order, screen-reader output,
localization, scale, clipping, or performance. `runtime_verified` is therefore
`false`. Those remain build/runtime gates even when source coverage is complete.

## Verification

```sh
python bin/generate-host-composed-surface-contract.py --check
python bin/check-host-composed-surface-contract.py
python bin/test_host_composed_surface_contract.py
python bin/check-material-rewrite-ledger.py
python bin/test_material_rewrite_ledger.py
```

The generator is deterministic and refreshes the same locked set; it refuses to
retain a resource that has become a valid ordinary static form.
