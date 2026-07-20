[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PayloadRoot,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$SourceCommit,

    [ValidateSet('Light', 'Dark', 'HighContrast')]
    [string]$Appearance = 'Light',

    [string]$DriverRoot = '',

    [string]$OutputRoot = '',

    [string]$RunId = '',

    [string]$McpUrl = '',

    [switch]$KeyboardFocus,

    [switch]$Templates
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;

public static class LibreOfficeMaterialProcessPath
{
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr OpenProcess(uint access, bool inheritHandle, uint processId);

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool QueryFullProcessImageName(
        IntPtr process, uint flags, StringBuilder path, ref uint size);

    [DllImport("kernel32.dll")]
    private static extern bool CloseHandle(IntPtr handle);

    public static string Get(uint processId)
    {
        const uint QueryLimitedInformation = 0x1000;
        IntPtr process = OpenProcess(QueryLimitedInformation, false, processId);
        if (process == IntPtr.Zero)
            throw new Win32Exception(Marshal.GetLastWin32Error());
        try
        {
            uint size = 32768;
            var path = new StringBuilder((int)size);
            if (!QueryFullProcessImageName(process, 0, path, ref size))
                throw new Win32Exception(Marshal.GetLastWin32Error());
            return path.ToString();
        }
        finally
        {
            CloseHandle(process);
        }
    }
}
'@

function Write-Utf8Lf {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [string]$Text
    )

    $normalized = $Text.Replace("`r`n", "`n").Replace("`r", "`n")
    [System.IO.File]::WriteAllText(
        $Path,
        $normalized,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [object]$Value
    )

    Write-Utf8Lf -Path $Path -Text (($Value | ConvertTo-Json -Depth 20) + "`n")
}

function Invoke-LowLevelTool {
    param(
        [Parameter(Mandatory = $true)] [string]$Tool,
        [hashtable]$Arguments = @{},
        [int]$TimeoutSeconds = 60
    )

    $argumentsJson = $Arguments | ConvertTo-Json -Compress -Depth 10
    $output = & uv run --directory $script:ResolvedDriverRoot python `
        $script:McpClientPath --url $script:McpUrl --tool $Tool `
        --arguments-json $argumentsJson --timeout $TimeoutSeconds 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = ($output | ForEach-Object { $_.ToString() }) -join "`n"
    if ($exitCode -ne 0) {
        throw "Low-level MCP tool '$Tool' failed with exit code ${exitCode}: $outputText"
    }
    try {
        return $outputText | ConvertFrom-Json
    }
    catch {
        throw "Low-level MCP tool '$Tool' returned invalid JSON: $outputText"
    }
}

function Get-FreeLoopbackPort {
    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        0
    )
    try {
        $listener.Start()
        return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    }
    finally {
        $listener.Stop()
    }
}

function Get-ExactPayloadProcesses {
    param([Parameter(Mandatory = $true)] [string]$ProgramRoot)

    $prefix = [System.IO.Path]::GetFullPath($ProgramRoot).TrimEnd('\') + '\'
    $matches = [System.Collections.Generic.List[object]]::new()
    foreach ($process in @(Get-Process -Name 'soffice', 'soffice.bin' -ErrorAction SilentlyContinue)) {
        try {
            $actual = [System.IO.Path]::GetFullPath(
                [LibreOfficeMaterialProcessPath]::Get([uint32]$process.Id)
            )
            if ($actual.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                $matches.Add([pscustomobject]@{
                    ProcessId = $process.Id
                    Name = $process.ProcessName
                    ExecutablePath = $actual
                    CreationDate = $process.StartTime
                })
            }
        }
        catch [System.ArgumentException] {
            # The process exited between enumeration and the path query.
        }
        catch [System.InvalidOperationException] {
            # The process exited between enumeration and the path query.
        }
    }
    return @($matches)
}

function Get-OwnedProcess {
    param(
        [Parameter(Mandatory = $true)] [int]$ProcessId,
        [Parameter(Mandatory = $true)] [string]$ProgramRoot
    )

    $process = Get-Process -Id $ProcessId -ErrorAction Stop
    $prefix = [System.IO.Path]::GetFullPath($ProgramRoot).TrimEnd('\') + '\'
    $actual = [System.IO.Path]::GetFullPath(
        [LibreOfficeMaterialProcessPath]::Get([uint32]$ProcessId)
    )
    if (-not $actual.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Run PID $ProcessId belongs to '$actual', outside exact payload '$prefix'."
    }
    return [pscustomobject]@{
        ProcessId = $process.Id
        Name = $process.ProcessName
        ExecutablePath = $actual
        CreationDate = $process.StartTime
    }
}

function Invoke-PayloadPython {
    param(
        [Parameter(Mandatory = $true)] [string[]]$Arguments,
        [int]$TimeoutSeconds = 75
    )

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $script:PayloadPython
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    foreach ($argument in $Arguments) {
        $startInfo.ArgumentList.Add($argument)
    }
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    try {
        if (-not $process.Start()) {
            throw 'Payload Python process did not start.'
        }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill($true)
            $process.WaitForExit()
            throw "Payload Python exceeded the ${TimeoutSeconds}-second timeout and its exact process tree was stopped."
        }
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        $outputText = (@($stdout, $stderr) | Where-Object { $_ }) -join "`n"
        if ($process.ExitCode -ne 0) {
            throw "Payload Python failed with exit code $($process.ExitCode): $outputText"
        }
        return $outputText
    }
    finally {
        $process.Dispose()
    }
}

function Analyze-Screenshot {
    param([Parameter(Mandatory = $true)] [string]$Path)

    $output = & uv run --directory $script:ResolvedDriverRoot python `
        $script:PngAnalyzerPath $Path 2>&1
    $exitCode = $LASTEXITCODE
    $outputText = ($output | ForEach-Object { $_.ToString() }) -join "`n"
    if ($exitCode -ne 0) {
        throw "Screenshot analysis failed with exit code ${exitCode}: $outputText"
    }
    $analysis = $outputText | ConvertFrom-Json
    if (-not $analysis.nonblank -or $analysis.width -lt 640 -or $analysis.height -lt 480) {
        throw "Screenshot '$Path' is blank or unexpectedly small."
    }
    return $analysis
}

function Assert-A11yReport {
    param(
        [Parameter(Mandatory = $true)] [object]$Report,
        [switch]$RequireFocused
    )

    if ($Report.PSObject.Properties.Name -contains 'fatal_error') {
        throw "Accessibility collection failed: $($Report.fatal_error)"
    }
    if ($Report.summary.node_count -le 0 -or $Report.summary.visible_nodes -le 0) {
        throw 'Accessibility collection returned no visible nodes.'
    }
    if ($Report.summary.partial -or $Report.summary.errors -ne 0) {
        throw "Accessibility collection was partial or reported errors: $($Report.summary | ConvertTo-Json -Compress)"
    }
    $focused = @($Report.nodes | Where-Object { @($_.states) -contains 'FOCUSED' })
    if ($RequireFocused -and $focused.Count -eq 0) {
        throw 'Keyboard focus scenario exposed no FOCUSED accessibility node.'
    }
    return [ordered]@{
        node_count = [int]$Report.summary.node_count
        visible_nodes = [int]$Report.summary.visible_nodes
        errors = [int]$Report.summary.errors
        partial = [bool]$Report.summary.partial
        focused_node_count = $focused.Count
        focused_nodes = @($focused | ForEach-Object {
            [ordered]@{ path = @($_.path); role = $_.role.name; name = $_.name }
        })
    }
}

function Capture-State {
    param(
        [Parameter(Mandatory = $true)] [string]$Slug,
        [switch]$RequireFocused,
        [switch]$Terminate
    )

    $screenshotPath = Join-Path $script:ScreenshotsRoot "$Slug.png"
    $capture = Invoke-LowLevelTool -Tool 'screenshot' -Arguments @{
        hwnd = [long]$script:WindowHandle
        output_path = $screenshotPath
    } -TimeoutSeconds 60
    if (-not $capture.rendered_ok) {
        throw "PrintWindow did not render '$Slug'."
    }
    $image = Analyze-Screenshot -Path $screenshotPath
    if ([int]$capture.width -ne [int]$image.width -or
        [int]$capture.height -ne [int]$image.height) {
        throw "Capture dimensions and PNG dimensions disagree for '$Slug'."
    }

    $a11yPath = Join-Path $script:LogsRoot "a11y-$Slug.json"
    $progressPath = Join-Path $script:LogsRoot "a11y-$Slug-progress.json"
    $arguments = @(
        $script:A11yCollectorPath,
        '--pipe', $script:UnoPipe,
        '--output', $a11yPath,
        '--run-id', $script:RunId,
        '--screenshot-sha256', [string]$image.sha256,
        '--progress-output', $progressPath,
        '--timeout', '45',
        '--require-visible'
    )
    if ($Terminate) {
        $arguments += '--terminate'
    }
    Invoke-PayloadPython -Arguments $arguments -TimeoutSeconds 75 | Out-Null
    $a11y = Get-Content -LiteralPath $a11yPath -Raw | ConvertFrom-Json
    $a11ySummary = Assert-A11yReport -Report $a11y -RequireFocused:$RequireFocused
    $a11yFile = Get-Item -LiteralPath $a11yPath
    $a11yHash = (Get-FileHash -LiteralPath $a11yPath -Algorithm SHA256).Hash.ToLowerInvariant()

    return [ordered]@{
        slug = $Slug
        screenshot = $image
        capture_api = 'PrintWindow through low-level computer-use MCP'
        accessibility = [ordered]@{
            path = $a11yPath
            bytes = [long]$a11yFile.Length
            sha256 = $a11yHash
            screenshot_sha256 = [string]$a11y.screenshot_sha256
            summary = $a11ySummary
        }
    }
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$payloadFull = [System.IO.Path]::GetFullPath($PayloadRoot)
$programRoot = Join-Path $payloadFull 'program'
$script:PayloadPython = Join-Path $programRoot 'python.exe'
$soffice = Join-Path $programRoot 'soffice.exe'
$script:McpClientPath = Join-Path $PSScriptRoot 'call-lowlevel-mcp.py'
$script:PngAnalyzerPath = Join-Path $PSScriptRoot 'analyze-png.py'
$script:A11yCollectorPath = Join-Path $PSScriptRoot 'dump-a11y.py'
$script:McpUrl = $McpUrl

if (-not $DriverRoot) {
    $script:ResolvedDriverRoot = [System.IO.Path]::GetFullPath(
        (Join-Path $repoRoot '..\lowlevel-computer-use-mcp')
    )
}
else {
    $script:ResolvedDriverRoot = [System.IO.Path]::GetFullPath($DriverRoot)
}
if (-not $OutputRoot) {
    $OutputRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'LibreOfficeMaterialQA'
}
$outputFull = [System.IO.Path]::GetFullPath($OutputRoot)

foreach ($required in @(
    $soffice,
    $script:PayloadPython,
    $script:McpClientPath,
    $script:PngAnalyzerPath,
    $script:A11yCollectorPath,
    (Join-Path $script:ResolvedDriverRoot 'pyproject.toml')
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required file is missing: $required"
    }
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is required to run the sibling low-level MCP client environment.'
}

$driverCommit = (& git -C $script:ResolvedDriverRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $driverCommit -notmatch '^[0-9a-f]{40}$') {
    throw 'Could not resolve the sibling low-level driver commit.'
}
$driverStatus = @(& git -C $script:ResolvedDriverRoot status --porcelain)
if ($LASTEXITCODE -ne 0 -or $driverStatus.Count -ne 0) {
    throw 'The sibling low-level driver checkout must be clean for accepted evidence.'
}

$sourceLower = $SourceCommit.ToLowerInvariant()
$shortCommit = $sourceLower.Substring(0, 10)
$appearanceSlug = $Appearance.ToLowerInvariant()
if (-not $RunId) {
    $RunId = '{0}-{1}-windows-headless-{2}' -f `
        (Get-Date -Format 'yyyyMMdd-HHmmss'), $shortCommit, $appearanceSlug
}
if ($RunId -notmatch '^[A-Za-z0-9._-]+$') {
    throw 'RunId may contain only letters, numbers, dot, underscore, and hyphen.'
}
$script:RunId = $RunId
$runRoot = Join-Path $outputFull $RunId
if (Test-Path -LiteralPath $runRoot) {
    throw "Run directory already exists: $runRoot"
}
$script:ScreenshotsRoot = Join-Path $runRoot 'screenshots'
$script:LogsRoot = Join-Path $runRoot 'logs'
$profileRoot = Join-Path $runRoot 'profile'
$profileUserRoot = Join-Path $profileRoot 'user'
New-Item -ItemType Directory -Path $script:ScreenshotsRoot, $script:LogsRoot, $profileUserRoot -Force | Out-Null

$appearanceValue = if ($Appearance -eq 'Dark') { 2 } else { 1 }
$highContrastValue = if ($Appearance -eq 'HighContrast') { 2 } else { 1 }
$profileConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="FirstRun" oor:op="fuse"><value>false</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Appearance"><prop oor:name="ApplicationAppearance" oor:op="fuse"><value>$appearanceValue</value></prop></item>
<item oor:path="/org.openoffice.Office.Common/Accessibility"><prop oor:name="HighContrast" oor:op="fuse"><value>$highContrastValue</value></prop></item>
</oor:items>
"@
Write-Utf8Lf -Path (Join-Path $profileUserRoot 'registrymodifications.xcu') -Text $profileConfig

$script:UnoPipe = "LibreOfficeMaterialQA-$shortCommit-$appearanceSlug-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$desktopName = "LOMaterialQA-$shortCommit-$appearanceSlug-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
if ($desktopName.Length -gt 64) {
    throw 'Generated desktop name exceeds the driver contract.'
}
$pidPath = Join-Path $runRoot 'soffice.pid'
$stdoutPath = Join-Path $script:LogsRoot 'soffice.stdout.log'
$stderrPath = Join-Path $script:LogsRoot 'soffice.stderr.log'
$wrapperPath = Join-Path $runRoot 'launch-headless.cmd'
$profileUri = [System.Uri]::new($profileRoot).AbsoluteUri
$wrapper = @"
@echo off
setlocal DisableDelayedExpansion
set "VCL_DRAW_WIDGETS_FROM_FILE=1"
set "VCL_FILE_WIDGET_THEME=material"
set "SAL_SKIA=raster"
set "SAL_DISABLEGL=1"
set "SAL_LOG=+WARN.vcl.gdi"
"$soffice" -env:UserInstallation=$profileUri --nologo --norestore --quickstart=no --language=en-US --pidfile="$pidPath" --accept=pipe,name=$($script:UnoPipe);urp 1>"$stdoutPath" 2>"$stderrPath"
exit /b %ERRORLEVEL%
"@
Write-Utf8Lf -Path $wrapperPath -Text $wrapper

$existing = @(Get-ExactPayloadProcesses -ProgramRoot $programRoot)
if ($existing.Count -ne 0) {
    throw "Exact payload already has running processes: $($existing | ConvertTo-Json -Compress)"
}

$results = [ordered]@{
    schema_version = 1
    run_id = $RunId
    status = 'running'
    generated_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    source_commit = $sourceLower
    payload_root = $payloadFull
    appearance = $Appearance
    profile_values = [ordered]@{
        ApplicationAppearance = $appearanceValue
        HighContrast = $highContrastValue
    }
    environment = [ordered]@{
        VCL_DRAW_WIDGETS_FROM_FILE = '1'
        VCL_FILE_WIDGET_THEME = 'material'
        SAL_SKIA = 'raster'
        SAL_DISABLEGL = '1'
        SAL_LOG = '+WARN.vcl.gdi'
    }
    driver = [ordered]@{
        root = $script:ResolvedDriverRoot
        commit = $driverCommit
        checkout_clean = $true
        mcp_url = $null
        dedicated_server = $false
        server_pid = $null
        desktop_name = $desktopName
    }
    process = $null
    window = $null
    scenarios = @()
    cleanup = [ordered]@{
        normal_uno_termination = $false
        forced_owned_process_cleanup = $false
        remaining_payload_processes = $null
        remaining_headless_windows = $null
        desktop_closed = $false
        dedicated_driver_stopped = $null
    }
    error = $null
}

$desktopCreated = $false
$dedicatedDriver = $null
$ownedPid = $null
$pidFilePid = $null
$normalTermination = $false
$fatal = $null
$script:WindowHandle = $null
try {
    if ($McpUrl) {
        $script:McpUrl = $McpUrl
    }
    else {
        $driverPort = Get-FreeLoopbackPort
        $script:McpUrl = "http://127.0.0.1:$driverPort/mcp"
        $driverStdout = Join-Path $script:LogsRoot 'lowlevel-mcp.stdout.log'
        $driverStderr = Join-Path $script:LogsRoot 'lowlevel-mcp.stderr.log'
        $uvPath = (Get-Command uv -ErrorAction Stop).Source
        $dedicatedDriver = Start-Process -FilePath $uvPath -ArgumentList @(
            'run',
            '--directory', $script:ResolvedDriverRoot,
            'lowlevel-computer-use-mcp',
            '--http',
            '--host', '127.0.0.1',
            '--port', [string]$driverPort
        ) -WindowStyle Hidden -RedirectStandardOutput $driverStdout `
            -RedirectStandardError $driverStderr -PassThru
        $results.driver.dedicated_server = $true
        $results.driver.server_pid = [int]$dedicatedDriver.Id
    }
    $results.driver.mcp_url = $script:McpUrl

    $serverDeadline = [DateTimeOffset]::UtcNow.AddSeconds(30)
    $serverReady = $false
    while ([DateTimeOffset]::UtcNow -lt $serverDeadline) {
        if ($dedicatedDriver -and $dedicatedDriver.HasExited) {
            throw "Dedicated low-level MCP server exited with code $($dedicatedDriver.ExitCode)."
        }
        try {
            Invoke-LowLevelTool -Tool 'get_screen_size' -Arguments @{} `
                -TimeoutSeconds 5 | Out-Null
            $serverReady = $true
            break
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $serverReady) {
        throw "Low-level MCP server did not become ready at $($script:McpUrl)."
    }

    Invoke-LowLevelTool -Tool 'create_headless_desktop' -Arguments @{ name = $desktopName } | Out-Null
    $desktopCreated = $true
    $launchCommand = 'cmd.exe /d /c call "{0}"' -f $wrapperPath
    $launcher = Invoke-LowLevelTool -Tool 'launch_on_headless_desktop' -Arguments @{
        name = $desktopName
        command = $launchCommand
    }

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(90)
    $stableHandle = $null
    $stableCount = 0
    $lastWindows = $null
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        if (-not $pidFilePid -and (Test-Path -LiteralPath $pidPath -PathType Leaf)) {
            $pidText = (Get-Content -LiteralPath $pidPath -Raw).Trim()
            if ($pidText -match '^\d+$') {
                # LibreOffice's small soffice.exe launcher can write its PID and
                # exit after handing off to soffice.bin.  Keep that PID as
                # provenance, but resolve the surviving owned process by exact
                # executable path; the preflight required that set to be empty.
                $pidFilePid = [int]$pidText
            }
        }
        if (-not $ownedPid) {
            $payloadProcesses = @(Get-ExactPayloadProcesses -ProgramRoot $programRoot)
            $owned = @($payloadProcesses | Sort-Object @{
                Expression = { if ($_.Name -ieq 'soffice.bin') { 0 } else { 1 } }
            }, CreationDate | Select-Object -First 1)
            if ($owned.Count -eq 1) {
                $ownedPid = [int]$owned[0].ProcessId
                $results.process = [ordered]@{
                    pid = $ownedPid
                    pidfile_pid = $pidFilePid
                    launcher_pid = [int]$launcher.pid
                    name = [string]$owned[0].Name
                    executable_path = [string]$owned[0].ExecutablePath
                    creation_date = [string]$owned[0].CreationDate
                }
            }
        }
        $lastWindows = Invoke-LowLevelTool -Tool 'list_headless_windows' -Arguments @{
            name = $desktopName
        } -TimeoutSeconds 15
        $candidate = @($lastWindows.windows | Where-Object {
            $_.class -eq 'SALFRAME' -and $_.title -match 'LibreOffice' -and
            [int]$_.width -ge 640 -and [int]$_.height -ge 480
        }) | Select-Object -First 1
        if ($candidate) {
            if ($stableHandle -eq [long]$candidate.handle) {
                $stableCount++
            }
            else {
                $stableHandle = [long]$candidate.handle
                $stableCount = 1
            }
        }
        else {
            $stableHandle = $null
            $stableCount = 0
        }
        if ($ownedPid -and $stableCount -ge 3) {
            $script:WindowHandle = $stableHandle
            $results.window = [ordered]@{
                handle = $script:WindowHandle
                title = [string]$candidate.title
                class = [string]$candidate.class
                width = [int]$candidate.width
                height = [int]$candidate.height
                stable_poll_count = $stableCount
            }
            break
        }
        Start-Sleep -Milliseconds 750
    }
    if (-not $ownedPid -or -not $script:WindowHandle) {
        throw "LibreOffice did not expose a stable owned window in 90 seconds. Last windows: $($lastWindows | ConvertTo-Json -Compress -Depth 8)"
    }

    $scenarioList = [System.Collections.Generic.List[object]]::new()
    $scenarioList.Add((Capture-State -Slug "start-center-$appearanceSlug"))

    if ($KeyboardFocus) {
        Invoke-LowLevelTool -Tool 'win_send_keys' -Arguments @{
            hwnd = [long]$script:WindowHandle
            keys = @('tab')
        } | Out-Null
        Start-Sleep -Milliseconds 750
        $scenarioList.Add((Capture-State -Slug "start-center-$appearanceSlug-keyboard-focus" -RequireFocused))
    }

    if ($Templates) {
        Invoke-LowLevelTool -Tool 'mouse_click' -Arguments @{
            hwnd = [long]$script:WindowHandle
            x = 140
            y = 330
            button = 'left'
            clicks = 1
        } | Out-Null
        Start-Sleep -Seconds 2
        $scenarioList.Add((Capture-State -Slug "start-center-templates-$appearanceSlug"))
    }

    $finalScenario = $scenarioList[$scenarioList.Count - 1]
    $finalSlug = [string]$finalScenario.slug
    $terminatedScenario = Capture-State -Slug $finalSlug -Terminate `
        -RequireFocused:($KeyboardFocus -and -not $Templates)
    $scenarioList[$scenarioList.Count - 1] = $terminatedScenario
    $results.scenarios = @($scenarioList)
    $normalTermination = $true
    $results.cleanup.normal_uno_termination = $true

    $exitDeadline = [DateTimeOffset]::UtcNow.AddSeconds(30)
    while ([DateTimeOffset]::UtcNow -lt $exitDeadline) {
        $remaining = @(Get-ExactPayloadProcesses -ProgramRoot $programRoot)
        $windowsAfter = Invoke-LowLevelTool -Tool 'list_headless_windows' -Arguments @{
            name = $desktopName
        } -TimeoutSeconds 15
        if ($remaining.Count -eq 0 -and [int]$windowsAfter.count -eq 0) {
            break
        }
        Start-Sleep -Milliseconds 500
    }
    $remaining = @(Get-ExactPayloadProcesses -ProgramRoot $programRoot)
    $windowsAfter = Invoke-LowLevelTool -Tool 'list_headless_windows' -Arguments @{
        name = $desktopName
    } -TimeoutSeconds 15
    if ($remaining.Count -ne 0 -or [int]$windowsAfter.count -ne 0) {
        throw 'LibreOffice did not fully exit after normal UNO termination.'
    }
    $results.status = 'passed'
}
catch {
    $fatal = $_.Exception
    $results.status = 'failed'
    $results.error = "{0}: {1}" -f $_.Exception.GetType().Name, $_.Exception.Message
}
finally {
    try {
        $remaining = @(Get-ExactPayloadProcesses -ProgramRoot $programRoot)
        if ($remaining.Count -ne 0 -and -not $normalTermination) {
            foreach ($remainingProcess in $remaining) {
                $remainingPid = [int]$remainingProcess.ProcessId
                Get-OwnedProcess -ProcessId $remainingPid -ProgramRoot $programRoot | Out-Null
                Stop-Process -Id $remainingPid -Force -ErrorAction Stop
            }
            $results.cleanup.forced_owned_process_cleanup = $true
            Start-Sleep -Seconds 1
            $remaining = @(Get-ExactPayloadProcesses -ProgramRoot $programRoot)
        }
        $results.cleanup.remaining_payload_processes = $remaining.Count
    }
    catch {
        if (-not $fatal) { $fatal = $_.Exception }
        $results.status = 'failed'
        if (-not $results.error) {
            $results.error = "Cleanup process error: $($_.Exception.Message)"
        }
    }

    if ($desktopCreated) {
        try {
            $windowsFinal = Invoke-LowLevelTool -Tool 'list_headless_windows' -Arguments @{
                name = $desktopName
            } -TimeoutSeconds 15
            $results.cleanup.remaining_headless_windows = [int]$windowsFinal.count
            $closed = Invoke-LowLevelTool -Tool 'close_headless_desktop' -Arguments @{
                name = $desktopName
            } -TimeoutSeconds 15
            $results.cleanup.desktop_closed = [bool]$closed.closed
            if (-not $closed.closed) {
                throw 'The long-lived low-level MCP server did not close its desktop handle.'
            }
        }
        catch {
            if (-not $fatal) { $fatal = $_.Exception }
            $results.status = 'failed'
            if (-not $results.error) {
                $results.error = "Desktop cleanup error: $($_.Exception.Message)"
            }
        }
    }
    if ($dedicatedDriver) {
        try {
            if (-not $dedicatedDriver.HasExited) {
                $dedicatedDriver.Kill($true)
                $dedicatedDriver.WaitForExit(15000) | Out-Null
            }
            $results.cleanup.dedicated_driver_stopped = $dedicatedDriver.HasExited
            if (-not $results.cleanup.dedicated_driver_stopped) {
                throw 'The dedicated low-level MCP process tree did not stop.'
            }
        }
        catch {
            if (-not $fatal) { $fatal = $_.Exception }
            $results.status = 'failed'
            if (-not $results.error) {
                $results.error = "Dedicated driver cleanup error: $($_.Exception.Message)"
            }
        }
        finally {
            $dedicatedDriver.Dispose()
        }
    }
    Write-JsonFile -Path (Join-Path $runRoot 'results.json') -Value $results
}

if ($fatal) {
    throw "Headless smoke failed; evidence retained at '$runRoot': $($fatal.Message)"
}
$results | ConvertTo-Json -Depth 20
