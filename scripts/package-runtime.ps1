[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [string]$DistPath,
    [string]$OutputDirectory,
    [string]$SevenZipPath = 'C:\Program Files\7-Zip\7z.exe',
    [ValidateRange(100, 1800)]
    [int]$VolumeSizeMiB = 1800
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $DistPath) {
    $DistPath = Join-Path $Root 'dist\ai-subtitle-studio'
}
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $Root 'release'
}
$ResolvedDist = (Resolve-Path -LiteralPath $DistPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $ResolvedDist 'ai-subtitle-studio.exe') -PathType Leaf)) {
    throw "Invalid frozen runtime: $ResolvedDist"
}
if (-not (Test-Path -LiteralPath $SevenZipPath -PathType Leaf)) {
    throw "7-Zip CLI was not found: $SevenZipPath"
}

New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
$ArchiveBaseName = "AI-Subtitle-Studio-Runtime-v$Version.7z"
$ArchiveBasePath = Join-Path $OutputDirectory $ArchiveBaseName
Get-ChildItem -LiteralPath $OutputDirectory -Filter "$ArchiveBaseName.*" -File | ForEach-Object {
    Remove-Item -LiteralPath $_.FullName -Force
}

$Parent = Split-Path -Parent $ResolvedDist
$Leaf = Split-Path -Leaf $ResolvedDist
Push-Location $Parent
try {
    & $SevenZipPath a -t7z -mx=3 -m0=lzma2 "-v${VolumeSizeMiB}m" $ArchiveBasePath $Leaf
    if ($LASTEXITCODE -ne 0) {
        throw "7-Zip failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$Volumes = @(Get-ChildItem -LiteralPath $OutputDirectory -Filter "$ArchiveBaseName.*" -File | Sort-Object Name)
if (-not $Volumes) {
    throw '7-Zip did not produce any runtime volumes.'
}
$StrictVolumeLimit = 19 * 1024 * 1024 * 100
for ($Index = 0; $Index -lt $Volumes.Count; $Index++) {
    $ExpectedSuffix = '.{0:d3}' -f ($Index + 1)
    if (-not $Volumes[$Index].Name.EndsWith($ExpectedSuffix)) {
        throw "Runtime volume sequence is not contiguous at $($Volumes[$Index].Name)."
    }
    if ($Volumes[$Index].Length -ge $StrictVolumeLimit) {
        throw "Runtime volume exceeds the strict 1.9 GiB limit: $($Volumes[$Index].Name)"
    }
}

$Summary = [ordered]@{
    schema_version = 1
    app_version = $Version
    archive_format = '7z-multivolume'
    volume_size_mib = $VolumeSizeMiB
    installed_size_bytes = (
        Get-ChildItem -LiteralPath $ResolvedDist -File -Recurse |
            Measure-Object -Property Length -Sum
    ).Sum
    volumes = @($Volumes | ForEach-Object {
        [ordered]@{
            name = $_.Name
            size_bytes = $_.Length
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
        }
    })
}
$Staging = Join-Path $Root 'release-staging\build'
New-Item -ItemType Directory -Force $Staging | Out-Null
$Summary | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 (Join-Path $Staging "runtime-package-v$Version.json")
Write-Host "Created $($Volumes.Count) runtime volume(s) in $OutputDirectory"
