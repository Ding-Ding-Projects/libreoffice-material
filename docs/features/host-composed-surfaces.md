# Host-composed Material surfaces

## Behavior

One hundred ninety-four registered resources render through LibreOffice's
globally activated Windows Material widget definition while their surrounding
host owns anatomy that does not live in the `.ui` file. The family includes 64
dialog variants and 130 child/atomic fragments. It preserves each resource's
real behavior: modeless tools stay modeless, progress and close-only dialogs do
not gain fake affirmative actions, runtime pages keep their existing owners,
and popup/notebookbar/toolbar roots keep the geometry and root identity their
host expects.

No decorative labels, hidden mnemonic targets, orphan grids, or wrapper margins
are added merely to satisfy a scanner.

## Configuration

There is no user setting for this contract. On Windows,
`material-default-activation.json` owns selection of
`vcl/uiconfig/theme_definitions/material/definition.xml`; the resources in this
family inherit that shared rendering like every other VCL control. The explicit
surface registry is generated with:

```sh
python bin/generate-host-composed-surface-contract.py
```

Generation preserves the locked surface set after its first creation and
refreshes only live hashes/marker snapshots. It refuses a surface whose ordinary
static predicate now passes.

## Failure modes

- A changed `.ui` file invalidates its normalized SHA-256 and marker snapshot.
- A renamed or substituted surface invalidates the fixed 194-surface set digest.
- A drifted root ID/class, owner, inventory row, former family, or predicate
  reason fails closed.
- Removing global Material activation, component-part coverage, or theme routing
  invalidates the renderer dependency chain.
- If a resource becomes a complete static form, remaining in the exception
  family is an error; it must migrate back to its ordinary family.
- Native host insertion, clipping, focus, scale, localization, accessibility,
  and performance can still fail despite source conformance.

## Security considerations

The contract deliberately preserves modal/modeless and decision semantics. It
does not turn Cancel, Close, Help, progress interruption, or a modeless tool into
an affirmative default. It changes no persistence, data access, privilege,
network, credential, signature, or macro-security path. Security prompts that
also carry specialized contracts retain those stricter contracts.

## Verification status

Build-free verification is provided by:

```sh
python bin/generate-host-composed-surface-contract.py --check
python bin/check-host-composed-surface-contract.py
python bin/test_host_composed_surface_contract.py
python bin/check-material-rewrite-ledger.py
python bin/test_material_rewrite_ledger.py
```

The contract records 184 prior `blocked-confirmed` audits and 10 current-source
re-audits. It proves source composition only. `runtime_verified` is `false`; no
new native capture or interaction result is claimed.

## Related documentation

- [Design rationale and contract anatomy](../design/host-composed-material-surfaces.md)
- [Adversarial per-surface audit](../design/material-rewrite-wave-2026-07-28-evidence.json)
- [Windows UI contract index](../../qa/windows-ui-contract/README.md#host-composed-material-surfaces)
- [Material rewrite ledger](../../qa/windows-ui-contract/material-rewrite-ledger.json)

