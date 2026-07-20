#requires -Version 5.1
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$workflowPath = Join-Path $repoRoot '.github\workflows\windows-installer.yml'
$failures = New-Object 'System.Collections.Generic.List[string]'

function Add-Failure {
    param([Parameter(Mandatory)][string]$Message)
    $script:failures.Add($Message)
}

if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
    Add-Failure -Message "Required workflow is missing: $workflowPath"
}
else {
    $workflowText = Get-Content -LiteralPath $workflowPath -Raw
    $helperMatch = [regex]::Match(
        $workflowText,
        '(?ms)^ {10}function Test-ReleaseUrlForState\(\$releaseObject\) \{\r?\n.*?^ {10}\}')
    if (-not $helperMatch.Success) {
        Add-Failure -Message 'The release URL state helper was not found.'
    }
    else {
        $helperText = [regex]::Replace($helperMatch.Value, '(?m)^ {10}', '')
        $fixtureScript = [scriptblock]::Create(@"
$helperText
`$releaseUrl = 'https://github.com/example/project/releases/tag/windows-msi-test'
`$draft = [pscustomobject]@{
    isDraft = `$true
    url = 'https://github.com/example/project/releases/tag/untagged-deadbeef'
}
`$publishedExact = [pscustomobject]@{
    isDraft = `$false
    url = `$releaseUrl
}
`$publishedWrong = [pscustomobject]@{
    isDraft = `$false
    url = 'https://github.com/example/project/releases/tag/other'
}
if (-not (Test-ReleaseUrlForState `$draft)) {
    throw 'A GitHub draft untagged URL must be accepted before promotion.'
}
if (-not (Test-ReleaseUrlForState `$publishedExact)) {
    throw 'A published release at the canonical tag URL must be accepted.'
}
if (Test-ReleaseUrlForState `$publishedWrong) {
    throw 'A published release at a different URL must be rejected.'
}
"@)
        try {
            & $fixtureScript
        }
        catch {
            Add-Failure -Message "Release URL state regression failed: $($_.Exception.Message)"
        }
    }

    $prePromotionMatch = [regex]::Match(
        $workflowText,
        '(?ms)^ {10}\$releaseReady = \$null\r?\n.*?^ {10}# Re-resolve immediately before promotion')
    if (-not $prePromotionMatch.Success) {
        Add-Failure -Message 'The pre-promotion readiness block was not found.'
    }
    else {
        $prePromotionText = $prePromotionMatch.Value
        if ($prePromotionText -match '\$candidate\.url\s+-eq\s+\$releaseUrl') {
            Add-Failure -Message 'Pre-promotion readiness must not require the final browser URL for a draft.'
        }
        if ($prePromotionText -notmatch '\$candidateUrlMatchesState\s*=\s*Test-ReleaseUrlForState\s+\$candidate') {
            Add-Failure -Message 'Pre-promotion readiness must use the release URL state helper.'
        }
        foreach ($diagnostic in @(
            'release_found=true',
            'url_for_state={3}',
            'release_found=false'
        )) {
            if (-not $prePromotionText.Contains($diagnostic)) {
                Add-Failure -Message "Final-poll diagnostics are missing: $diagnostic"
            }
        }
    }

    if ($workflowText -notmatch '-or -not \(Test-ReleaseUrlForState \$release\)') {
        Add-Failure -Message 'Existing draft recovery must use the release URL state helper.'
    }
    $postPromotionMatch = [regex]::Match(
        $workflowText,
        '(?ms)^ {10}\$publishedRelease = \$null\r?\n.*?^ {10}\$latestAssetsVerified = \$false')
    if (-not $postPromotionMatch.Success `
        -or $postPromotionMatch.Value -notmatch '\$candidate\.url\s+-eq\s+\$releaseUrl') {
        Add-Failure -Message 'Post-promotion verification must still require the canonical tag URL.'
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    throw "Windows release workflow validation failed with $($failures.Count) error(s)."
}

Write-Host 'Windows release workflow static/regression validation: PASS' -ForegroundColor Green
