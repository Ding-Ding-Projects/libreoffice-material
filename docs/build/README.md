# Build and distribution

This category documents how LibreOffice Material is built and how the results
reach a user's machine.

| Document | Covers |
| --- | --- |
| [`source-installer.md`](source-installer.md) | The touchless "build and run from source" Windows installer (`bin/Install-LibreOfficeMaterial-FromSource.ps1`) and its release workflow (`.github/workflows/source-installer.yml`). |
| [`windows-only.md`](windows-only.md) | The strictly-Windows-only build strip (stages 0-5): removing the iOS/Android/macOS/Quartz/Aqua/Qt/KF/GTK backends from the build graph, what is preserved and why, and which stages remain gated behind an MSI baseline. |
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

The two tag namespaces are disjoint by construction, so a release from one
channel can never collide with or overwrite a release from the other.
