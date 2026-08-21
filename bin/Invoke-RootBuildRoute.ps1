#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Bootstrap', 'Program', 'Installer')]
    [string] $Route,
    [Parameter(ValueFromRemainingArguments)]
    [string[]] $RouteArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$forward = [System.Collections.Generic.List[string]]::new()
$silent = $env:SILENT -eq '1'
foreach ($argument in @($RouteArguments)) {
    if ($argument -in @('/s', '--silent')) { $silent = $true; continue }
    $forward.Add($argument)
}
$phase = switch ($Route) {
    'Bootstrap' { 'Bootstrap' }
    'Program' { 'Program' }
    'Installer' { 'All' }
}
Write-Host ('Root build route: {0}; silent: {1}; signing: disabled by policy' -f $Route, $silent)
$engine = Join-Path $PSScriptRoot 'Build-Windows.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $engine -Phase $phase @forward
exit $LASTEXITCODE
