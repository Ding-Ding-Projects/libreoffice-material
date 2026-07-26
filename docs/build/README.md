# Build and distribution

This category documents how LibreOffice Material is built and how the results
reach a user's machine.

| Document | Covers |
| --- | --- |
| [`source-installer.md`](source-installer.md) | The touchless "build and run from source" Windows installer (`bin/Install-LibreOfficeMaterial-FromSource.ps1`) and its release workflow (`.github/workflows/source-installer.yml`). |
| [`windows-only.md`](windows-only.md) | The strictly-Windows-only build strip (stages 0-5): what was removed, what is preserved and why, and the successful MSI-123 compile evidence after stages 4+5 landed. |
| [`release-channel-integrity.md`](release-channel-integrity.md) | Separation of source-package and stable-MSI releases, the single-writer/ancestry-monotonic Latest policy, failure modes, and the 2026-07-26 incident/repair evidence. |
| [`ci-a11y-gate.md`](ci-a11y-gate.md) | The pre-push `gla11y` accessibility FATAL gate (`bin/check-ui-a11y-fatals.py`) that reproduces the build's exact gla11y invocation so `.ui` a11y FATALs are caught in seconds instead of ~3h into the MSI build. |
| [`../LOCAL_WINDOWS_BUILD.md`](../LOCAL_WINDOWS_BUILD.md) | Manual local Windows build notes. |

There is no HTTP or API surface in this category, so no Postman collection
applies to it.

## Distribution channels

Two independent channels ship from this repository, and neither waits on the
other:

| Channel | Workflow | Tags | Latency |
| --- | --- | --- | --- |
| Prebuilt Windows MSI | `.github/workflows/windows-installer.yml` | `windows-msi-<run>-<attempt>-<sha10>` | ~3 hours after a push |
| Source installer | `.github/workflows/source-installer.yml` | `source-installer-<run>-<attempt>-<sha10>` | ~2 minutes after a push |

The two tag namespaces are disjoint by construction, so their immutable
releases cannot collide. That alone does not protect GitHub's shared mutable
`Latest` pointer: source releases are now explicitly non-Latest, while stable
MSI promotion is serialized and may move only to the same commit or a
descendant. See [Release-channel integrity](release-channel-integrity.md).

As of 2026-07-26, the source workflow had published at least 21 releases, but the source
installer script itself remained unverified end to end. A pre-fix source
release also displaced the stable MSI from Latest, causing the public MSI
Latest URL to return 404. The source guard is present, and the one-time remote
repair restored `windows-msi-123-1-952090ce26` at `952090ce2`: Latest again has
exactly four assets, while the canonical MSI/XML/checksum routes returned HTTP
200 with 197,111,808/960/103-byte lengths. The three legacy unguarded runs were
cancelled and those API/route facts were rechecked afterwards.
Source run `30214506688` then verified the fail-closed exact-tag preflight.
Initial revised MSI run `30214506398` was rejected before job creation by
GitHub's 21,000-character expression limit; current source makes the 23 KB
publish scalar expression-free through standard `GITHUB_*` environment variables.
