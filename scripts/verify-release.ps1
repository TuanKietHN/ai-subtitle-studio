[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [string]$ReleaseDirectory,
    [string]$SignToolPath
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $ReleaseDirectory) {
    $ReleaseDirectory = Join-Path $Root 'release'
}
$VerificationDirectory = [IO.Path]::GetFullPath($ReleaseDirectory)
if (-not (Test-Path -LiteralPath $VerificationDirectory -PathType Container)) {
    throw "Release directory does not exist: $VerificationDirectory"
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
    $Path = [IO.Path]::GetFullPath((Join-Path $VerificationDirectory $Matches[2]))
    $VerificationPrefix = $VerificationDirectory.TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    ) + [IO.Path]::DirectorySeparatorChar
    if (-not $Path.StartsWith($VerificationPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Checksum references a path outside the release directory: $($Matches[2])"
    }
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
