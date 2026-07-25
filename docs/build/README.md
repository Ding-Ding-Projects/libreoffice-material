# Build and distribution

This category documents how LibreOffice Material is built and how the results
reach a user's machine.

| Document | Covers |
| --- | --- |
| [`source-installer.md`](source-installer.md) | The touchless "build and run from source" Windows installer (`bin/Install-LibreOfficeMaterial-FromSource.ps1`) and its release workflow (`.github/workflows/source-installer.yml`). |
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
