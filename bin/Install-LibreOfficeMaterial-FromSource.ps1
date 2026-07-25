<#
.SYNOPSIS
    Touchless "build and run from source" installer for the LibreOffice Material
    Windows fork.

.DESCRIPTION
    One file. The user runs it. It self-elevates, installs every build
    dependency, clones this repository at the requested ref, configures and
    builds a Windows x64 LibreOfficeDev with the Material Design 3 UI, then
    launches the result. No prompts, ever.

    Every dependency step and every build flag in this script is mirrored from
    .github/workflows/windows-installer.yml so that a local build matches CI:

      * Visual Studio / Windows SDK component set
            <- "Validate Visual Studio and Windows SDK packaging tools"
               (windows-installer.yml lines 117-145)
      * Cygwin package set
            <- "Install Cygwin build prerequisites"
               (windows-installer.yml lines 278-282)
      * Build-tool validation loop
            <- "Validate Cygwin and LibreOffice build tools"
               (windows-installer.yml line 324)
      * autogen.sh flag set
            <- "Configure Windows x64 LibreOfficeDev build"
               (windows-installer.yml lines 355-377)

    If configure or make fails, the script feeds the failing command plus the
    tail of the log to the `opencode` CLI agent in its non-interactive `run`
    mode and retries, up to -MaxFixAttempts times.

.NOTES
    VERIFICATION STATUS: UNVERIFIED END TO END.

    This script has never been executed to completion. A full LibreOffice
    Windows build takes roughly three hours and tens of gigabytes, and the
    machine this script was authored on has no build root. Individual pieces
    (parameter handling, dependency detection, the workflow-mirrored package and
    flag lists, and the opencode invocation form) were reviewed against the CI
    workflow and against `opencode run --help`, but the end-to-end path -- and
    in particular the auto-fix loop and the post-build launch -- has NOT been
    observed working. Treat the first run as the first test. The transcript in
    the build root is the evidence; read it before believing any claim of
    success.

.PARAMETER Ref
    Git ref, tag or SHA to build. Default 'main'.

.PARAMETER BuildRoot
    Root directory for checkout, build tree, tarballs and logs. Default 'C:\lo'.

.PARAMETER Unattended
    Keep every step non-interactive. Default $true. Setting it to $false does
    not add prompts; it only relaxes the refusal to continue without a console.

.PARAMETER AutoFix
    Invoke the opencode CLI agent to repair build failures. Default $true.

.PARAMETER MaxFixAttempts
    Maximum opencode repair attempts per failing stage. Default 3.

.PARAMETER SkipLaunch
    Do not start soffice.exe after a successful build.

.PARAMETER JobCount
    Parallel native build jobs. Defaults to a value derived from CPU count.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Install-LibreOfficeMaterial-FromSource.ps1

.EXAMPLE
    pwsh -File .\Install-LibreOfficeMaterial-FromSource.ps1 -Ref main -BuildRoot D:\lo -SkipLaunch
#>

[CmdletBinding()]
param(
    [string] $Ref = 'main',
    [string] $BuildRoot = 'C:\lo',
    [bool]   $Unattended = $true,
    [bool]   $AutoFix = $true,
    [int]    $MaxFixAttempts = 3,
    [switch] $SkipLaunch,
    [int]    $JobCount = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# --------------------------------------------------------------------------
# Constants mirrored from .github/workflows/windows-installer.yml
# --------------------------------------------------------------------------

$RepositoryUrl = 'https://github.com/Ding-Ding-Projects/libreoffice-material.git'
$CygwinRoot = 'C:\cygwin64'
$CygwinMirror = 'https://mirrors.kernel.org/sourceware/cygwin/'
$OpenCodeScript = Join-Path $env:APPDATA 'npm\opencode.ps1'
$MinimumFreeBytes = 60GB

# windows-installer.yml lines 278-282, verbatim.
$CygwinPackages = @(
    'autoconf', 'automake', 'bison', 'cabextract', 'diffutils', 'file',
    'flex', 'gawk', 'gettext-devel', 'git', 'gperf', 'libxml2-devel',
    'libxslt', 'make', 'nasm', 'patch', 'perl', 'perl-Archive-Zip',
    'perl-Font-TTF', 'perl-IO-String', 'pkg-config', 'python3', 'rsync',
    'unzip', 'wget', 'which', 'zip'
)

# windows-installer.yml line 324, verbatim.
$RequiredCygwinTools = @(
    'autoconf', 'automake', 'bison', 'flex', 'gawk', 'gperf', 'nasm', 'ninja',
    'patch', 'perl', 'python3', 'rsync', 'unzip', 'wget', 'zip'
)

# windows-installer.yml lines 124-129: the -requires set proven by CI.
$VisualStudioComponents = @(
    'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
    'Microsoft.VisualStudio.Component.VC.CLI.Support',
    'Microsoft.VisualStudio.Component.VC.ATL',
    'Microsoft.VisualStudio.Component.VC.Redist.MSM',
    'Microsoft.VisualStudio.Component.VC.CMake.Project'
)

# The workload plus SDKs that provide the components above.
$VisualStudioInstallArguments = @(
    '--quiet', '--wait', '--norestart', '--nocache',
    '--add', 'Microsoft.VisualStudio.Workload.VCTools',
    '--add', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
    '--add', 'Microsoft.VisualStudio.Component.VC.CLI.Support',
    '--add', 'Microsoft.VisualStudio.Component.VC.ATL',
    '--add', 'Microsoft.VisualStudio.Component.VC.Redist.MSM',
    '--add', 'Microsoft.VisualStudio.Component.VC.CMake.Project',
    '--add', 'Microsoft.VisualStudio.Component.Windows11SDK.22621',
    '--add', 'Microsoft.VisualStudio.Component.Windows10SDK.20348',
    '--includeRecommended'
)

# windows-installer.yml lines 355-377: the exact configure flag set.
# --with-external-tar is rewritten at runtime to live under -BuildRoot.
$AutogenFlags = @(
    '--host=x86_64-pc-cygwin',
    '--with-visual-studio=2022',
    '--with-windows-sdk=10.0',
    '--with-package-format=msi',
    '--with-external-tar=@TARBALLS@',
    '--with-lang=en-US',
    '--enable-online-update',
    '--with-privacy-policy-url=https://github.com/Ding-Ding-Projects/libreoffice-material/blob/main/PRIVACY.md',
    '--enable-python=fully-internal',
    '--without-java',
    '--without-junit',
    '--without-dotnet',
    '--without-help',
    '--without-helppack-integration',
    '--without-myspell-dicts',
    '--without-doxygen',
    '--without-fonts',
    '--with-galleries=no',
    '--disable-odk',
    '--disable-ccache',
    '--disable-pdfium',
    '--enable-database-connectivity',
    '--disable-cairo-canvas'
)

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

$script:StartTime = Get-Date
$script:LogDirectory = Join-Path $BuildRoot 'installer-logs'
$script:Installed = [System.Collections.Generic.List[string]]::new()
$script:Skipped = [System.Collections.Generic.List[string]]::new()
$script:TranscriptPath = $null

function Write-Stamp {
    param(
        [Parameter(Mandatory)] [string] $Message,
        [ValidateSet('INFO', 'WARN', 'FAIL', 'STEP', 'OK')] [string] $Level = 'INFO'
    )
    $stamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $line = "[$stamp] [$Level] $Message"
    switch ($Level) {
        'FAIL' { Write-Host $line -ForegroundColor Red }
        'WARN' { Write-Host $line -ForegroundColor Yellow }
        'STEP' { Write-Host '' ; Write-Host $line -ForegroundColor Cyan }
        'OK'   { Write-Host $line -ForegroundColor Green }
        default { Write-Host $line }
    }
}

function Stop-WithFailure {
    param([Parameter(Mandatory)] [string] $Message)
    Write-Stamp -Level FAIL -Message $Message
    if ($script:TranscriptPath) {
        Write-Stamp -Level FAIL -Message "Full transcript: $script:TranscriptPath"
    }
    Write-Stamp -Level FAIL -Message 'The build did NOT succeed. Nothing was launched.'
    try { Stop-Transcript | Out-Null } catch { }
    exit 1
}

# --------------------------------------------------------------------------
# Elevation and shell bootstrap
# --------------------------------------------------------------------------

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-ForwardedArguments {
    $forwarded = @(
        '-Ref', $Ref,
        '-BuildRoot', $BuildRoot,
        '-Unattended', ([string]$Unattended),
        '-AutoFix', ([string]$AutoFix),
        '-MaxFixAttempts', ([string]$MaxFixAttempts),
        '-JobCount', ([string]$JobCount)
    )
    if ($SkipLaunch) { $forwarded += '-SkipLaunch' }
    return $forwarded
}

function Invoke-SelfRelaunch {
    param(
        [Parameter(Mandatory)] [string] $Executable,
        [Parameter(Mandatory)] [bool] $Elevate,
        [Parameter(Mandatory)] [string] $Why
    )
    Write-Stamp -Level STEP -Message "Relaunching: $Why"
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath) + (Get-ForwardedArguments)
    $startParameters = @{
        FilePath     = $Executable
        ArgumentList = $arguments
        Wait         = $true
        PassThru     = $true
    }
    if ($Elevate) { $startParameters['Verb'] = 'RunAs' }
    $process = Start-Process @startParameters
    exit $process.ExitCode
}

function Get-PwshPath {
    $command = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($candidate in @(
            "$env:ProgramFiles\PowerShell\7\pwsh.exe",
            "${env:ProgramFiles(x86)}\PowerShell\7\pwsh.exe",
            "$env:LOCALAPPDATA\Microsoft\WindowsApps\pwsh.exe")) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    return $null
}

# --------------------------------------------------------------------------
# Command helpers
# --------------------------------------------------------------------------

function Invoke-Native {
    <#
        Runs a native command, streams and captures output, and returns an
        object carrying the exit code and the captured text. It never throws on
        a non-zero exit code; the caller decides.
    #>
    param(
        [Parameter(Mandatory)] [string] $FilePath,
        [string[]] $Arguments = @(),
        [string] $LogFile,
        [string] $WorkingDirectory
    )
    $displayed = "$FilePath $($Arguments -join ' ')"
    Write-Stamp -Message "exec: $displayed"

    $previousLocation = $null
    if ($WorkingDirectory) {
        $previousLocation = (Get-Location).Path
        Set-Location -LiteralPath $WorkingDirectory
    }
    try {
        $output = & $FilePath @Arguments 2>&1 | ForEach-Object {
            $text = [string]$_
            Write-Host $text
            $text
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        if ($previousLocation) { Set-Location -LiteralPath $previousLocation }
    }

    $joined = ($output -join [Environment]::NewLine)
    if ($LogFile) {
        $directory = Split-Path -Parent $LogFile
        if ($directory -and -not (Test-Path -LiteralPath $directory)) {
            New-Item -ItemType Directory -Force -Path $directory | Out-Null
        }
        Set-Content -LiteralPath $LogFile -Value $joined -Encoding UTF8
    }
    return [pscustomobject]@{
        Command  = $displayed
        ExitCode = if ($null -eq $exitCode) { 0 } else { [int]$exitCode }
        Output   = $joined
        LogFile  = $LogFile
    }
}

function Test-CommandExists {
    param([Parameter(Mandatory)] [string] $Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = (@($machine, $user) | Where-Object { $_ }) -join ';'
    foreach ($extra in @("$CygwinRoot\bin", "$CygwinRoot\opt\lo\bin")) {
        if ((Test-Path -LiteralPath $extra) -and ($env:Path -notlike "*$extra*")) {
            $env:Path = "$extra;$env:Path"
        }
    }
}

function Invoke-Winget {
    <#
        Installs a winget package with every agreement flag pre-accepted so no
        prompt can ever appear. Returns $true when winget reports success or
        "already installed".
    #>
    param(
        [Parameter(Mandatory)] [string] $Id,
        [string[]] $Extra = @()
    )
    if (-not (Test-CommandExists 'winget')) { return $false }
    $arguments = @(
        'install', '--id', $Id, '--exact', '--silent',
        '--accept-package-agreements', '--accept-source-agreements',
        '--disable-interactivity', '--source', 'winget'
    ) + $Extra
    $result = Invoke-Native -FilePath 'winget' -Arguments $arguments `
        -LogFile (Join-Path $script:LogDirectory ("winget-$($Id -replace '[^\w.-]', '_').log"))
    # 0 = installed, -1978335189 = already installed, -1978335135 = no upgrade.
    return ($result.ExitCode -in @(0, -1978335189, -1978335135))
}

function Invoke-Choco {
    param([Parameter(Mandatory)] [string] $Package)
    if (-not (Test-CommandExists 'choco')) { return $false }
    $result = Invoke-Native -FilePath 'choco' -Arguments @(
        'install', $Package, '-y', '--no-progress', '--limit-output',
        '--accept-license', '--ignore-checksums'
    ) -LogFile (Join-Path $script:LogDirectory "choco-$Package.log")
    return ($result.ExitCode -in @(0, 1641, 3010))
}

function Get-RemoteFile {
    param(
        [Parameter(Mandatory)] [string] $Uri,
        [Parameter(Mandatory)] [string] $Destination,
        [int] $MinimumBytes = 1
    )
    $directory = Split-Path -Parent $Destination
    if ($directory -and -not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    Write-Stamp -Message "download: $Uri -> $Destination"
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            Invoke-WebRequest -Uri $Uri -OutFile $Destination -UseBasicParsing -TimeoutSec 900
            $size = (Get-Item -LiteralPath $Destination).Length
            if ($size -ge $MinimumBytes) {
                Write-Stamp -Level OK -Message ("downloaded {0:N0} bytes" -f $size)
                return
            }
            Write-Stamp -Level WARN -Message "Downloaded file is too small ($size bytes); retrying."
        }
        catch {
            Write-Stamp -Level WARN -Message "Download attempt $attempt failed: $($_.Exception.Message)"
        }
        Start-Sleep -Seconds (5 * $attempt)
    }
    Stop-WithFailure "Could not download $Uri after 5 attempts."
}

# --------------------------------------------------------------------------
# Cygwin bridge
# --------------------------------------------------------------------------

function Get-CygwinBash {
    $bash = Join-Path $CygwinRoot 'bin\bash.exe'
    if (-not (Test-Path -LiteralPath $bash)) {
        Stop-WithFailure "Cygwin bash is missing at $bash."
    }
    return $bash
}

function ConvertTo-CygwinPath {
    param([Parameter(Mandatory)] [string] $WindowsPath)
    $cygpath = Join-Path $CygwinRoot 'bin\cygpath.exe'
    $converted = & $cygpath -u $WindowsPath
    if ($LASTEXITCODE -ne 0 -or -not $converted) {
        Stop-WithFailure "cygpath could not convert $WindowsPath."
    }
    return ([string]$converted).Trim()
}

function Invoke-CygwinScript {
    <#
        Runs a bash script under Cygwin with the same PATH ordering and shell
        options the CI workflow uses:
            cygbash --noprofile --norc -o igncr -eo pipefail
    #>
    param(
        [Parameter(Mandatory)] [string] $Script,
        [string] $LogFile
    )
    $bash = Get-CygwinBash
    $scriptFile = Join-Path $script:LogDirectory ("cygwin-" + [guid]::NewGuid().ToString('N') + '.sh')
    $body = @(
        'export PATH="/opt/lo/bin:/usr/local/bin:/usr/bin:/bin:$PATH"',
        $Script
    ) -join "`n"
    # Cygwin needs LF; -o igncr tolerates CR but the file is written clean.
    [System.IO.File]::WriteAllText($scriptFile, ($body -replace "`r`n", "`n") + "`n",
        [System.Text.UTF8Encoding]::new($false))
    $unixScript = ConvertTo-CygwinPath $scriptFile
    try {
        return Invoke-Native -FilePath $bash `
            -Arguments @('--noprofile', '--norc', '-o', 'igncr', '-eo', 'pipefail', $unixScript) `
            -LogFile $LogFile
    }
    finally {
        Remove-Item -LiteralPath $scriptFile -Force -ErrorAction SilentlyContinue
    }
}

# --------------------------------------------------------------------------
# Dependency installation (each step detects first, installs only if missing)
# --------------------------------------------------------------------------

function Install-Git {
    Write-Stamp -Level STEP -Message 'Dependency: Git for Windows'
    Update-SessionPath
    if (Test-CommandExists 'git') {
        $version = (& git --version) -join ''
        Write-Stamp -Level OK -Message "Already present: $version"
        $script:Skipped.Add('Git') ; return
    }
    if (-not (Invoke-Winget -Id 'Git.Git')) {
        if (-not (Invoke-Choco 'git')) {
            Stop-WithFailure 'Neither winget nor choco could install Git.'
        }
    }
    Update-SessionPath
    if (-not (Test-CommandExists 'git')) {
        Stop-WithFailure 'Git is still not on PATH after installation.'
    }
    $script:Installed.Add('Git')
}

function Install-SevenZip {
    Write-Stamp -Level STEP -Message 'Dependency: 7-Zip'
    Update-SessionPath
    $known = @("$env:ProgramFiles\7-Zip\7z.exe", "${env:ProgramFiles(x86)}\7-Zip\7z.exe")
    if ((Test-CommandExists '7z') -or ($known | Where-Object { Test-Path -LiteralPath $_ })) {
        Write-Stamp -Level OK -Message 'Already present.'
        $script:Skipped.Add('7-Zip') ; return
    }
    if (Invoke-Winget -Id '7zip.7zip') { $script:Installed.Add('7-Zip') }
    elseif (Invoke-Choco '7zip') { $script:Installed.Add('7-Zip') }
    else { Write-Stamp -Level WARN -Message '7-Zip could not be installed; continuing (it is optional).' }
    Update-SessionPath
}

function Get-VsWherePath {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path -LiteralPath $vswhere) { return $vswhere }
    return $null
}

function Get-ValidatedVisualStudio {
    <#
        Mirrors windows-installer.yml lines 117-145: the install only counts if
        vswhere reports it satisfies every required component AND the bundled
        CMake and the ATL headers are physically present.
    #>
    $vswhere = Get-VsWherePath
    if (-not $vswhere) { return $null }
    $arguments = @('-latest', '-version', '[17.0,18.0)', '-products', '*', '-requires') +
        $VisualStudioComponents + @('-property', 'installationPath')
    $installationPath = (& $vswhere @arguments) -join ''
    if (-not $installationPath) { return $null }
    $installationPath = $installationPath.Trim()

    $cmake = Join-Path $installationPath 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
    if (-not (Test-Path -LiteralPath $cmake)) {
        Write-Stamp -Level WARN -Message "Visual Studio found but its bundled CMake is missing: $cmake"
        return $null
    }
    $atlRoot = Join-Path $installationPath 'VC\Tools\MSVC'
    if (-not (Test-Path -LiteralPath $atlRoot)) {
        Write-Stamp -Level WARN -Message 'Visual Studio found but VC\Tools\MSVC is missing.'
        return $null
    }
    $atl = Get-ChildItem -Path $atlRoot -Recurse -Filter atlbase.h -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $atl) {
        Write-Stamp -Level WARN -Message 'Visual Studio found but ATL headers are missing.'
        return $null
    }
    return $installationPath
}

function Test-WindowsSdk {
    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\Include",
        "$env:ProgramFiles\Windows Kits\10\Include"
    )
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $versions = Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like '10.*' }
        foreach ($version in $versions) {
            if (Test-Path -LiteralPath (Join-Path $version.FullName 'um\windows.h')) {
                Write-Stamp -Level OK -Message "Windows SDK: $($version.Name)"
                return $true
            }
        }
    }
    return $false
}

function Install-VisualStudioBuildTools {
    Write-Stamp -Level STEP -Message 'Dependency: Visual Studio 2022 Build Tools + Windows SDK'
    $existing = Get-ValidatedVisualStudio
    if ($existing -and (Test-WindowsSdk)) {
        Write-Stamp -Level OK -Message "Already present and complete: $existing"
        $script:Skipped.Add('Visual Studio 2022 Build Tools') ; return $existing
    }

    $vswhere = Get-VsWherePath
    if ($vswhere) {
        # An installation exists but lacks components; modify it in place.
        $installedPath = ((& $vswhere -latest -version '[17.0,18.0)' -products '*' -property installationPath) -join '').Trim()
        $installer = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vs_installer.exe'
        if ($installedPath -and (Test-Path -LiteralPath $installer)) {
            Write-Stamp -Message "Adding missing components to $installedPath"
            $modifyArguments = @('modify', '--installPath', $installedPath) + $VisualStudioInstallArguments
            Invoke-Native -FilePath $installer -Arguments $modifyArguments `
                -LogFile (Join-Path $script:LogDirectory 'vs-modify.log') | Out-Null
            $validated = Get-ValidatedVisualStudio
            if ($validated -and (Test-WindowsSdk)) {
                $script:Installed.Add('Visual Studio 2022 components')
                return $validated
            }
        }
    }

    $bootstrapper = Join-Path $BuildRoot 'vs_BuildTools.exe'
    Get-RemoteFile -Uri 'https://aka.ms/vs/17/release/vs_BuildTools.exe' `
        -Destination $bootstrapper -MinimumBytes 500000
    $result = Invoke-Native -FilePath $bootstrapper -Arguments $VisualStudioInstallArguments `
        -LogFile (Join-Path $script:LogDirectory 'vs-buildtools-install.log')
    if ($result.ExitCode -notin @(0, 3010, 1641)) {
        Stop-WithFailure "The Visual Studio Build Tools installer exited with $($result.ExitCode). See $($result.LogFile)."
    }

    $validated = Get-ValidatedVisualStudio
    if (-not $validated) {
        Stop-WithFailure 'Visual Studio 2022 with MSVC x64, C++/CLI, ATL, CMake, and CRT merge modules was not found after installation.'
    }
    if (-not (Test-WindowsSdk)) {
        Stop-WithFailure 'No Windows 10/11 SDK was found after installation.'
    }
    $script:Installed.Add('Visual Studio 2022 Build Tools')
    return $validated
}

function Install-Python {
    Write-Stamp -Level STEP -Message 'Dependency: Windows Python launcher'
    Update-SessionPath
    if (Test-CommandExists 'py') {
        Write-Stamp -Level OK -Message ('Already present: ' + ((& py --version 2>&1) -join ''))
        $script:Skipped.Add('Python') ; return
    }
    if (-not (Invoke-Winget -Id 'Python.Python.3.12')) {
        if (-not (Invoke-Choco 'python3')) {
            Write-Stamp -Level WARN -Message 'Windows Python could not be installed; the build uses Cygwin python3 anyway.'
            return
        }
    }
    Update-SessionPath
    if (Test-CommandExists 'py') { $script:Installed.Add('Python') }
}

function Install-Cygwin {
    <#
        Mirrors windows-installer.yml "Install Cygwin build prerequisites"
        (lines 262-317): signature-checked official setup, the exact package
        list, the two LibreOffice-supplied MSVC tools under /opt/lo/bin, and the
        cygbash.exe copy used as the shell for build steps.
    #>
    Write-Stamp -Level STEP -Message 'Dependency: Cygwin build prerequisites'

    $setup = Join-Path $BuildRoot 'cygwin-setup.exe'
    Get-RemoteFile -Uri 'https://cygwin.com/setup-x86_64.exe' -Destination $setup -MinimumBytes 500000

    $signature = Get-AuthenticodeSignature -LiteralPath $setup
    Write-Stamp -Message "Cygwin setup signature: $($signature.Status) / $($signature.SignerCertificate.Subject)"
    if ($signature.Status -ne 'Valid') {
        Stop-WithFailure 'The Cygwin installer signature is not valid; refusing to run it.'
    }

    $setupArguments = @(
        '-q', '-n', '-N', '-d',
        '-R', $CygwinRoot,
        '-s', $CygwinMirror,
        '-P', ($CygwinPackages -join ',')
    )
    $result = Invoke-Native -FilePath $setup -Arguments $setupArguments `
        -LogFile (Join-Path $script:LogDirectory 'cygwin-setup.log')
    if ($result.ExitCode -ne 0) {
        Stop-WithFailure "Cygwin setup failed with exit code $($result.ExitCode)."
    }

    $toolDirectory = Join-Path $CygwinRoot 'opt\lo\bin'
    New-Item -ItemType Directory -Force -Path $toolDirectory | Out-Null
    $downloads = [ordered]@{
        'make.exe'          = 'https://dev-www.libreoffice.org/bin/cygwin/make-4.2.1-msvc.exe'
        'pkgconf-2.4.3.exe' = 'https://dev-www.libreoffice.org/extern/pkgconf-2.4.3.exe'
    }
    foreach ($entry in $downloads.GetEnumerator()) {
        $destination = Join-Path $toolDirectory $entry.Key
        if ((Test-Path -LiteralPath $destination) -and
            ((Get-Item -LiteralPath $destination).Length -ge 10000)) {
            Write-Stamp -Level OK -Message "Already present: $($entry.Key)"
            continue
        }
        Get-RemoteFile -Uri $entry.Value -Destination $destination -MinimumBytes 10000
        $hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        Write-Stamp -Message "$($entry.Key) SHA-256 $hash"
    }

    $cygwinBash = Join-Path $CygwinRoot 'bin\bash.exe'
    if (-not (Test-Path -LiteralPath $cygwinBash)) {
        Stop-WithFailure 'Cygwin bash was not installed.'
    }
    Copy-Item -LiteralPath $cygwinBash -Destination (Join-Path $CygwinRoot 'bin\cygbash.exe') -Force
    Update-SessionPath
    $script:Installed.Add('Cygwin + LibreOffice build tools')
}

function Test-CygwinBuildTools {
    <#
        Mirrors windows-installer.yml "Validate Cygwin and LibreOffice build
        tools" (lines 319-335) exactly, including the NASM >= 2.16 check and the
        "Built for Windows" assertion on the MSVC make.
    #>
    Write-Stamp -Level STEP -Message 'Validating Cygwin and LibreOffice build tools'
    $tools = $RequiredCygwinTools -join ' '
    $validation = @"
test "`$(uname -o)" = Cygwin
for tool in $tools; do
  command -v "`$tool"
done
perl -MArchive::Zip -e 1
perl -MFont::TTF::Font -e 1
/opt/lo/bin/make.exe --version | tee /tmp/make-version.txt
grep -q 'Built for Windows' /tmp/make-version.txt
/opt/lo/bin/pkgconf-2.4.3.exe --version
test "`$(command -v nasm)" = /usr/bin/nasm
nasm_version="`$(nasm -v | awk '{ print `$3 }')"
printf 'NASM %s\n' "`$nasm_version"
test "`$(printf '%s\n' 2.16 "`$nasm_version" | sort -V | head -n 1)" = 2.16
"@
    $result = Invoke-CygwinScript -Script $validation `
        -LogFile (Join-Path $script:LogDirectory 'cygwin-validation.log')
    return $result
}

function Install-CygwinIfNeeded {
    if (Test-Path -LiteralPath (Join-Path $CygwinRoot 'bin\bash.exe')) {
        Update-SessionPath
        $probe = Test-CygwinBuildTools
        if ($probe.ExitCode -eq 0) {
            Write-Stamp -Level OK -Message 'Cygwin already satisfies every build prerequisite.'
            $script:Skipped.Add('Cygwin + LibreOffice build tools')
            return
        }
        Write-Stamp -Level WARN -Message 'Cygwin is present but incomplete; re-running setup to add missing packages.'
    }
    Install-Cygwin
    $validation = Test-CygwinBuildTools
    if ($validation.ExitCode -ne 0) {
        Stop-WithFailure "The Cygwin toolchain validation failed. See $($validation.LogFile)."
    }
    Write-Stamp -Level OK -Message 'Cygwin build prerequisites validated.'
}

# --------------------------------------------------------------------------
# Source checkout
# --------------------------------------------------------------------------

function Sync-SourceCheckout {
    param([Parameter(Mandatory)] [string] $SourceDirectory)

    Write-Stamp -Level STEP -Message "Source checkout at ref '$Ref'"
    # The Windows build refuses a CRLF worktree; force LF for this checkout.
    & git config --global core.autocrlf false | Out-Null

    if (Test-Path -LiteralPath (Join-Path $SourceDirectory '.git')) {
        Write-Stamp -Message 'Updating the existing checkout.'
        $fetch = Invoke-Native -FilePath 'git' -Arguments @('fetch', '--tags', '--force', 'origin') `
            -WorkingDirectory $SourceDirectory -LogFile (Join-Path $script:LogDirectory 'git-fetch.log')
        if ($fetch.ExitCode -ne 0) {
            Stop-WithFailure "git fetch failed. See $($fetch.LogFile)."
        }
    }
    else {
        if (Test-Path -LiteralPath $SourceDirectory) {
            $entries = @(Get-ChildItem -LiteralPath $SourceDirectory -Force)
            if ($entries.Count -gt 0) {
                Stop-WithFailure "$SourceDirectory exists, is not a git checkout, and is not empty. Refusing to overwrite it."
            }
        }
        $clone = Invoke-Native -FilePath 'git' -Arguments @('clone', $RepositoryUrl, $SourceDirectory) `
            -LogFile (Join-Path $script:LogDirectory 'git-clone.log')
        if ($clone.ExitCode -ne 0) {
            Stop-WithFailure "git clone failed. See $($clone.LogFile)."
        }
    }

    $checkout = Invoke-Native -FilePath 'git' -Arguments @('checkout', '--force', $Ref) `
        -WorkingDirectory $SourceDirectory -LogFile (Join-Path $script:LogDirectory 'git-checkout.log')
    if ($checkout.ExitCode -ne 0) {
        # A branch name that only exists on the remote needs the remote spelling.
        $checkout = Invoke-Native -FilePath 'git' -Arguments @('checkout', '--force', "origin/$Ref") `
            -WorkingDirectory $SourceDirectory -LogFile (Join-Path $script:LogDirectory 'git-checkout-remote.log')
    }
    if ($checkout.ExitCode -ne 0) {
        Stop-WithFailure "Could not check out ref '$Ref'. See $($checkout.LogFile)."
    }
    # Fast-forward when the ref is a branch; a detached tag/sha simply has no upstream.
    Invoke-Native -FilePath 'git' -Arguments @('pull', '--ff-only') -WorkingDirectory $SourceDirectory `
        -LogFile (Join-Path $script:LogDirectory 'git-pull.log') | Out-Null

    $head = ((& git -C $SourceDirectory rev-parse HEAD) -join '').Trim()
    Write-Stamp -Level OK -Message "HEAD: $head"

    $eol = (& git -C $SourceDirectory ls-files --eol autogen.sh configure.ac distro-configs/LibreOfficeWin64.conf) -join "`n"
    Write-Stamp -Message $eol
    if ($eol -match 'w/crlf') {
        Stop-WithFailure 'The Windows build requires an LF checkout; CRLF files were detected.'
    }
    return $head
}

# --------------------------------------------------------------------------
# opencode auto-fix
# --------------------------------------------------------------------------

function Resolve-OpenCodeCommand {
    <#
        `opencode run [message..]` is the documented non-interactive entry point
        (`opencode --help` lists it as "run opencode with a message"; the plain
        `opencode` default starts the TUI). `--auto` auto-approves permissions so
        no approval prompt can block an unattended run, and `--dir` selects the
        checkout to operate on. Returns a scriptblock-friendly descriptor or
        $null when opencode is unavailable.
    #>
    $command = Get-Command 'opencode' -ErrorAction SilentlyContinue
    if ($command -and $command.CommandType -eq 'Application') {
        return [pscustomobject]@{ FilePath = $command.Source; Prefix = @() }
    }
    if (Test-Path -LiteralPath $OpenCodeScript) {
        $pwshPath = Get-PwshPath
        $host_ = if ($pwshPath) { $pwshPath } else { 'powershell.exe' }
        return [pscustomobject]@{
            FilePath = $host_
            Prefix   = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $OpenCodeScript)
        }
    }
    $cmdShim = Join-Path $env:APPDATA 'npm\opencode.cmd'
    if (Test-Path -LiteralPath $cmdShim) {
        return [pscustomobject]@{ FilePath = $cmdShim; Prefix = @() }
    }
    return $null
}

function Invoke-OpenCodeRepair {
    param(
        [Parameter(Mandatory)] [string] $SourceDirectory,
        [Parameter(Mandatory)] [string] $Stage,
        [Parameter(Mandatory)] [string] $FailingCommand,
        [Parameter(Mandatory)] [string] $ErrorTail,
        [Parameter(Mandatory)] [int] $Attempt
    )
    $opencode = Resolve-OpenCodeCommand
    if (-not $opencode) {
        Write-Stamp -Level WARN -Message 'opencode is not installed; cannot attempt an automatic repair.'
        return $false
    }

    $prompt = @"
You are repairing a LibreOffice Windows x64 build that failed inside the
checkout at $SourceDirectory. Fix the source in that checkout so the build
proceeds. Do not change the build configuration flags, do not disable tests,
and do not fake success.

Failing stage: $Stage
Failing command:
$FailingCommand

Tail of the build log:
$ErrorTail

Make the smallest correct source change that resolves this error, then stop.
"@

    $promptFile = Join-Path $script:LogDirectory "opencode-prompt-$Stage-$Attempt.txt"
    [System.IO.File]::WriteAllText($promptFile, $prompt, [System.Text.UTF8Encoding]::new($false))
    Write-Stamp -Level STEP -Message "opencode repair attempt $Attempt for stage '$Stage' (prompt: $promptFile)"

    $arguments = $opencode.Prefix + @(
        'run', '--auto', '--dir', $SourceDirectory,
        '--title', "auto-fix $Stage attempt $Attempt",
        $prompt
    )
    $result = Invoke-Native -FilePath $opencode.FilePath -Arguments $arguments `
        -LogFile (Join-Path $script:LogDirectory "opencode-$Stage-$Attempt.log")
    if ($result.ExitCode -ne 0) {
        Write-Stamp -Level WARN -Message "opencode exited with $($result.ExitCode); retrying the build anyway."
    }
    return $true
}

function Get-LogTail {
    param(
        [Parameter(Mandatory)] [string] $Text,
        [int] $Lines = 200
    )
    $split = $Text -split "`r?`n"
    if ($split.Count -le $Lines) { return $Text }
    return ($split[($split.Count - $Lines)..($split.Count - 1)] -join [Environment]::NewLine)
}

function Invoke-StageWithAutoFix {
    <#
        Runs a Cygwin build stage. On failure, feeds the tail of its log to
        opencode and retries, up to -MaxFixAttempts times. Every attempt is
        logged separately so the whole history survives.
    #>
    param(
        [Parameter(Mandatory)] [string] $Stage,
        [Parameter(Mandatory)] [string] $Script,
        [Parameter(Mandatory)] [string] $SourceDirectory,
        [Parameter(Mandatory)] [string] $Description
    )
    $attempt = 0
    while ($true) {
        $attempt++
        Write-Stamp -Level STEP -Message "$Description (attempt $attempt)"
        $logFile = Join-Path $script:LogDirectory "$Stage-attempt-$attempt.log"
        $result = Invoke-CygwinScript -Script $Script -LogFile $logFile
        if ($result.ExitCode -eq 0) {
            Write-Stamp -Level OK -Message "$Description succeeded on attempt $attempt."
            return
        }

        Write-Stamp -Level FAIL -Message "$Description failed with exit code $($result.ExitCode). Log: $logFile"
        if (-not $AutoFix) {
            Stop-WithFailure "$Description failed and -AutoFix is disabled. Log: $logFile"
        }
        if ($attempt -gt $MaxFixAttempts) {
            Stop-WithFailure "$Description still fails after $MaxFixAttempts automatic repair attempts. Last log: $logFile"
        }

        $tail = Get-LogTail -Text $result.Output -Lines 200
        $repaired = Invoke-OpenCodeRepair -SourceDirectory $SourceDirectory -Stage $Stage `
            -FailingCommand $result.Command -ErrorTail $tail -Attempt $attempt
        if (-not $repaired) {
            Stop-WithFailure "$Description failed and no automatic repair was possible. Log: $logFile"
        }
    }
}

# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------

function Invoke-Configure {
    param(
        [Parameter(Mandatory)] [string] $SourceDirectory,
        [Parameter(Mandatory)] [string] $BuildDirectory,
        [Parameter(Mandatory)] [string] $TarballDirectory
    )
    $unixSource = ConvertTo-CygwinPath $SourceDirectory
    $unixBuild = ConvertTo-CygwinPath $BuildDirectory
    $unixTarballs = ConvertTo-CygwinPath $TarballDirectory
    $flags = $AutogenFlags -replace '@TARBALLS@', ($TarballDirectory -replace '\\', '/')
    $flagText = ($flags | ForEach-Object { "  $_ \" }) -join "`n"
    $flagText = $flagText -replace ' \\$', ''

    $script = @"
src_dir="$unixSource"
build_dir="$unixBuild"
tarball_dir="$unixTarballs"
test -n "`$HOME"
mkdir -p "`$HOME"
/usr/bin/git config --global --add safe.directory "`$src_dir"
/usr/bin/git -C "`$src_dir" rev-parse --verify HEAD
mkdir -p "`$build_dir" "`$tarball_dir"
cd "`$build_dir"
"`$src_dir/autogen.sh" \
$flagText

grep -Eq '^export BUILD_TYPE=.*[[:space:]]DBCONNECTIVITY([[:space:]]|`$)' config_host.mk
grep -qx 'export ENABLE_CLI=TRUE' config_host.mk
"@
    Invoke-StageWithAutoFix -Stage 'configure' -Script $script -SourceDirectory $SourceDirectory `
        -Description 'Configure the Windows x64 LibreOfficeDev build'
}

function Invoke-Build {
    param(
        [Parameter(Mandatory)] [string] $SourceDirectory,
        [Parameter(Mandatory)] [string] $BuildDirectory,
        [Parameter(Mandatory)] [int] $Jobs
    )
    $unixBuild = ConvertTo-CygwinPath $BuildDirectory
    $script = @"
export CL=/FS
cd "$unixBuild"
/opt/lo/bin/make.exe -j$Jobs
"@
    Invoke-StageWithAutoFix -Stage 'make' -Script $script -SourceDirectory $SourceDirectory `
        -Description 'Build LibreOfficeDev from source'
}

function Find-SofficeExecutable {
    param([Parameter(Mandatory)] [string] $BuildDirectory)
    $candidates = @(
        (Join-Path $BuildDirectory 'instdir\program\soffice.exe'),
        (Join-Path $BuildDirectory 'instdir\program\soffice.bin')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    $found = Get-ChildItem -Path $BuildDirectory -Filter 'soffice.exe' -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    return $null
}

function Install-StartMenuShortcut {
    param([Parameter(Mandatory)] [string] $SofficePath)
    try {
        $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
        New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
        $shortcut = Join-Path $startMenu 'LibreOffice Material.lnk'
        $shell = New-Object -ComObject WScript.Shell
        $link = $shell.CreateShortcut($shortcut)
        $link.TargetPath = $SofficePath
        $link.WorkingDirectory = Split-Path -Parent $SofficePath
        $link.Description = 'LibreOffice Material (built from source)'
        $link.Save()
        Write-Stamp -Level OK -Message "Start menu shortcut: $shortcut"
    }
    catch {
        Write-Stamp -Level WARN -Message "Could not create a Start menu shortcut: $($_.Exception.Message)"
    }
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

# Bootstrap 1: prefer PowerShell 7 when this started under Windows PowerShell 5.1.
if ($PSVersionTable.PSVersion.Major -lt 7 -and -not $env:LOM_NO_PWSH_BOOTSTRAP) {
    $pwsh = Get-PwshPath
    if (-not $pwsh) {
        Write-Host 'PowerShell 7 is missing; installing it with winget.'
        if (Test-CommandExists 'winget') {
            & winget install --id Microsoft.PowerShell --exact --silent `
                --accept-package-agreements --accept-source-agreements --disable-interactivity | Out-Host
        }
        $pwsh = Get-PwshPath
    }
    if ($pwsh) {
        Invoke-SelfRelaunch -Executable $pwsh -Elevate:(-not (Test-IsAdministrator)) `
            -Why 'switching to PowerShell 7'
    }
    else {
        Write-Warning 'Continuing under Windows PowerShell 5.1; PowerShell 7 could not be installed.'
        $env:LOM_NO_PWSH_BOOTSTRAP = '1'
    }
}

# Bootstrap 2: elevate. Installing compilers and writing to C:\ requires it.
if (-not (Test-IsAdministrator)) {
    $self = if ($PSVersionTable.PSVersion.Major -ge 7) { (Get-PwshPath) } else { $null }
    if (-not $self) { $self = (Get-Process -Id $PID).Path }
    Invoke-SelfRelaunch -Executable $self -Elevate $true `
        -Why 'Administrator rights are required to install build dependencies'
}

New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null
New-Item -ItemType Directory -Force -Path $script:LogDirectory | Out-Null
$script:TranscriptPath = Join-Path $script:LogDirectory (
    'install-{0}.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
try { Start-Transcript -Path $script:TranscriptPath -Force | Out-Null }
catch { Write-Warning "Could not start a transcript: $($_.Exception.Message)" }

try {
    Write-Stamp -Level STEP -Message 'LibreOffice Material - build and run from source'
    Write-Stamp -Message "Ref            : $Ref"
    Write-Stamp -Message "Build root     : $BuildRoot"
    Write-Stamp -Message "Unattended     : $Unattended"
    Write-Stamp -Message "AutoFix        : $AutoFix (max $MaxFixAttempts attempts per stage)"
    Write-Stamp -Message "Skip launch    : $([bool]$SkipLaunch)"
    Write-Stamp -Message "Transcript     : $script:TranscriptPath"
    Write-Stamp -Message "PowerShell     : $($PSVersionTable.PSVersion)"
    Write-Stamp -Level WARN -Message 'This script has never been run end to end. Read the transcript before trusting any result.'

    if ($JobCount -le 0) {
        $processors = [int]$env:NUMBER_OF_PROCESSORS
        if ($processors -le 0) { $processors = 4 }
        $JobCount = [Math]::Max(2, [Math]::Min(8, [int][Math]::Floor($processors / 2)))
    }
    Write-Stamp -Message "Parallel jobs  : $JobCount"

    # Disk-space precheck. A full LibreOffice build plus tarballs and the
    # installation set needs tens of gigabytes.
    $driveLetter = (Split-Path -Qualifier (Resolve-Path -LiteralPath $BuildRoot).Path).TrimEnd(':')
    $drive = Get-PSDrive -Name $driveLetter
    Write-Stamp -Message ("Free on {0}: {1:N1} GiB" -f $driveLetter, ($drive.Free / 1GB))
    if ($drive.Free -lt $MinimumFreeBytes) {
        Stop-WithFailure ("Only {0:N1} GiB free on {1}:. At least {2:N0} GiB are required. Free space or pass -BuildRoot on a larger drive." -f `
            ($drive.Free / 1GB), $driveLetter, ($MinimumFreeBytes / 1GB))
    }

    Install-Git
    Install-SevenZip
    Install-Python
    $visualStudio = Install-VisualStudioBuildTools
    Write-Stamp -Level OK -Message "Visual Studio: $visualStudio"
    Install-CygwinIfNeeded

    $sourceDirectory = Join-Path $BuildRoot 'src'
    $buildDirectory = Join-Path $BuildRoot 'build'
    $tarballDirectory = Join-Path $BuildRoot 'tarballs'
    New-Item -ItemType Directory -Force -Path $buildDirectory, $tarballDirectory | Out-Null

    $head = Sync-SourceCheckout -SourceDirectory $sourceDirectory

    Invoke-Configure -SourceDirectory $sourceDirectory -BuildDirectory $buildDirectory `
        -TarballDirectory $tarballDirectory
    Invoke-Build -SourceDirectory $sourceDirectory -BuildDirectory $buildDirectory -Jobs $JobCount

    $soffice = Find-SofficeExecutable -BuildDirectory $buildDirectory
    if (-not $soffice) {
        Stop-WithFailure "The build reported success but no soffice.exe was produced under $buildDirectory."
    }
    Write-Stamp -Level OK -Message "Built office: $soffice"
    Install-StartMenuShortcut -SofficePath $soffice

    $elapsed = (Get-Date) - $script:StartTime
    Write-Stamp -Level STEP -Message 'Summary'
    Write-Stamp -Level OK -Message ("Elapsed: {0:hh\:mm\:ss}" -f $elapsed)
    Write-Stamp -Message "Source ref     : $Ref ($head)"
    Write-Stamp -Message "Installed      : $(if ($script:Installed.Count) { $script:Installed -join ', ' } else { '(nothing new)' })"
    Write-Stamp -Message "Already present: $(if ($script:Skipped.Count) { $script:Skipped -join ', ' } else { '(none)' })"
    Write-Stamp -Message "Office         : $soffice"
    Write-Stamp -Message "Logs           : $script:LogDirectory"
    Write-Stamp -Message "Transcript     : $script:TranscriptPath"

    if ($SkipLaunch) {
        Write-Stamp -Level OK -Message 'Done. -SkipLaunch was set, so nothing was started.'
    }
    else {
        Write-Stamp -Level STEP -Message 'Launching LibreOffice Material'
        Start-Process -FilePath $soffice -WorkingDirectory (Split-Path -Parent $soffice) | Out-Null
        Write-Stamp -Level OK -Message 'Done.'
    }
}
catch {
    Write-Stamp -Level FAIL -Message $_.Exception.Message
    Write-Stamp -Level FAIL -Message ($_.ScriptStackTrace)
    Stop-WithFailure 'The installer stopped on an unexpected error.'
}
finally {
    try { Stop-Transcript | Out-Null } catch { }
}

exit 0
