# UI-scale control

A persisted whole-UI scale control on Tools > Options > Appearance, restoring
the feature upstream removed (TDF Bugzilla tdf#101646, 38 CC / 8 duplicates).
Shipped in commit `79b783fce`. It is modelled 1:1 on the existing
`MaterialDensity` control.

## Behavior

A labelled `GtkSpinButton` ("UI _scale:" with a mnemonic) is added to
`cui/uiconfig/ui/appearance.ui`. The value is a percentage read from and
written back to `officecfg` by `cui/source/options/appearance.cxx`
(`ResetMaterial` reads via the accessor's `::get()` into `set_value`;
`CommitMaterialAppearance` writes via `::set()` from `get_value`), exactly as
`MaterialDensity` is handled. Its "Apply" path is the existing restart path
shared by the Material appearance options — there is no live rescale.

## Configuration

`officecfg/registry/schema/org/openoffice/Office/Common.xcs`, `Appearance`
group:

| Property | Type | Default | Bounds |
| --- | --- | --- | --- |
| `MaterialUiScale` | `xs:short` | `100` (percent) | `minInclusive` 50, `maxInclusive` 400 |

- Accessor: `officecfg::Office::Common::Appearance::MaterialUiScale`.
- UI adjustment: `uiscaleadjustment`, range 50-400, step 25, spin id
  `uiscalespin`.
- The property's `<desc>` in the `.xcs` states honestly that it is stored-only
  in this stage.

## Failure modes

- **Stored-value only.** This stage persists and round-trips the value through
  the cui page, but **no metric consumes the scale factor yet** — the control
  is honest-inert, exactly like `MaterialDensity`. No visible rescaling occurs
  or is claimed.
- The round-trip must be bidirectional: a read-only or write-only binding is a
  broken round-trip and is caught fail-closed by the contract's read/write
  marker checks.
- The value is bounded by the schema's `minInclusive`/`maxInclusive` (50-400),
  clamping out-of-range persisted input.

## Security considerations

None beyond the bounded schema clamp (50-400%). The value is a percentage
stored in the user's own registry; it is not written into documents and drives
no privileged behavior.

## Verification status

**Source-implemented and compile-verified; STORED-VALUE-ONLY; RUNTIME
UNVERIFIED.**

- Cross-checked build-free by `qa/windows-ui-contract/material-ui-scale.json`,
  which carries `"runtime_verified": false` and `"stored_only": true`. Its
  mutation suite proves that promoting either flag fails closed.
- The metric that would actually rescale the UI is **deferred exactly like
  `MaterialDensity`**; both the `.xcs` `<desc>` and the contract say so.
- The feature commit `79b783fce` is an ancestor of successful MSI-123 at
  `952090ce2`; that workflow compiled the Windows product and produced the MSI.
  No runtime Options-page interaction or visible rescaling is claimed. The
  compiled stage remains intentionally stored-only because no metric consumes
  the value.
- The `.ui` change was verified gla11y-clean (0 new errors) — a reciprocal
  label-for/labelled-by pair and a mnemonic to the focusable spin button — the
  same class of a11y FATAL that broke the MSI build earlier this session.
