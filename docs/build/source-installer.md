# Source installer — build and run from source, touchless

> **Verification status: SCRIPT UNVERIFIED END TO END.** By 2026-07-26 the
> release workflow had published at least 20 source-installer releases, so its validation,
> packaging, and GitHub publication path has run. The installer script itself
> has never been observed provisioning a clean host and completing a real
> LibreOffice build and launch. A full Windows build takes roughly three hours
> and tens of gigabytes. Read
> [Verification status](#verification-status) before relying on anything here.

- Script: [`bin/Install-LibreOfficeMaterial-FromSource.ps1`](../../bin/Install-LibreOfficeMaterial-FromSource.ps1)
- Workflow: [`.github/workflows/source-installer.yml`](../../.github/workflows/source-installer.yml)

## What it is

One file that a user downloads and runs. It installs every build dependency,
clones this fork, configures and compiles it, installs shortcuts to the result,
and launches it. It asks nothing at any point: no `Read-Host`, no license
prompt, no UAC dead end — it re-launches itself elevated instead of failing.

## Behavior

The script runs in this order. Every dependency step detects first and installs
only when something is genuinely missing, so a second run is fast and harmless.

1. **PowerShell bootstrap.** If it started under Windows PowerShell 5.1 it
   locates or installs PowerShell 7 and re-launches itself under `pwsh`,
   forwarding every parameter. `LOM_NO_PWSH_BOOTSTRAP=1` suppresses the retry
   loop if PowerShell 7 cannot be installed.
2. **Self-elevation.** If not already Administrator it re-launches itself with
   `Start-Process -Verb RunAs`, waits, and propagates the child's exit code.
3. **Transcript and log directory.** `<BuildRoot>\installer-logs` is created and
   `Start-Transcript` begins. Every native command additionally writes its own
   log file there.
4. **Disk-space precheck.** Refuses to start with less than 60 GiB free on the
   build drive.
5. **Dependencies** — Git, 7-Zip, the Windows Python launcher (`py`), the
   Visual Studio 2022 Build Tools, and Cygwin. See
   [Mirrored dependency set](#mirrored-dependency-set).
6. **Source checkout.** Sets `core.autocrlf false`, clones or fetches into
   `<BuildRoot>\src`, checks out `-Ref` (falling back to `origin/<Ref>`), and
   asserts the worktree is LF — the Windows build refuses a CRLF checkout.
7. **Configure** with the CI flag set, followed by CI's two `config_host.mk`
   assertions (`DBCONNECTIVITY` in `BUILD_TYPE`, `ENABLE_CLI=TRUE`).
8. **Build** with the LibreOffice MSVC `make` at `-j<JobCount>` and `CL=/FS`.
9. **Install and launch.** Locates `instdir\program\soffice.exe`, creates a
   Start-menu shortcut, and starts it unless `-SkipLaunch`.
10. **Summary.** Elapsed time, what was installed, what was already present, the
    office path, and the log locations.

## Mirrored dependency set

Nothing here was invented. Each list is copied from
`.github/workflows/windows-installer.yml` so a local build matches CI.

### Visual Studio and Windows SDK (workflow lines 117–145)

Detection uses `vswhere -latest -version '[17.0,18.0)' -products '*' -requires`
with exactly the CI component set, then additionally proves the bundled CMake
and the ATL headers exist on disk:

- `Microsoft.VisualStudio.Component.VC.Tools.x86.x64`
- `Microsoft.VisualStudio.Component.VC.CLI.Support`
- `Microsoft.VisualStudio.Component.VC.ATL`
- `Microsoft.VisualStudio.Component.VC.Redist.MSM`
- `Microsoft.VisualStudio.Component.VC.CMake.Project`

When the check fails, the script either `vs_installer.exe modify`s the existing
installation or downloads `https://aka.ms/vs/17/release/vs_BuildTools.exe` and
runs it `--quiet --wait --norestart --nocache` with the
`Microsoft.VisualStudio.Workload.VCTools` workload, the five components above,
`Windows11SDK.22621` and `Windows10SDK.20348`, and `--includeRecommended`. The
same `vswhere` validation then has to pass or the script stops.

> The workload/SDK component ids are the script's own addition: CI receives a
> pre-provisioned `windows-2022` runner and never installs Visual Studio, so
> there is no CI line to copy for the *install* side. Only the *validation* side
> is verbatim.

### Cygwin packages (workflow lines 278–282, verbatim)

```
autoconf, automake, bison, cabextract, diffutils, file, flex, gawk,
gettext-devel, git, gperf, libxml2-devel, libxslt, make, nasm, patch, perl,
perl-Archive-Zip, perl-Font-TTF, perl-IO-String, pkg-config, python3, rsync,
unzip, wget, which, zip
```

Installed by the official `https://cygwin.com/setup-x86_64.exe`, whose
Authenticode signature is checked and must be `Valid` before it is executed,
with `-q -n -N -d -R C:\cygwin64 -s https://mirrors.kernel.org/sourceware/cygwin/ -P <packages>`.
Two LibreOffice-supplied MSVC tools are then fetched into
`C:\cygwin64\opt\lo\bin` and SHA-256 logged:

- `make.exe` from `https://dev-www.libreoffice.org/bin/cygwin/make-4.2.1-msvc.exe`
- `pkgconf-2.4.3.exe` from `https://dev-www.libreoffice.org/extern/pkgconf-2.4.3.exe`

`bash.exe` is copied to `cygbash.exe`, matching CI's custom shell.

### Build-tool validation (workflow line 324, verbatim)

Every build stage runs under `bash --noprofile --norc -o igncr -eo pipefail`
with `PATH=/opt/lo/bin:/usr/local/bin:/usr/bin:/bin:$PATH`. The validation
script asserts `uname -o` is `Cygwin`, that each of

```
autoconf automake bison flex gawk gperf nasm ninja patch perl python3 rsync unzip wget zip
```

resolves, that `perl -MArchive::Zip` and `perl -MFont::TTF::Font` load, that
`/opt/lo/bin/make.exe --version` reports `Built for Windows`, that
`pkgconf-2.4.3.exe` runs, that `nasm` is `/usr/bin/nasm`, and that its version
sorts at or above 2.16. This same validation doubles as the idempotency probe:
an existing Cygwin that passes it is left completely untouched.

### Configure flags (workflow lines 355–377, verbatim)

```
--host=x86_64-pc-cygwin --with-visual-studio=2022 --with-windows-sdk=10.0
--with-package-format=msi --with-external-tar=<BuildRoot>/tarballs
--with-lang=en-US --enable-online-update
--with-privacy-policy-url=https://github.com/Ding-Ding-Projects/libreoffice-material/blob/main/PRIVACY.md
--enable-python=fully-internal --without-java --without-junit --without-dotnet
--without-help --without-helppack-integration --without-myspell-dicts
--without-doxygen --without-fonts --with-galleries=no --disable-odk
--disable-ccache --disable-pdfium --enable-database-connectivity
--disable-cairo-canvas
```

The only edit is `--with-external-tar`, which CI hard-codes to `C:/lo/tarballs`
and the script rewrites to sit under `-BuildRoot`.

## Auto-fix loop

`configure` and `make` each run through the same retry wrapper.

On a non-zero exit the wrapper writes `<stage>-attempt-<n>.log`, takes the last
200 lines of output, and invokes the `opencode` CLI agent non-interactively:

```
opencode run --auto --dir <checkout> --title "auto-fix <stage> attempt <n>" "<prompt>"
```

`run` is opencode's documented non-interactive entry point — `opencode --help`
lists `opencode run [message..]` as "run opencode with a message", while bare
`opencode [project]` is the default TUI. `--auto` ("auto-approve permissions
that are not explicitly denied") is what stops a permission prompt from hanging
an unattended run, and `--dir` selects the directory to operate in. The flags
were read from `opencode --help` and `opencode run --help` on the authoring
machine rather than guessed.

The prompt names the failing stage, the exact failing command, and the log
tail, and instructs the agent to make the smallest correct source change — not
to weaken the configure flags, disable tests, or fake success.

Resolution order for the executable: `opencode` on `PATH`, then
`%APPDATA%\npm\opencode.ps1` invoked through `pwsh -NoProfile -ExecutionPolicy Bypass -File`,
then `%APPDATA%\npm\opencode.cmd`. If none resolves, the run stops with a clear
failure rather than looping.

The stage then reruns. After `-MaxFixAttempts` failed repairs the script exits
non-zero with the last log path. It never reports success on failure, and it
never launches an office that was not produced.

## Configuration

| Parameter | Default | Meaning |
| --- | --- | --- |
| `-Ref` | `main` | Branch, tag, or SHA to build. |
| `-BuildRoot` | `C:\lo` | Root for `src`, `build`, `tarballs`, `installer-logs`. |
| `-Unattended` | `$true` | Keeps every step non-interactive. |
| `-AutoFix` | `$true` | Enables the opencode repair loop. |
| `-MaxFixAttempts` | `3` | Repair attempts per failing stage. |
| `-SkipLaunch` | off | Build but do not start the office. |
| `-JobCount` | derived | Parallel build jobs; defaults to half the CPU count, clamped to 2–8. |

## Failure modes

| Symptom | Cause | What the script does |
| --- | --- | --- |
| UAC declined | User cancels the elevation prompt | `Start-Process -Verb RunAs` throws; the run stops. It cannot proceed unelevated. |
| Fewer than 60 GiB free | Insufficient disk | Stops before touching anything, naming the drive and the shortfall. |
| Cygwin setup signature not `Valid` | Tampered or truncated download | Refuses to execute the installer. |
| Cygwin present but missing packages | Partial prior install | Re-runs setup with the full package list, then re-validates. |
| `vswhere` finds no complete VS | Missing components | Modifies the existing install, else installs Build Tools, then re-validates or stops. |
| CRLF worktree | `core.autocrlf` at machine scope | Detected via `git ls-files --eol`; stops with the CI error message. |
| `configure` or `make` fails | Source or environment defect | Auto-fix loop, then a non-zero exit naming the log. |
| `opencode` not installed | Agent unavailable | Warns and stops rather than looping uselessly. |
| Build "succeeds" with no `soffice.exe` | Silent packaging failure | Treated as a failure; nothing is launched. |
| Network flake | Transient | Downloads retry five times with increasing backoff. |

## Security considerations

State plainly what this script does, because it is a lot:

- **It self-elevates to Administrator.** It re-launches itself with
  `-Verb RunAs`. Anyone running it grants it full control of the machine.
- **It installs system-wide software** — Git, 7-Zip, Python, the Visual Studio
  2022 Build Tools, and Cygwin — via `winget`/`choco` with every license
  agreement pre-accepted (`--accept-package-agreements`,
  `--accept-source-agreements`, `--disable-interactivity`, `-y --accept-license`).
  The user accepts those licenses by running the script.
- **It downloads and executes third-party binaries** from `cygwin.com`,
  `aka.ms`, and `dev-www.libreoffice.org`. Only the Cygwin setup is
  signature-verified; the two LibreOffice tools are size-checked and SHA-256
  *logged*, not pinned. This matches CI, which does the same — but it means a
  compromised upstream mirror would be executed. Pinning those two hashes is a
  known, deliberate gap.
- **`choco install` passes `--ignore-checksums`** as a fallback path. That
  weakens integrity checking; it exists only because Chocolatey packages often
  outrun their published checksums, and `winget` is always tried first.
- **The auto-fix loop runs an LLM agent with `--auto`**, which auto-approves
  tool permissions. That agent can modify files in the checkout and run
  commands, elevated. `-AutoFix $false` disables it entirely; use that if an
  autonomous agent editing source on an elevated session is not acceptable.
- **It writes no secrets and reads none.** No token, credential, or telemetry is
  collected or transmitted. Logs contain build output and command lines only.
- **Logs may contain local paths and usernames.** Review
  `<BuildRoot>\installer-logs` before sharing a transcript.

Anyone who does not want all of the above should not run the script; the
prebuilt MSI release is the alternative.

## Release workflow

`.github/workflows/source-installer.yml` runs on every push to `main` and on
`workflow_dispatch`, on `ubuntu-latest`, with a 15-minute timeout. It is
deliberately independent of `windows-installer.yml`: it never waits on, reads
from, or gates on the MSI job, so a downloadable installer exists roughly two
minutes after a push instead of three hours.

Steps: check out; validate the script (assert no `Read-Host`, assert the
mirrored markers are present); run the build-free fleet-closure and release-
channel integrity checker/mutation suites; parse the script with the PowerShell parser;
stage a zip of the script plus `README.txt` and `SHA256SUMS.txt`; upload the zip
as a workflow artifact with `if: always()` and `continue-on-error: true` so it
survives a failure, matching the failure-proof pattern in
`windows-installer.yml`; then publish a normal non-draft release that is
explicitly marked `--latest=false`.

**Tagging:** `source-installer-<run_number>-<attempt>-<sha10>`. Prebuilt MSI
releases use `windows-msi-<run_number>-<attempt>-<sha10>`, so the channel
namespaces are disjoint. Before creating a release, the publish step performs a
fail-closed matching-ref lookup for the exact source tag; an API error is not
accepted as absence, and an existing ref or release is never overwritten. It
also reads the repository's uncached Latest release both before and after
publication, failing unless that release differs from the source tag and
contains exactly the canonical `LibreOfficeMaterial-Windows-x64.msi` asset.
The preflight prevents a new release when inherited remote state is already
wrong; the workflow still cannot infer or perform an operational repair. After
publication it also asserts `isDraft == false`.

Source release tags are excluded from the Windows UI contract's `push` trigger.
That contract still runs for every branch push, pull request, and manual
dispatch, but publishing this fast source package no longer launches a duplicate
full static fleet for the same commit. The complete mutable-Latest policy is in
[`release-channel-integrity.md`](release-channel-integrity.md).

## Verification status

What was done:

- The dependency lists, validation logic, and configure flags were read
  directly out of `.github/workflows/windows-installer.yml` and are cited above
  with line numbers.
- The opencode invocation form was taken from `opencode --help` and
  `opencode run --help` on the authoring machine.
- The workflow YAML was parsed successfully.
- The repository's build-free check/test gate was run and still passes.
- At least twenty `source-installer-*` releases had been published by 2026-07-26.
  This is real workflow packaging/publication evidence, not execution evidence
  for the PowerShell installer inside the zip.
- Commit `27a7c7d00` added `--latest=false`, the stable-MSI post-publication
  assertion, tag-push exclusion for the Windows UI contract, and CI fleet-
  closure/release-channel mutation checks. The one-time remote repair restored
  `windows-msi-123-1-952090ce26` at `952090ce2` as Latest with four assets and
  HTTP-200 MSI/XML/checksum routes. Run `30213637973` attempt 2 then published
  `source-installer-20-2-27a7c7d000` successfully while preserving MSI-123 as
  Latest. The newer fail-closed matching-ref preflight remains source/static
  evidence until the follow-up push runs this workflow.

What was **not** done, and must not be claimed:

- The installer has never been executed, at all — not the elevation path, not a
  dependency install, not a checkout, not a configure, not a build, not a
  launch.
- The auto-fix loop has never fired against a real failure.
- No clean Windows host has run the packaged script through dependency
  provisioning, checkout, configure, compile, shortcut creation, and launch.
- The pre-fix source channel displaced the Windows MSI from GitHub Latest and
  made the public Latest MSI URL return 404. The source policy prevents a
  repeat, and the one-time repair plus public reachability checks have completed.
  The three legacy unguarded MSI runs were cancelled and Latest was rechecked
  afterwards; no source-script runtime claim follows from this release repair.

The installer is written to be defensive and log-heavy precisely because of
this. The transcript under `<BuildRoot>\installer-logs` is the only acceptable
evidence that any particular run did what it says.
