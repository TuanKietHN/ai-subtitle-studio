[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$Owner,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_.-]+$')]
    [string]$Repository,
    [ValidateSet('stable', 'prerelease')]
    [string]$Channel = 'prerelease',
    [ValidateSet('signed', 'unsigned_prerelease')]
    [string]$InstallerSignatureStatus = 'unsigned_prerelease',
    [string]$ReleaseDirectory,
    [string]$GitCommit
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $ReleaseDirectory) {
    $ReleaseDirectory = Join-Path $Root 'release'
}
$BuildIdentityPath = Join-Path $Root 'release-staging\build\build-identity.json'
$DependencyManifestPath = Join-Path $Root 'release-staging\build\dependency-manifest.txt'
$RuntimePackagePath = Join-Path $Root "release-staging\build\runtime-package-v$Version.json"
foreach ($Required in @($BuildIdentityPath, $DependencyManifestPath, $RuntimePackagePath)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw "Missing release evidence: $Required"
    }
}
$BuildIdentity = Get-Content -Raw $BuildIdentityPath | ConvertFrom-Json
$RuntimePackage = Get-Content -Raw $RuntimePackagePath | ConvertFrom-Json
if ($BuildIdentity.app_version -ne $Version -or $RuntimePackage.app_version -ne $Version) {
    throw 'Release evidence version does not match the requested version.'
}
if (-not $GitCommit) {
    $GitCommit = (& git -C $Root rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $GitCommit) {
        $GitCommit = 'uncommitted'
    }
}
$GitCommit = $GitCommit.Trim()
$Tag = "v$Version"
$NumericVersion = "$($Version.Split('-')[0]).0"
$BaseUrl = "https://github.com/$Owner/$Repository/releases/download/$Tag"
$Artifacts = @()
$VolumeIndex = 0
foreach ($Volume in $RuntimePackage.volumes) {
    $VolumeIndex++
    $Path = Join-Path $ReleaseDirectory $Volume.name
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing runtime volume: $Path"
    }
    $Artifacts += [ordered]@{
        name = $Volume.name
        kind = 'runtime_volume'
        size_bytes = [int64]$Volume.size_bytes
        sha256 = $Volume.sha256
        download_url = "$BaseUrl/$($Volume.name)"
        required = $true
        volume_index = $VolumeIndex
        signature_status = 'not_applicable'
    }
}
$InstallerName = "AI-Subtitle-Studio-Setup-v$Version.exe"
$InstallerPath = Join-Path $ReleaseDirectory $InstallerName
if (Test-Path -LiteralPath $InstallerPath -PathType Leaf) {
    $Installer = Get-Item -LiteralPath $InstallerPath
    $Artifacts += [ordered]@{
        name = $Installer.Name
        kind = 'installer'
        size_bytes = $Installer.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Installer.FullName).Hash.ToLowerInvariant()
        download_url = "$BaseUrl/$($Installer.Name)"
        required = $true
        signature_status = $InstallerSignatureStatus
    }
}
foreach ($Supplemental in @(
    @{ Name = "SBOM-v$Version.json"; Kind = 'sbom' },
    @{ Name = "THIRD-PARTY-NOTICES-v$Version.txt"; Kind = 'notices' }
)) {
    $SupplementalPath = Join-Path $ReleaseDirectory $Supplemental.Name
    if (Test-Path -LiteralPath $SupplementalPath -PathType Leaf) {
        $SupplementalFile = Get-Item -LiteralPath $SupplementalPath
        $Artifacts += [ordered]@{
            name = $SupplementalFile.Name
            kind = $Supplemental.Kind
            size_bytes = $SupplementalFile.Length
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $SupplementalFile.FullName).Hash.ToLowerInvariant()
            download_url = "$BaseUrl/$($SupplementalFile.Name)"
            required = $true
            signature_status = 'not_applicable'
        }
    }
}
$ArchiveBytes = ($RuntimePackage.volumes | Measure-Object -Property size_bytes -Sum).Sum
$Manifest = [ordered]@{
    schema_version = 1
    release = [ordered]@{
        app_version = $Version
        git_commit = $GitCommit
        git_tag = $Tag
        built_at_utc = [DateTime]::UtcNow.ToString('o')
        python_version = $BuildIdentity.python_version
        platform = $BuildIdentity.platform
        whisperx_version = $BuildIdentity.whisperx_version
        torch_version = $BuildIdentity.torch_version
        cuda_runtime_version = $BuildIdentity.cuda_runtime_version
        pyinstaller_version = $BuildIdentity.pyinstaller_version
        dependency_manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $DependencyManifestPath).Hash.ToLowerInvariant()
    }
    channel = $Channel
    minimum_windows_version = '10'
    architecture = 'x64'
    install_scope = 'current_user'
    installed_size_bytes = [int64]$RuntimePackage.installed_size_bytes
    temporary_space_bytes = [int64]($RuntimePackage.installed_size_bytes + $ArchiveBytes)
    artifacts = $Artifacts
}
New-Item -ItemType Directory -Force $ReleaseDirectory | Out-Null
$ManifestPath = Join-Path $ReleaseDirectory "release-manifest-v$Version.json"
$Manifest | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $ManifestPath

$GeneratedValues = Join-Path $Root 'packaging\installer\generated-release-values.iss'
$Lines = @(
    "#define AppVersion `"$Version`"",
    "#define AppVersionNumeric `"$NumericVersion`"",
    "#define ReleaseTag `"$Tag`"",
    "#define ReleaseOwner `"$Owner`"",
    "#define ReleaseRepository `"$Repository`"",
    "#define RuntimeBaseUrl `"$BaseUrl`"",
    "#define RuntimeVolumeCount $($RuntimePackage.volumes.Count)",
    "#define InstalledSizeBytes $($RuntimePackage.installed_size_bytes)",
    "#define TemporarySpaceBytes $($Manifest.temporary_space_bytes)",
    "#define ReleaseChannel `"$Channel`"",
    "#define InstallerSignatureStatus `"$InstallerSignatureStatus`""
)
$VolumeIndex = 0
foreach ($Volume in $RuntimePackage.volumes) {
    $VolumeIndex++
    $Lines += "#define RuntimeVolume${VolumeIndex}Name `"$($Volume.name)`""
    $Lines += "#define RuntimeVolume${VolumeIndex}Sha256 `"$($Volume.sha256)`""
    $Lines += "#define RuntimeVolume${VolumeIndex}Size $($Volume.size_bytes)"
}
$Lines | Set-Content -Encoding utf8 $GeneratedValues

$ChecksumsPath = Join-Path $ReleaseDirectory "SHA256SUMS-v$Version.txt"
$ChecksumFiles = Get-ChildItem -LiteralPath $ReleaseDirectory -File |
    Where-Object { $_.FullName -ne $ChecksumsPath } |
    Sort-Object Name
$ChecksumLines = @($ChecksumFiles | ForEach-Object {
    "$((Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant())  $($_.Name)"
})
$ChecksumLines | Set-Content -Encoding ascii $ChecksumsPath
Write-Host "Generated manifest, installer values and checksums for $Tag"
