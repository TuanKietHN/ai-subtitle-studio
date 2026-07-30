[CmdletBinding()]
param(
    [string]$RequirementsPath,
    [string]$AllowlistPath,
    [switch]$FailOnAllowlisted
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $RequirementsPath) {
    $RequirementsPath = Join-Path $Root 'packaging\release-requirements.txt'
}
if (-not $AllowlistPath) {
    $AllowlistPath = Join-Path $Root 'packaging\vulnerability-allowlist.json'
}
foreach ($Required in @($RequirementsPath, $AllowlistPath)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw "Dependency audit input was not found: $Required"
    }
}

$Policy = Get-Content -Raw -LiteralPath $AllowlistPath | ConvertFrom-Json
$Advisories = @($Policy.advisories)
$Today = [DateTime]::UtcNow.Date
$SeenIds = @{}
foreach ($Advisory in $Advisories) {
    if (
        -not $Advisory.id -or
        -not $Advisory.package -or
        -not $Advisory.affected_version -or
        -not $Advisory.expires_on -or
        -not $Advisory.rationale
    ) {
        throw 'Every vulnerability exception must include id, package, affected_version, expires_on and rationale.'
    }
    if ($SeenIds.ContainsKey($Advisory.id)) {
        throw "Duplicate vulnerability exception: $($Advisory.id)"
    }
    $SeenIds[$Advisory.id] = $true
    $Expiry = [DateTime]::ParseExact(
        [string]$Advisory.expires_on,
        'yyyy-MM-dd',
        [Globalization.CultureInfo]::InvariantCulture
    )
    if ($Expiry.Date -lt $Today) {
        throw "Vulnerability exception expired on $($Advisory.expires_on): $($Advisory.id)"
    }
}
if ($FailOnAllowlisted -and $Advisories.Count -gt 0) {
    throw "Stable release is blocked by $($Advisories.Count) active vulnerability exception(s)."
}

$Arguments = @(
    '-m', 'pip_audit',
    '-r', $RequirementsPath,
    '--no-deps',
    '--progress-spinner', 'off'
)
foreach ($Advisory in $Advisories) {
    $Arguments += @('--ignore-vuln', [string]$Advisory.id)
    Write-Warning (
        "Temporary security exception $($Advisory.id) for " +
        "$($Advisory.package)==$($Advisory.affected_version) expires $($Advisory.expires_on)."
    )
}
& python @Arguments
if ($LASTEXITCODE -ne 0) {
    throw 'Dependency vulnerability audit failed.'
}
Write-Host "Dependency audit passed with $($Advisories.Count) explicit prerelease exception(s)."
