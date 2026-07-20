# Disposable Windows installer lifecycle gate

This harness exercises the released Windows x64 MSI only inside Windows
Sandbox. It does not install, repair, upgrade, or uninstall anything on the
host. It also never deletes a pending-restart registry value. A changed reboot
indicator, exit code `3010`, or exit code `1641` fails the gate; closing the
disposable Sandbox removes all guest state.

The two pinned inputs are the exact normal releases at source commits
`577059e2741185b512c184c64685c16d335d10ea` and
`fbba560e27db26de605c40aa237c554c1f0744b1`. The guest verifies their byte
counts, SHA-256 values, ProductCodes, shared LibreOfficeDev UpgradeCode, and
absence of `ForceReboot` / `ScheduleReboot` in `InstallExecuteSequence` before
any mutation.

## Prerequisites

- 64-bit Windows 11 Pro with Windows Sandbox, Hyper-V, the Hyper-V hypervisor,
  and Virtual Machine Platform enabled;
- an active hypervisor and at least 8 GB of memory available to the Sandbox;
- network access during preparation so the host can fetch the two exact-tag
  GitHub assets;
- no need to install the Windows SDK or any test framework.

The generated Sandbox has networking, vGPU, audio input, video input, printer
redirection, and clipboard redirection disabled. It maps only a pinned input
directory as read-only and a new empty result directory as writable.
Before any MSI query or mutation, the guest positively requires the documented
`WDAGUtilityAccount` identity and SID RID, its Sandbox profile and reviewed
mapped entry point, Microsoft's virtual-machine identity, active hypervisor,
and enforced read-only input mapping. Failure occurs outside the cleanup and
shutdown block, so accidentally invoking the guest script on the host cannot
reach MSI cleanup or `shutdown.exe`.

## Static validation

Run the dependency-free source validator first:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\qa\windows-installer-lifecycle\Validate-Harness.ps1
```

This parses both PowerShell files and checks the launch boundary, pinned
release metadata, Sandbox isolation settings, lifecycle steps, exact updater
properties, reboot snapshots, zero-only acceptance, completion publication,
and absence of restart-flag deletion.

## Review-first execution

Preparation is deliberately the default and never starts Windows Sandbox:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\bin\Test-WindowsInstallerLifecycle.ps1 -Mode Prepare
```

The command prints a unique run directory and the exact explicit launch
command. Before launch, review `run-manifest.json`, `input\expected.json`, and
`LibreOfficeMaterial-InstallerLifecycle.wsb` in that directory.

Revalidate those reviewed bytes and policies without launching anything:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\bin\Test-WindowsInstallerLifecycle.ps1 `
  -Mode Inspect `
  -RunDirectory 'C:\absolute\prepared\run-directory'
```

Launch only the reviewed prepared run:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\bin\Test-WindowsInstallerLifecycle.ps1 `
  -Mode Launch `
  -RunDirectory 'C:\absolute\prepared\run-directory'
```

The host revalidates every prepared byte against the hard-coded release pins
and the current reviewed repository guest source, requires an empty output directory,
checks Sandbox/Hyper-V readiness, records host reboot and LibreOffice
registration state, launches the generated `.wsb`, and polls for an atomic
guest sentinel. It then requires the Windows Sandbox client processes to
dispose normally and never force-closes a timed-out Sandbox. Only after guest
output, disposal, and unchanged host-safety checks pass does it write
`host-verification.json` in the run root.

The guest performs, in order:

1. old exact-tag MSI install;
2. corrected same-version major update with `REINSTALL=ALL` and
   `REINSTALLMODE=vomus`;
3. corrected repair after moving `program\updchklo.dll` aside as the repair
   probe;
4. corrected ProductCode uninstall.

Every operation uses `/qn`, `/norestart`, `REBOOT=ReallySuppress`,
`MSIRESTARTMANAGERCONTROL=DisableShutdown`, and flushed verbose logging. The
old updater DLL hash must change to the corrected hash during update, repair
must restore the missing corrected DLL, and both ProductCodes must be absent at
the end with successful Windows Installer `ProductState = -1` queries. COM query
errors fail closed. Before/after fingerprints must match for every step and the
whole lifecycle, and the host independently recomputes each comparison. A
`COMPLETE.json` file is published only after every assertion and best-effort
final cleanup succeed.

Revalidate a completed result bundle without launching anything:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
  -File .\bin\Test-WindowsInstallerLifecycle.ps1 `
  -Mode Verify `
  -RunDirectory 'C:\absolute\prepared\run-directory'
```

## Evidence boundary

Preparing or statically validating this harness is not installer lifecycle
proof. Acceptance requires a real Sandbox run whose host-verified output
contains the four zero-exit lifecycle logs, before/after reboot snapshots,
`results.json`, a byte-verified `artifact-manifest.json`, and the atomic
`COMPLETE.json` sentinel, followed by verified Sandbox client disposal. The
current source updater and the lifecycle harness
both supply `MSIRESTARTMANAGERCONTROL=DisableShutdown`; the corrected public
`fbba560e2` release predates that sixth updater argument, so it must not be
reported as runtime proof for this additional protection.
