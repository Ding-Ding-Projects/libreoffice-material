#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
foreach ($name in @('download-dependencies.bat', 'build.bat', 'build-installer.bat')) {
    $path = Join-Path $root $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing root route: $name" }
    if ((Get-Content -LiteralPath $path -Raw) -notmatch 'Invoke-RootBuildRoute[.]ps1') {
        throw "$name does not use the reviewed root dispatcher."
    }
}
$dispatcher = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Invoke-RootBuildRoute.ps1') -Raw
foreach ($needle in @("'/s'", "'--silent'", "\$env:SILENT -eq '1'", "'Installer' \{ 'All' \}")) {
    if ($dispatcher -notmatch $needle) { throw "Dispatcher contract is missing: $needle" }
}
$engine = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Build-Windows.ps1') -Raw
foreach ($needle in @("'Program'", 'signed = \$false', 'administrative_extract', 'SHA-256')) {
    if ($engine -notmatch $needle) { throw "Build engine contract is missing: $needle" }
}
Write-Host 'PASS: root dependency, runnable-program, and unsigned-installer routes are wired.'
