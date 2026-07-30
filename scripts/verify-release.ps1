[CmdletBinding(DefaultParameterSetName = 'Local')]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [Parameter(ParameterSetName = 'Local')]
    [switch]$Local,
    [Parameter(ParameterSetName = 'GitHubDraft')]
    [switch]$GitHubDraft,
    [string]$Owner,
    [string]$Repository,
    [string]$ReleaseDirectory,
    [string]$SignToolPath
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $ReleaseDirectory) {
    $ReleaseDirectory = Join-Path $Root 'release'
}
$VerificationDirectory = $ReleaseDirectory
$TemporaryDraftDirectory = $null
try {
    if ($GitHubDraft) {
        if (-not $Owner -or -not $Repository) {
            throw '-Owner and -Repository are required with -GitHubDraft.'
        }
        $Gh = Get-Command gh.exe -ErrorAction SilentlyContinue
        if (-not $Gh) {
            throw 'GitHub CLI is required for draft verification.'
        }
        $TemporaryDraftDirectory = Join-Path ([IO.Path]::GetTempPath()) ("ai-subtitle-release-" + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Force $TemporaryDraftDirectory | Out-Null
        & $Gh.Source release download "v$Version" --repo "$Owner/$Repository" --dir $TemporaryDraftDirectory
        if ($LASTEXITCODE -ne 0) {
            throw 'Could not download GitHub draft release assets.'
        }
        $VerificationDirectory = $TemporaryDraftDirectory
    }

    $ManifestPath = Join-Path $VerificationDirectory "release-manifest-v$Version.json"
    $env:PYTHONPATH = Join-Path $Root 'src'
    & python -m ai_subtitle_studio.release_verifier --release-dir $VerificationDirectory --manifest $ManifestPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Release manifest verification failed.'
    }

    $ChecksumsPath = Join-Path $VerificationDirectory "SHA256SUMS-v$Version.txt"
    if (-not (Test-Path -LiteralPath $ChecksumsPath -PathType Leaf)) {
        throw "Missing checksum file: $ChecksumsPath"
    }
    foreach ($Line in Get-Content -LiteralPath $ChecksumsPath) {
        if ($Line -notmatch '^([0-9a-f]{64})  (.+)$') {
            throw "Invalid checksum line: $Line"
        }
        $Path = Join-Path $VerificationDirectory $Matches[2]
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Checksum references missing asset: $($Matches[2])"
        }
        $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
        if ($Actual -ne $Matches[1]) {
            throw "Checksum mismatch: $($Matches[2])"
        }
    }

    $Manifest = Get-Content -Raw $ManifestPath | ConvertFrom-Json
    if ($Manifest.channel -eq 'stable') {
        $Installer = $Manifest.artifacts | Where-Object kind -eq 'installer'
        if (-not $Installer -or $Installer.signature_status -ne 'signed') {
            throw 'Stable releases require a signed installer.'
        }
        if (-not $SignToolPath) {
            $SignToolPath = Get-ChildItem -LiteralPath 'C:\Program Files (x86)\Windows Kits\10\bin' -Filter signtool.exe -File -Recurse |
                Where-Object FullName -Match '\\x64\\' |
                Sort-Object FullName -Descending |
                Select-Object -First 1 -ExpandProperty FullName
        }
        if (-not $SignToolPath) {
            throw 'SignTool is required to verify stable artifacts.'
        }
        & $SignToolPath verify /pa /all (Join-Path $VerificationDirectory $Installer.name)
        if ($LASTEXITCODE -ne 0) {
            throw 'Installer Authenticode verification failed.'
        }
    }
    Write-Host "Release verification passed: $VerificationDirectory"
}
finally {
    if ($TemporaryDraftDirectory) {
        $ResolvedTemporary = [IO.Path]::GetFullPath($TemporaryDraftDirectory)
        $ResolvedTempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
        if ($ResolvedTemporary.StartsWith($ResolvedTempRoot, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $ResolvedTemporary)) {
            Remove-Item -LiteralPath $ResolvedTemporary -Recurse -Force
        }
    }
}
