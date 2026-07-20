#requires -Version 5.1
<#
.SYNOPSIS
    Prepares, inspects, launches, or verifies the disposable Windows Sandbox MSI lifecycle gate.

.DESCRIPTION
    Prepare is the safe default. It downloads two exact-tag MSI assets, verifies
    pinned sizes and SHA-256 values, creates fresh input/output directories, and
    writes a locked-down .wsb configuration. It does not start Windows Sandbox.

    Inspect revalidates an explicitly prepared run without launching anything.

    Launch requires an explicitly prepared run directory. All MSI install,
    same-version update, repair, and uninstall operations occur in Windows
    Sandbox. The host only polls a fresh mapped output directory and validates
    the guest's completion manifest.

    Verify revalidates an already completed output directory without launching
    Windows Sandbox.
#>
[CmdletBinding()]
param(
    [ValidateSet('Prepare', 'Inspect', 'Launch', 'Verify')]
    [string]$Mode = 'Prepare',

    [string]$RunDirectory,

    [string]$RunRoot = (Join-Path -Path ([Environment]::GetFolderPath('LocalApplicationData')) -ChildPath 'LibreOfficeMaterial\InstallerLifecycle'),

    [ValidateRange(5, 240)]
    [int]$TimeoutMinutes = 90,

    [ValidateRange(4096, 32768)]
    [int]$MemoryInMB = 8192,

    [ValidateRange(30, 600)]
    [int]$DisposalTimeoutSeconds = 180
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:OldInstaller = [ordered]@{
    file_name = 'old.msi'
    release_tag = 'windows-msi-local-20260720-577059e274'
    source_commit = '577059e2741185b512c184c64685c16d335d10ea'
    url = 'https://github.com/Ding-Ding-Projects/libreoffice-material/releases/download/windows-msi-local-20260720-577059e274/LibreOfficeMaterial-Windows-x64.msi'
    bytes = 199692288
    sha256 = '437b059c7dd5ed7a60c2ae4f47f2a1905cf97ef4e136e98183e08658d7654a43'
    updater_dll_sha256 = '363db7d0ebfa878f084751aea4d6069e03ede53d71252c3007f11fd984834ade'
}
$script:CorrectedInstaller = [ordered]@{
    file_name = 'corrected.msi'
    release_tag = 'windows-msi-local-20260720-fbba560e2'
    source_commit = 'fbba560e27db26de605c40aa237c554c1f0744b1'
    url = 'https://github.com/Ding-Ding-Projects/libreoffice-material/releases/download/windows-msi-local-20260720-fbba560e2/LibreOfficeMaterial-Windows-x64.msi'
    bytes = 199688192
    sha256 = '180e511c065f3e21cd9e4fd0abe31f8886b0cc5ce5ce27a48f2890f83d1afeea'
    updater_dll_sha256 = '32f80adfcd5097ef54f13951b748a5703439aef0dbb751d6a4c5d3e6102446a3'
    product_code = '{2BD7C198-30D4-4BC6-AE7C-52B7F5DBAF71}'
}
$script:ExpectedUpgradeCode = '{910006D2-BDF1-440C-89D3-8F1DD93790FE}'
$script:StableLibreOfficeUpgradeCode = '{4B17E523-5D91-4E69-BD96-7FD81CFA81BB}'
$script:ExpectedProductVersion = '27.2.0.0.alpha0'
$script:ExpectedInstallRoot = 'C:\Program Files\LibreOfficeDev 27'
$script:RequiredSteps = @(
    'old-install',
    'corrected-same-version-update',
    'corrected-repair',
    'corrected-uninstall'
)

function Get-FullPath {
    param([Parameter(Mandatory)][string]$LiteralPath)
    [IO.Path]::GetFullPath($LiteralPath)
}

function Get-Sha256 {
    param([Parameter(Mandatory)][string]$LiteralPath)
    (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-ObjectPropertyValue {
    param(
        [Parameter(Mandatory)]$InputObject,
        [Parameter(Mandatory)][string]$Name
    )
    $property = $InputObject.PSObject.Properties[$Name]
    if ($property) {
        $property.Value
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory)]$Value,
        [Parameter(Mandatory)][string]$LiteralPath
    )
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $LiteralPath -Encoding UTF8
}

function Assert-OrdinaryDirectory {
    param([Parameter(Mandatory)][string]$LiteralPath)
    $item = Get-Item -LiteralPath $LiteralPath -Force
    if (-not $item.PSIsContainer) {
        throw "Expected a directory: $LiteralPath"
    }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing a reparse-point directory: $LiteralPath"
    }
}

function Assert-FileMatches {
    param(
        [Parameter(Mandatory)][string]$LiteralPath,
        [Parameter(Mandatory)][long]$ExpectedBytes,
        [Parameter(Mandatory)][string]$ExpectedSha256
    )
    $item = Get-Item -LiteralPath $LiteralPath -Force
    if ($item.PSIsContainer) {
        throw "Expected an ordinary file: $LiteralPath"
    }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing a reparse-point file: $LiteralPath"
    }
    if ($item.Length -ne $ExpectedBytes) {
        throw "Size mismatch for $LiteralPath. Expected $ExpectedBytes, got $($item.Length)."
    }
    $actualHash = Get-Sha256 -LiteralPath $LiteralPath
    if ($actualHash -ne $ExpectedSha256) {
        throw "SHA-256 mismatch for $LiteralPath. Expected $ExpectedSha256, got $actualHash."
    }
}

function Assert-BoundedOrdinaryJsonFile {
    param(
        [Parameter(Mandatory)][string]$LiteralPath,
        [ValidateRange(2, 1048576)][long]$MaximumBytes = 1048576
    )
    $item = Get-Item -LiteralPath $LiteralPath -Force
    if ($item.PSIsContainer -or
        ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        $item.Length -lt 2 -or $item.Length -gt $MaximumBytes) {
        throw "Refusing invalid or oversized JSON artifact: $LiteralPath"
    }
}

function Invoke-PinnedDownload {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][string]$Destination,
        [Parameter(Mandatory)][long]$ExpectedBytes,
        [Parameter(Mandatory)][string]$ExpectedSha256
    )
    if (Test-Path -LiteralPath $Destination) {
        throw "Pinned download destination already exists: $Destination"
    }

    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $partial = "$Destination.partial"
    for ($attempt = 1; $attempt -le 4; $attempt++) {
        try {
            if (Test-Path -LiteralPath $partial) {
                Remove-Item -LiteralPath $partial -Force
            }
            Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $partial
            Assert-FileMatches -LiteralPath $partial -ExpectedBytes $ExpectedBytes `
                -ExpectedSha256 $ExpectedSha256
            Move-Item -LiteralPath $partial -Destination $Destination
            return
        }
        catch {
            if (Test-Path -LiteralPath $partial) {
                Remove-Item -LiteralPath $partial -Force
            }
            if ($attempt -eq 4) {
                throw
            }
            Start-Sleep -Seconds (2 * $attempt)
        }
    }
}

function Get-RebootState {
    $sessionManager = Get-ItemProperty `
        -LiteralPath 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' `
        -ErrorAction SilentlyContinue
    $updates = Get-ItemProperty -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Updates' `
        -ErrorAction SilentlyContinue
    $updateExeVolatileProperty = if ($updates) {
        $updates.PSObject.Properties['UpdateExeVolatile']
    } else { $null }
    $pendingRenameProperty = if ($sessionManager) {
        $sessionManager.PSObject.Properties['PendingFileRenameOperations']
    } else { $null }
    $pendingRename2Property = if ($sessionManager) {
        $sessionManager.PSObject.Properties['PendingFileRenameOperations2']
    } else { $null }
    [ordered]@{
        boot_time_utc = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
        cbs_reboot_pending = Test-Path -LiteralPath `
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending'
        cbs_reboot_in_progress = Test-Path -LiteralPath `
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootInProgress'
        cbs_packages_pending = Test-Path -LiteralPath `
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\PackagesPending'
        windows_update_reboot_required = Test-Path -LiteralPath `
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
        pending_file_rename_operations = if ($pendingRenameProperty) {
            @($pendingRenameProperty.Value)
        } else { @() }
        pending_file_rename_operations_2 = if ($pendingRename2Property) {
            @($pendingRename2Property.Value)
        } else { @() }
        update_exe_volatile = if ($updateExeVolatileProperty) {
            $updateExeVolatileProperty.Value
        } else { $null }
        windows_installer_in_progress = Test-Path -LiteralPath `
            'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\InProgress'
    }
}

function Get-LibreOfficeRegistrations {
    $roots = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    @(
        Get-ItemProperty -Path $roots -ErrorAction SilentlyContinue |
            ForEach-Object {
                $displayName = [string](Get-ObjectPropertyValue -InputObject $_ -Name 'DisplayName')
                if ($displayName -match 'LibreOffice') {
                    [ordered]@{
                        key = [string](Get-ObjectPropertyValue -InputObject $_ -Name 'PSChildName')
                        display_name = $displayName
                        display_version = [string](Get-ObjectPropertyValue -InputObject $_ -Name 'DisplayVersion')
                        install_location = [string](Get-ObjectPropertyValue -InputObject $_ -Name 'InstallLocation')
                    }
                }
            } |
            Sort-Object key, display_name
    )
}

function Get-HostSafetySnapshot {
    [ordered]@{
        captured_at_utc = [DateTime]::UtcNow.ToString('o')
        reboot = Get-RebootState
        libreoffice_registrations = @(Get-LibreOfficeRegistrations)
    }
}

function Get-HostSafetyFingerprint {
    param([Parameter(Mandatory)]$Snapshot)
    ([ordered]@{
        reboot = $Snapshot.reboot
        libreoffice_registrations = @($Snapshot.libreoffice_registrations)
    } | ConvertTo-Json -Depth 20 -Compress)
}

function Get-RebootFingerprint {
    param([Parameter(Mandatory)]$Snapshot)
    ([ordered]@{
        boot_time_utc = $Snapshot.boot_time_utc
        cbs_reboot_pending = $Snapshot.cbs_reboot_pending
        cbs_reboot_in_progress = $Snapshot.cbs_reboot_in_progress
        cbs_packages_pending = $Snapshot.cbs_packages_pending
        windows_update_reboot_required = $Snapshot.windows_update_reboot_required
        pending_file_rename_operations = @($Snapshot.pending_file_rename_operations)
        pending_file_rename_operations_2 = @($Snapshot.pending_file_rename_operations_2)
        update_exe_volatile = $Snapshot.update_exe_volatile
        windows_installer_in_progress = $Snapshot.windows_installer_in_progress
    } | ConvertTo-Json -Depth 10 -Compress)
}

function Get-WindowsSandboxProcesses {
    $names = @(
        'WindowsSandbox.exe',
        'WindowsSandboxClient.exe',
        'WindowsSandboxRemoteSession.exe',
        'WindowsSandboxServer.exe'
    )
    @(
        Get-CimInstance Win32_Process |
            Where-Object { $_.Name -in $names } |
            ForEach-Object {
                [ordered]@{
                    id = [int]$_.ProcessId
                    name = [string]$_.Name
                    executable_path = [string]$_.ExecutablePath
                    command_line = [string]$_.CommandLine
                    creation_date = if ($_.CreationDate) {
                        $_.CreationDate.ToUniversalTime().ToString('o')
                    } else { $null }
                }
            }
    )
}

function Wait-ForWindowsSandboxProcessExit {
    param(
        [Parameter(Mandatory)][string[]]$Names,
        [Parameter(Mandatory)][DateTime]$Deadline,
        [Parameter(Mandatory)][string]$Description
    )
    do {
        $processes = @(Get-WindowsSandboxProcesses | Where-Object { $_.name -in $Names })
        if ($processes.Count -eq 0) {
            return
        }
        Start-Sleep -Seconds 1
    } while ([DateTime]::UtcNow -lt $Deadline)

    $summary = @($processes | ForEach-Object { "$($_.name):$($_.id)" }) -join ', '
    throw "Timed out waiting for $Description; remaining processes: $summary"
}

function Assert-RunBoundSandboxRemoteSession {
    param(
        [Parameter(Mandatory)]$Process,
        [Parameter(Mandatory)]$Run
    )
    $expectedWsbArgument = '"' + [IO.Path]::GetFullPath($Run.WsbPath) + '"'
    if ([string]::IsNullOrWhiteSpace($Process.command_line) -or
        $Process.command_line.IndexOf($expectedWsbArgument,
            [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Refusing to close a Windows Sandbox client that is not bound to this run: $($Process.id)"
    }
    if ([string]::IsNullOrWhiteSpace($Process.executable_path) -or
        $Process.executable_path -notmatch
            '(?i)\\WindowsApps\\MicrosoftWindows\.WindowsSandbox_[^\\]+__cw5n1h2txyewy\\WindowsSandboxRemoteSession\.exe$') {
        throw "Refusing an unexpected Windows Sandbox remote-session executable: $($Process.executable_path)"
    }
}

function Wait-ForWindowsSandboxDisposal {
    param([Parameter(Mandatory)]$Run)

    $deadline = [DateTime]::UtcNow.AddSeconds($DisposalTimeoutSeconds)

    # The guest publishes its sentinel before requesting shutdown. The backend must
    # disappear on its own; the host never terminates or closes the guest server.
    Wait-ForWindowsSandboxProcessExit -Names @('WindowsSandboxServer.exe') `
        -Deadline $deadline -Description 'the Windows Sandbox backend to exit normally'

    $remoteSessions = @(
        Get-WindowsSandboxProcesses |
            Where-Object { $_.name -eq 'WindowsSandboxRemoteSession.exe' }
    )
    if ($remoteSessions.Count -gt 1) {
        $summary = @($remoteSessions | ForEach-Object { "$($_.name):$($_.id)" }) -join ', '
        throw "Refusing to close multiple Windows Sandbox remote sessions: $summary"
    }
    if ($remoteSessions.Count -eq 1) {
        $remoteSession = $remoteSessions[0]
        Assert-RunBoundSandboxRemoteSession -Process $remoteSession -Run $Run
        $client = Get-Process -Id $remoteSession.id -ErrorAction SilentlyContinue
        if ($client -and -not $client.CloseMainWindow()) {
            throw "The run-bound Windows Sandbox client did not accept a graceful close request: $($remoteSession.id)"
        }
    }

    Wait-ForWindowsSandboxProcessExit `
        -Names @(
            'WindowsSandbox.exe',
            'WindowsSandboxClient.exe',
            'WindowsSandboxRemoteSession.exe',
            'WindowsSandboxServer.exe'
        ) `
        -Deadline $deadline -Description 'all Windows Sandbox processes to dispose normally'
}

function Assert-SandboxReady {
    $sandboxExecutable = Join-Path $env:SystemRoot 'System32\WindowsSandbox.exe'
    if (-not (Test-Path -LiteralPath $sandboxExecutable -PathType Leaf)) {
        throw 'Windows Sandbox is not installed.'
    }

    foreach ($featureName in @(
        'Containers-DisposableClientVM',
        'Microsoft-Hyper-V-All',
        'Microsoft-Hyper-V-Hypervisor',
        'VirtualMachinePlatform'
    )) {
        $feature = Get-CimInstance Win32_OptionalFeature -Filter "Name='$featureName'"
        if (-not $feature -or [int]$feature.InstallState -ne 1) {
            throw "Required Windows feature is not enabled: $featureName"
        }
    }

    $computer = Get-CimInstance Win32_ComputerSystem
    if (-not $computer.HypervisorPresent) {
        throw 'Windows reports that no hypervisor is present.'
    }
    $sandboxExecutable
}

function Get-PreparedRun {
    param([Parameter(Mandatory)][string]$LiteralPath)
    $resolved = (Resolve-Path -LiteralPath $LiteralPath).Path
    Assert-OrdinaryDirectory -LiteralPath $resolved
    $inputDirectory = Join-Path $resolved 'input'
    $outputDirectory = Join-Path $resolved 'output'
    $manifestPath = Join-Path $resolved 'run-manifest.json'
    foreach ($directory in @($inputDirectory, $outputDirectory)) {
        Assert-OrdinaryDirectory -LiteralPath $directory
    }
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Prepared-run manifest is missing: $manifestPath"
    }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.schema_version -ne 1 -or [string]::IsNullOrWhiteSpace($manifest.run_id)) {
        throw 'Prepared-run manifest is invalid.'
    }
    if (-not [string]::Equals(
            (Get-FullPath -LiteralPath ([string]$manifest.input_directory)),
            (Get-FullPath -LiteralPath $inputDirectory),
            [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals(
            (Get-FullPath -LiteralPath ([string]$manifest.output_directory)),
            (Get-FullPath -LiteralPath $outputDirectory),
            [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Prepared-run manifest directory bindings do not match the selected run.'
    }
    [pscustomobject]@{
        Root = $resolved
        Input = $inputDirectory
        Output = $outputDirectory
        ManifestPath = $manifestPath
        Manifest = $manifest
        WsbPath = Join-Path $resolved 'LibreOfficeMaterial-InstallerLifecycle.wsb'
    }
}

function Assert-WsbPolicy {
    param([Parameter(Mandatory)]$Run)

    $document = New-Object System.Xml.XmlDocument
    $document.PreserveWhitespace = $true
    $document.Load($Run.WsbPath)

    $expectedRootElements = @(
        'VGpu',
        'Networking',
        'AudioInput',
        'VideoInput',
        'PrinterRedirection',
        'ClipboardRedirection',
        'MemoryInMB',
        'MappedFolders',
        'LogonCommand'
    )
    $root = $document.DocumentElement
    if (-not $root -or $root.LocalName -ne 'Configuration') {
        throw 'Prepared .wsb has no Configuration root element.'
    }
    $actualRootElements = @(
        $root.ChildNodes |
            Where-Object { $_.NodeType -eq [Xml.XmlNodeType]::Element } |
            ForEach-Object { $_.LocalName }
    )
    if ($actualRootElements.Count -ne $expectedRootElements.Count) {
        throw 'Prepared .wsb root settings differ from the generated isolation policy.'
    }
    foreach ($name in $expectedRootElements) {
        if (@($actualRootElements | Where-Object { $_ -eq $name }).Count -ne 1) {
            throw "Prepared .wsb setting is missing or duplicated: $name"
        }
    }

    foreach ($setting in @(
        [pscustomobject]@{ XPath = '/Configuration/VGpu'; Value = 'Disable' },
        [pscustomobject]@{ XPath = '/Configuration/Networking'; Value = 'Disable' },
        [pscustomobject]@{ XPath = '/Configuration/AudioInput'; Value = 'Disable' },
        [pscustomobject]@{ XPath = '/Configuration/VideoInput'; Value = 'Disable' },
        [pscustomobject]@{ XPath = '/Configuration/PrinterRedirection'; Value = 'Disable' },
        [pscustomobject]@{ XPath = '/Configuration/ClipboardRedirection'; Value = 'Disable' }
    )) {
        $nodes = @($document.SelectNodes($setting.XPath))
        if ($nodes.Count -ne 1 -or $nodes[0].InnerText -ne $setting.Value) {
            throw "Prepared .wsb isolation setting changed: $($setting.XPath)"
        }
    }

    $memoryNodes = @($document.SelectNodes('/Configuration/MemoryInMB'))
    $configuredMemory = 0
    if ($memoryNodes.Count -ne 1 -or
        -not [int]::TryParse($memoryNodes[0].InnerText, [ref]$configuredMemory) -or
        $configuredMemory -lt 4096 -or $configuredMemory -gt 32768) {
        throw 'Prepared .wsb has an invalid MemoryInMB value.'
    }

    $mappedFolders = @($document.SelectNodes('/Configuration/MappedFolders/MappedFolder'))
    if ($mappedFolders.Count -ne 2) {
        throw 'Prepared .wsb must contain exactly two mapped folders.'
    }
    $expectedMappings = @(
        [pscustomobject]@{
            Host = (Get-FullPath -LiteralPath $Run.Input)
            Sandbox = 'C:\Lifecycle\Input'
            ReadOnly = 'true'
        },
        [pscustomobject]@{
            Host = (Get-FullPath -LiteralPath $Run.Output)
            Sandbox = 'C:\Lifecycle\Output'
            ReadOnly = 'false'
        }
    )
    foreach ($expectedMapping in $expectedMappings) {
        $matches = @($mappedFolders | Where-Object {
            $hostNode = $_.SelectSingleNode('./HostFolder')
            $sandboxNode = $_.SelectSingleNode('./SandboxFolder')
            $readOnlyNode = $_.SelectSingleNode('./ReadOnly')
            $hostNode -and $sandboxNode -and $readOnlyNode -and
            [string]::Equals(
                (Get-FullPath -LiteralPath $hostNode.InnerText),
                $expectedMapping.Host,
                [StringComparison]::OrdinalIgnoreCase) -and
            $sandboxNode.InnerText -eq $expectedMapping.Sandbox -and
            $readOnlyNode.InnerText -eq $expectedMapping.ReadOnly
        })
        if ($matches.Count -ne 1) {
            throw "Prepared .wsb mapping changed: $($expectedMapping.Sandbox)"
        }
    }

    $commandNodes = @($document.SelectNodes('/Configuration/LogonCommand/Command'))
    $expectedCommand = 'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\Lifecycle\Input\guest-lifecycle.ps1'
    if ($commandNodes.Count -ne 1 -or $commandNodes[0].InnerText -ne $expectedCommand) {
        throw 'Prepared .wsb logon command differs from the reviewed guest entry point.'
    }
}

function Assert-PreparedInputs {
    param([Parameter(Mandatory)]$Run)

    $expectedNames = @('old.msi', 'corrected.msi', 'expected.json', 'guest-lifecycle.ps1')
    $entries = @($Run.Manifest.input_files)
    if ($entries.Count -ne $expectedNames.Count) {
        throw 'Prepared-run manifest does not contain the exact narrow input set.'
    }
    foreach ($expectedName in $expectedNames) {
        if (@($entries | Where-Object { $_.name -eq $expectedName }).Count -ne 1) {
            throw "Prepared-run input is missing or duplicated: $expectedName"
        }
    }

    $actualEntries = @(Get-ChildItem -LiteralPath $Run.Input -Force)
    if ($actualEntries.Count -ne $expectedNames.Count -or
        @($actualEntries | Where-Object { $_.PSIsContainer }).Count -ne 0) {
        throw 'Prepared input directory contains an unexpected file or directory.'
    }
    foreach ($expectedName in $expectedNames) {
        if (@($actualEntries | Where-Object { $_.Name -eq $expectedName }).Count -ne 1) {
            throw "Prepared input directory differs from its narrow allowlist: $expectedName"
        }
    }

    foreach ($entry in $entries) {
        $name = [string]$entry.name
        if ([IO.Path]::IsPathRooted($name) -or $name -match '(^|[\\/])\.\.([\\/]|$)') {
            throw "Unsafe input manifest path: $name"
        }
        $path = Join-Path $Run.Input $name
        Assert-FileMatches -LiteralPath $path -ExpectedBytes ([long]$entry.bytes) `
            -ExpectedSha256 ([string]$entry.sha256)
    }
    Assert-FileMatches -LiteralPath (Join-Path $Run.Input $script:OldInstaller.file_name) `
        -ExpectedBytes $script:OldInstaller.bytes -ExpectedSha256 $script:OldInstaller.sha256
    Assert-FileMatches -LiteralPath (Join-Path $Run.Input $script:CorrectedInstaller.file_name) `
        -ExpectedBytes $script:CorrectedInstaller.bytes `
        -ExpectedSha256 $script:CorrectedInstaller.sha256

    $repoRoot = Split-Path -Parent $PSScriptRoot
    $reviewedGuestPath = Join-Path $repoRoot 'qa\windows-installer-lifecycle\guest-lifecycle.ps1'
    $reviewedGuest = Get-Item -LiteralPath $reviewedGuestPath -Force
    Assert-FileMatches -LiteralPath (Join-Path $Run.Input 'guest-lifecycle.ps1') `
        -ExpectedBytes $reviewedGuest.Length `
        -ExpectedSha256 (Get-Sha256 -LiteralPath $reviewedGuestPath)

    $expected = Get-Content -LiteralPath (Join-Path $Run.Input 'expected.json') -Raw |
        ConvertFrom-Json
    if ($expected.schema_version -ne 1 -or $expected.run_id -ne $Run.Manifest.run_id -or
        $expected.old.file_name -ne $script:OldInstaller.file_name -or
        $expected.old.release_tag -ne $script:OldInstaller.release_tag -or
        $expected.old.source_commit -ne $script:OldInstaller.source_commit -or
        $expected.old.url -ne $script:OldInstaller.url -or
        [long]$expected.old.bytes -ne $script:OldInstaller.bytes -or
        $expected.old.sha256 -ne $script:OldInstaller.sha256 -or
        $expected.old.updater_dll_sha256 -ne $script:OldInstaller.updater_dll_sha256 -or
        $expected.corrected.file_name -ne $script:CorrectedInstaller.file_name -or
        $expected.corrected.release_tag -ne $script:CorrectedInstaller.release_tag -or
        $expected.corrected.source_commit -ne $script:CorrectedInstaller.source_commit -or
        $expected.corrected.url -ne $script:CorrectedInstaller.url -or
        [long]$expected.corrected.bytes -ne $script:CorrectedInstaller.bytes -or
        $expected.corrected.sha256 -ne $script:CorrectedInstaller.sha256 -or
        $expected.corrected.updater_dll_sha256 -ne $script:CorrectedInstaller.updater_dll_sha256 -or
        $expected.corrected.product_code -ne $script:CorrectedInstaller.product_code -or
        $expected.expected_upgrade_code -ne $script:ExpectedUpgradeCode -or
        $expected.stable_libreoffice_upgrade_code -ne $script:StableLibreOfficeUpgradeCode -or
        $expected.expected_product_version -ne $script:ExpectedProductVersion -or
        $expected.expected_install_root -ne $script:ExpectedInstallRoot -or
        (@($expected.required_steps) -join "`n") -ne ($script:RequiredSteps -join "`n")) {
        throw 'Prepared expected-input manifest differs from the hard-coded release pins.'
    }
    Assert-FileMatches -LiteralPath $Run.WsbPath -ExpectedBytes ([long]$Run.Manifest.wsb.bytes) `
        -ExpectedSha256 ([string]$Run.Manifest.wsb.sha256)
    Assert-WsbPolicy -Run $Run
}

function New-PreparedRun {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $guestSource = Join-Path $repoRoot 'qa\windows-installer-lifecycle\guest-lifecycle.ps1'
    if (-not (Test-Path -LiteralPath $guestSource -PathType Leaf)) {
        throw "Guest lifecycle script is missing: $guestSource"
    }

    if ($RunDirectory) {
        $runPath = Get-FullPath -LiteralPath $RunDirectory
        if (Test-Path -LiteralPath $runPath) {
            throw "Prepare requires a fresh, nonexistent run directory: $runPath"
        }
    }
    else {
        $rootPath = Get-FullPath -LiteralPath $RunRoot
        if (-not (Test-Path -LiteralPath $rootPath)) {
            New-Item -ItemType Directory -Path $rootPath -Force | Out-Null
        }
        Assert-OrdinaryDirectory -LiteralPath $rootPath
        $runId = (Get-Date -Format 'yyyyMMdd-HHmmss-fffffff') + '-' + [guid]::NewGuid().ToString('N')
        $runPath = Join-Path $rootPath $runId
    }

    New-Item -ItemType Directory -Path $runPath | Out-Null
    $inputDirectory = Join-Path $runPath 'input'
    $outputDirectory = Join-Path $runPath 'output'
    New-Item -ItemType Directory -Path $inputDirectory | Out-Null
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
    Assert-OrdinaryDirectory -LiteralPath $runPath
    Assert-OrdinaryDirectory -LiteralPath $inputDirectory
    Assert-OrdinaryDirectory -LiteralPath $outputDirectory

    $runId = Split-Path -Leaf $runPath
    $oldPath = Join-Path $inputDirectory $script:OldInstaller.file_name
    $correctedPath = Join-Path $inputDirectory $script:CorrectedInstaller.file_name
    Write-Host 'Downloading and verifying the exact old release MSI...'
    Invoke-PinnedDownload -Uri $script:OldInstaller.url -Destination $oldPath `
        -ExpectedBytes $script:OldInstaller.bytes -ExpectedSha256 $script:OldInstaller.sha256
    Write-Host 'Downloading and verifying the exact corrected release MSI...'
    Invoke-PinnedDownload -Uri $script:CorrectedInstaller.url -Destination $correctedPath `
        -ExpectedBytes $script:CorrectedInstaller.bytes `
        -ExpectedSha256 $script:CorrectedInstaller.sha256

    $guestDestination = Join-Path $inputDirectory 'guest-lifecycle.ps1'
    Copy-Item -LiteralPath $guestSource -Destination $guestDestination
    $expected = [ordered]@{
        schema_version = 1
        run_id = $runId
        created_at_utc = [DateTime]::UtcNow.ToString('o')
        old = $script:OldInstaller
        corrected = $script:CorrectedInstaller
        expected_upgrade_code = $script:ExpectedUpgradeCode
        stable_libreoffice_upgrade_code = $script:StableLibreOfficeUpgradeCode
        expected_product_version = $script:ExpectedProductVersion
        expected_install_root = $script:ExpectedInstallRoot
        required_steps = $script:RequiredSteps
    }
    $expectedPath = Join-Path $inputDirectory 'expected.json'
    Write-JsonFile -Value $expected -LiteralPath $expectedPath

    $escapedInput = [Security.SecurityElement]::Escape($inputDirectory)
    $escapedOutput = [Security.SecurityElement]::Escape($outputDirectory)
    $wsb = @"
<Configuration>
  <VGpu>Disable</VGpu>
  <Networking>Disable</Networking>
  <AudioInput>Disable</AudioInput>
  <VideoInput>Disable</VideoInput>
  <PrinterRedirection>Disable</PrinterRedirection>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <MemoryInMB>$MemoryInMB</MemoryInMB>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$escapedInput</HostFolder>
      <SandboxFolder>C:\Lifecycle\Input</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
    <MappedFolder>
      <HostFolder>$escapedOutput</HostFolder>
      <SandboxFolder>C:\Lifecycle\Output</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\Lifecycle\Input\guest-lifecycle.ps1</Command>
  </LogonCommand>
</Configuration>
"@
    $wsbPath = Join-Path $runPath 'LibreOfficeMaterial-InstallerLifecycle.wsb'
    $wsb | Set-Content -LiteralPath $wsbPath -Encoding UTF8

    $inputFiles = @()
    foreach ($file in Get-ChildItem -LiteralPath $inputDirectory -File | Sort-Object Name) {
        $inputFiles += [ordered]@{
            name = $file.Name
            bytes = $file.Length
            sha256 = Get-Sha256 -LiteralPath $file.FullName
        }
    }
    $wsbFile = Get-Item -LiteralPath $wsbPath
    $manifest = [ordered]@{
        schema_version = 1
        run_id = $runId
        prepared_at_utc = [DateTime]::UtcNow.ToString('o')
        input_directory = $inputDirectory
        output_directory = $outputDirectory
        input_files = $inputFiles
        wsb = [ordered]@{
            name = $wsbFile.Name
            bytes = $wsbFile.Length
            sha256 = Get-Sha256 -LiteralPath $wsbFile.FullName
        }
        launch_requires_explicit_mode = $true
    }
    Write-JsonFile -Value $manifest -LiteralPath (Join-Path $runPath 'run-manifest.json')
    Get-PreparedRun -LiteralPath $runPath
}

function Assert-FreshOutput {
    param([Parameter(Mandatory)]$Run)
    $entries = @(Get-ChildItem -LiteralPath $Run.Output -Force)
    if ($entries.Count -ne 0) {
        throw "Launch requires a fresh empty output directory: $($Run.Output)"
    }
}

function Assert-OutputArtifacts {
    param([Parameter(Mandatory)]$Run)
    $completePath = Join-Path $Run.Output 'COMPLETE.json'
    $failurePath = Join-Path $Run.Output 'FAILURE.json'
    if (Test-Path -LiteralPath $failurePath -PathType Leaf) {
        Assert-BoundedOrdinaryJsonFile -LiteralPath $failurePath
        $failure = Get-Content -LiteralPath $failurePath -Raw | ConvertFrom-Json
        throw "Sandbox lifecycle failed: $($failure.error)"
    }
    if (-not (Test-Path -LiteralPath $completePath -PathType Leaf)) {
        throw "Completion sentinel is missing: $completePath"
    }

    Assert-BoundedOrdinaryJsonFile -LiteralPath $completePath
    $complete = Get-Content -LiteralPath $completePath -Raw | ConvertFrom-Json
    if ($complete.schema_version -ne 1 -or $complete.status -ne 'passed' `
        -or $complete.run_id -ne $Run.Manifest.run_id) {
        throw 'Completion sentinel does not match this prepared run.'
    }

    $artifactManifestPath = Join-Path $Run.Output 'artifact-manifest.json'
    Assert-FileMatches -LiteralPath $artifactManifestPath `
        -ExpectedBytes ([long]$complete.artifact_manifest_bytes) `
        -ExpectedSha256 ([string]$complete.artifact_manifest_sha256)
    $artifactManifest = Get-Content -LiteralPath $artifactManifestPath -Raw | ConvertFrom-Json
    if ($artifactManifest.schema_version -ne 1 -or $artifactManifest.run_id -ne $Run.Manifest.run_id) {
        throw 'Artifact manifest does not match this prepared run.'
    }

    $outputPrefix = (Get-FullPath -LiteralPath $Run.Output).TrimEnd('\') + '\'
    $seen = @{}
    $seenFullPaths = @{}
    foreach ($entry in @($artifactManifest.files)) {
        $relativePath = [string]$entry.path
        if ([string]::IsNullOrWhiteSpace($relativePath) -or [IO.Path]::IsPathRooted($relativePath) `
            -or $relativePath -match '(^|[\\/])\.\.([\\/]|$)' `
            -or $relativePath -in @('artifact-manifest.json', 'COMPLETE.json', 'FAILURE.json') `
            -or $seen.ContainsKey($relativePath)) {
            throw "Unsafe or duplicate artifact path: $relativePath"
        }
        $seen[$relativePath] = $true
        $artifactPath = Get-FullPath -LiteralPath (Join-Path $Run.Output $relativePath)
        if (-not $artifactPath.StartsWith($outputPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Artifact escapes the output directory: $relativePath"
        }
        Assert-FileMatches -LiteralPath $artifactPath -ExpectedBytes ([long]$entry.bytes) `
            -ExpectedSha256 ([string]$entry.sha256)
        $seenFullPaths[$artifactPath] = $true
    }

    $requiredArtifacts = @(
        'preflight.json',
        'reboot-snapshots.json',
        'results.json',
        '01-old-install.log',
        '02-corrected-same-version-update.log',
        '03-corrected-repair.log',
        '04-corrected-uninstall.log'
    )
    foreach ($requiredArtifact in $requiredArtifacts) {
        if (-not $seen.ContainsKey($requiredArtifact)) {
            throw "Required hash-pinned artifact is missing: $requiredArtifact"
        }
    }

    $actualOutputEntries = @(Get-ChildItem -LiteralPath $Run.Output -Recurse -Force)
    if (@($actualOutputEntries | Where-Object { $_.PSIsContainer }).Count -ne 0) {
        throw 'Completion output contains an unexpected directory.'
    }
    if ($actualOutputEntries.Count -ne (@($artifactManifest.files).Count + 2)) {
        throw 'Completion output contains an unmanifested or missing file.'
    }
    foreach ($outputFile in $actualOutputEntries) {
        $fullPath = Get-FullPath -LiteralPath $outputFile.FullName
        if ($fullPath -ne (Get-FullPath -LiteralPath $completePath) -and
            $fullPath -ne (Get-FullPath -LiteralPath $artifactManifestPath) -and
            -not $seenFullPaths.ContainsKey($fullPath)) {
            throw "Completion output contains an unmanifested file: $fullPath"
        }
    }

    $resultsPath = Join-Path $Run.Output 'results.json'
    $results = Get-Content -LiteralPath $resultsPath -Raw | ConvertFrom-Json
    if ($results.status -ne 'passed' -or $results.run_id -ne $Run.Manifest.run_id `
        -or $results.reboot_state_changed -or $results.lifecycle_reboot_state_changed `
        -or @($results.cleanup_errors).Count -ne 0 `
        -or [int]$results.final_old_product_state -ne -1 `
        -or [int]$results.final_corrected_product_state -ne -1) {
        throw 'Guest result acceptance fields are invalid.'
    }
    $steps = @($results.steps)
    if ($steps.Count -ne $script:RequiredSteps.Count) {
        throw 'Guest result contains an unexpected or missing lifecycle step.'
    }
    foreach ($requiredStep in $script:RequiredSteps) {
        $matches = @($steps | Where-Object { $_.name -eq $requiredStep -and $_.exit_code -eq 0 `
            -and -not $_.reboot_state_changed -and -not $_.cleanup })
        if ($matches.Count -ne 1) {
            throw "Required successful lifecycle step is missing or duplicated: $requiredStep"
        }
    }

    $preflight = Get-Content -LiteralPath (Join-Path $Run.Output 'preflight.json') -Raw |
        ConvertFrom-Json
    if ($preflight.schema_version -ne 1 -or $preflight.run_id -ne $Run.Manifest.run_id `
        -or -not $preflight.high_integrity) {
        throw 'Guest preflight artifact is invalid.'
    }

    $snapshots = @(Get-Content -LiteralPath `
        (Join-Path $Run.Output 'reboot-snapshots.json') -Raw | ConvertFrom-Json)
    if ($snapshots.Count -ne (($script:RequiredSteps.Count * 2) + 2)) {
        throw 'Guest did not publish the exact per-step and whole-lifecycle reboot snapshots.'
    }
    foreach ($requiredStep in @($script:RequiredSteps) + @('__lifecycle__')) {
        foreach ($phase in @('before', 'after')) {
            if (@($snapshots | Where-Object {
                $_.step -eq $requiredStep -and $_.phase -eq $phase
            }).Count -ne 1) {
                throw "Required reboot snapshot is missing or duplicated: $requiredStep/$phase"
            }
        }
        $before = @($snapshots | Where-Object {
            $_.step -eq $requiredStep -and $_.phase -eq 'before'
        })[0].state
        $after = @($snapshots | Where-Object {
            $_.step -eq $requiredStep -and $_.phase -eq 'after'
        })[0].state
        if ((Get-RebootFingerprint -Snapshot $before) -ne
            (Get-RebootFingerprint -Snapshot $after)) {
            throw "Host recomputation found a reboot-state change: $requiredStep"
        }
    }
    $complete
}

function Assert-HostVerification {
    param([Parameter(Mandatory)]$Run)

    $beforePath = Join-Path $Run.Root 'host-before.json'
    $afterPath = Join-Path $Run.Root 'host-after.json'
    $verificationPath = Join-Path $Run.Root 'host-verification.json'
    foreach ($path in @($beforePath, $afterPath, $verificationPath)) {
        Assert-BoundedOrdinaryJsonFile -LiteralPath $path
    }

    $before = Get-Content -LiteralPath $beforePath -Raw | ConvertFrom-Json
    $after = Get-Content -LiteralPath $afterPath -Raw | ConvertFrom-Json
    $verification = Get-Content -LiteralPath $verificationPath -Raw | ConvertFrom-Json
    if ($verification.schema_version -ne 1 -or
        $verification.run_id -ne $Run.Manifest.run_id -or
        $verification.status -ne 'passed' -or
        -not $verification.sandbox_disposed -or
        [int]$verification.sandbox_processes_after -ne 0 -or
        -not $verification.host_safety_unchanged -or
        [int]$verification.launch_process_id -le 0) {
        throw 'Host verification acceptance fields are invalid.'
    }
    if ((Get-Sha256 -LiteralPath $beforePath) -ne $verification.host_before_sha256 -or
        (Get-Sha256 -LiteralPath $afterPath) -ne $verification.host_after_sha256) {
        throw 'Host verification snapshot hashes do not match the retained files.'
    }
    if ((Get-HostSafetyFingerprint -Snapshot $before) -ne
        (Get-HostSafetyFingerprint -Snapshot $after)) {
        throw 'Host verification snapshots do not preserve the host safety state.'
    }
    $verification
}

function Wait-ForSandboxResult {
    param([Parameter(Mandatory)]$Run)
    $deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
    $completePath = Join-Path $Run.Output 'COMPLETE.json'
    $failurePath = Join-Path $Run.Output 'FAILURE.json'
    while ([DateTime]::UtcNow -lt $deadline) {
        if ((Test-Path -LiteralPath $completePath -PathType Leaf) `
            -or (Test-Path -LiteralPath $failurePath -PathType Leaf)) {
            Start-Sleep -Seconds 1
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "Timed out after $TimeoutMinutes minutes. The Sandbox was not force-closed; inspect it and $($Run.Output)."
}

switch ($Mode) {
    'Prepare' {
        $run = New-PreparedRun
        Assert-PreparedInputs -Run $run
        Write-Host ''
        Write-Host 'Prepared and pinned. Windows Sandbox was not launched.' -ForegroundColor Green
        Write-Host ("Run directory: {0}" -f $run.Root)
        Write-Host 'Review the generated input manifest and .wsb, then explicitly launch with:'
        Write-Host ("& `"{0}`" -Mode Launch -RunDirectory `"{1}`"" -f $PSCommandPath, $run.Root) `
            -ForegroundColor Yellow
        return
    }
    'Inspect' {
        if ([string]::IsNullOrWhiteSpace($RunDirectory)) {
            throw 'Inspect requires -RunDirectory from a completed Prepare invocation.'
        }
        $run = Get-PreparedRun -LiteralPath $RunDirectory
        Assert-PreparedInputs -Run $run
        Assert-FreshOutput -Run $run
        Write-Host ("Prepared Sandbox run is pinned, current, and launch-ready: {0}" -f $run.Root) `
            -ForegroundColor Green
        return
    }
    'Launch' {
        if ([string]::IsNullOrWhiteSpace($RunDirectory)) {
            throw 'Launch requires -RunDirectory from a completed Prepare invocation.'
        }
        $run = Get-PreparedRun -LiteralPath $RunDirectory
        Assert-PreparedInputs -Run $run
        Assert-FreshOutput -Run $run
        $sandboxExecutable = Assert-SandboxReady
        $existingSandboxProcesses = @(Get-WindowsSandboxProcesses)
        if ($existingSandboxProcesses.Count -ne 0) {
            $summary = @($existingSandboxProcesses | ForEach-Object { "$($_.name):$($_.id)" }) -join ', '
            throw "Launch requires no pre-existing Windows Sandbox client: $summary"
        }
        $hostBefore = Get-HostSafetySnapshot
        Write-JsonFile -Value $hostBefore -LiteralPath (Join-Path $run.Root 'host-before.json')
        $complete = $null
        $launchError = $null
        $hostSafetyError = $null
        $disposalError = $null
        $sandboxLaunched = $false
        try {
            Write-Host 'Launching the reviewed Windows Sandbox configuration...' -ForegroundColor Yellow
            $sandboxProcess = Start-Process -FilePath $sandboxExecutable `
                -ArgumentList ('"{0}"' -f $run.WsbPath) -PassThru
            $sandboxLaunched = $true
            Wait-ForSandboxResult -Run $run
            $complete = Assert-OutputArtifacts -Run $run
        }
        catch {
            $launchError = $_
        }
        finally {
            if ($sandboxLaunched) {
                try {
                    Wait-ForWindowsSandboxDisposal -Run $run
                }
                catch {
                    $disposalError = $_
                }
            }
            try {
                $hostAfter = Get-HostSafetySnapshot
                Write-JsonFile -Value $hostAfter `
                    -LiteralPath (Join-Path $run.Root 'host-after.json')
                if ((Get-HostSafetyFingerprint -Snapshot $hostBefore) -ne `
                    (Get-HostSafetyFingerprint -Snapshot $hostAfter)) {
                    throw 'Host reboot or LibreOffice registration state changed while the Sandbox test ran.'
                }
            }
            catch {
                $hostSafetyError = $_
            }
        }
        if ($disposalError) {
            if ($launchError) {
                throw "Sandbox lifecycle failed ($($launchError.Exception.Message)); disposal validation also failed: $($disposalError.Exception.Message)"
            }
            throw $disposalError
        }
        if ($hostSafetyError) {
            if ($launchError) {
                throw "Sandbox lifecycle failed ($($launchError.Exception.Message)); host safety validation also failed: $($hostSafetyError.Exception.Message)"
            }
            throw $hostSafetyError
        }
        if ($launchError) {
            throw $launchError
        }
        $hostVerification = [ordered]@{
            schema_version = 1
            run_id = $run.Manifest.run_id
            status = 'passed'
            completed_at_utc = [DateTime]::UtcNow.ToString('o')
            guest_completed_at_utc = $complete.completed_at_utc
            launch_process_id = [int]$sandboxProcess.Id
            sandbox_disposed = $true
            sandbox_processes_after = @(Get-WindowsSandboxProcesses).Count
            host_safety_unchanged = $true
            host_before_sha256 = Get-Sha256 -LiteralPath (Join-Path $run.Root 'host-before.json')
            host_after_sha256 = Get-Sha256 -LiteralPath (Join-Path $run.Root 'host-after.json')
        }
        Write-JsonFile -Value $hostVerification `
            -LiteralPath (Join-Path $run.Root 'host-verification.json')
        [void](Assert-HostVerification -Run $run)
        Write-Host ("Disposable MSI lifecycle passed at {0}." -f $complete.completed_at_utc) `
            -ForegroundColor Green
        return
    }
    'Verify' {
        if ([string]::IsNullOrWhiteSpace($RunDirectory)) {
            throw 'Verify requires -RunDirectory.'
        }
        $run = Get-PreparedRun -LiteralPath $RunDirectory
        Assert-PreparedInputs -Run $run
        $complete = Assert-OutputArtifacts -Run $run
        [void](Assert-HostVerification -Run $run)
        Write-Host ("Verified host-attested disposable MSI lifecycle from {0}." -f $complete.completed_at_utc) `
            -ForegroundColor Green
        return
    }
}
