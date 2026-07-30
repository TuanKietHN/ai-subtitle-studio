[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [string]$FfmpegPath,
    [switch]$Clean,
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ConfigPath = Join-Path $Root 'packaging\release-config.json'
$Config = Get-Content -Raw $ConfigPath | ConvertFrom-Json
$PyProject = Get-Content -Raw (Join-Path $Root 'pyproject.toml')
$ProjectVersionMatch = [regex]::Match($PyProject, '(?m)^version\s*=\s*"([^"]+)"')
if (-not $ProjectVersionMatch.Success -or $ProjectVersionMatch.Groups[1].Value -ne $Version) {
    throw "Version '$Version' must match pyproject.toml version."
}
if ($Config.app_version -ne $Version) {
    throw "Version '$Version' must match packaging/release-config.json."
}

$PythonVersion = (& python -c 'import platform; print(platform.python_version())').Trim()
if ($LASTEXITCODE -ne 0 -or $PythonVersion -ne $Config.python_version) {
    throw "Release requires Python $($Config.python_version); found $PythonVersion."
}

if ($Clean) {
    foreach ($RelativePath in @('build', 'dist', 'release-staging\build')) {
        $Target = [IO.Path]::GetFullPath((Join-Path $Root $RelativePath))
        if ($Target.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $Target)) {
            Remove-Item -LiteralPath $Target -Recurse -Force
        }
    }
}

$VendorFfmpeg = Join-Path $Root $Config.ffmpeg.vendor_path
$VendorDirectory = Split-Path -Parent $VendorFfmpeg
New-Item -ItemType Directory -Force $VendorDirectory | Out-Null
if (-not $FfmpegPath) {
    $FfmpegCommand = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
    if ($FfmpegCommand) {
        $FfmpegPath = $FfmpegCommand.Source
    }
}
if (-not $FfmpegPath -or -not (Test-Path -LiteralPath $FfmpegPath -PathType Leaf)) {
    throw 'ffmpeg.exe is required. Pass its verified path with -FfmpegPath.'
}
Copy-Item -LiteralPath $FfmpegPath -Destination $VendorFfmpeg -Force
$FfmpegVersionOutput = & $VendorFfmpeg -version
$FfmpegExitCode = $LASTEXITCODE
if ($FfmpegExitCode -ne 0) {
    throw 'The supplied ffmpeg executable did not pass `ffmpeg -version`.'
}
$FfmpegVersionLine = $FfmpegVersionOutput | Select-Object -First 1
if ($FfmpegVersionLine -notmatch ('^ffmpeg version ' + [regex]::Escape($Config.ffmpeg.version) + '(\s|-)')) {
    throw "Expected ffmpeg $($Config.ffmpeg.version), found: $FfmpegVersionLine"
}
Write-Host $FfmpegVersionLine

& python -m pip check
if ($LASTEXITCODE -ne 0) {
    throw 'pip check failed.'
}
& (Join-Path $PSScriptRoot 'audit-dependencies.ps1')
if (-not $SkipTests) {
    & python -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw 'Source tests failed.'
    }
}

$Staging = Join-Path $Root 'release-staging\build'
New-Item -ItemType Directory -Force $Staging | Out-Null
& python -m pip freeze --all | Set-Content -Encoding utf8 (Join-Path $Staging 'dependency-manifest.txt')
& (Join-Path $PSScriptRoot 'generate-sbom.ps1') `
    -Version $Version `
    -DependencyManifestPath (Join-Path $Staging 'dependency-manifest.txt') `
    -OutputPath (Join-Path $Staging "SBOM-v$Version.json")
if ($Clean) {
    & python -m PyInstaller --noconfirm --clean (Join-Path $Root 'packaging\ai-subtitle-studio.spec')
}
else {
    & python -m PyInstaller --noconfirm (Join-Path $Root 'packaging\ai-subtitle-studio.spec')
}
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller build failed.'
}

$DistPath = Join-Path $Root 'dist\ai-subtitle-studio'
& (Join-Path $PSScriptRoot 'smoke-frozen.ps1') -DistPath $DistPath
if ($LASTEXITCODE -ne 0) {
    throw 'Frozen smoke validation failed.'
}

$Inventory = Get-ChildItem -LiteralPath $DistPath -File -Recurse | ForEach-Object {
    [pscustomobject]@{
        path = $_.FullName.Substring($DistPath.Length + 1).Replace('\', '/')
        size_bytes = $_.Length
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
    }
}
$Inventory | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $Staging 'runtime-inventory.json')

$FfmpegHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $VendorFfmpeg).Hash.ToLowerInvariant()
$BuildIdentity = [ordered]@{
    schema_version = 1
    app_version = $Version
    python_version = $PythonVersion
    platform = $Config.platform
    whisperx_version = $Config.whisperx_version
    torch_version = $Config.torch_version
    cuda_runtime_version = $Config.cuda_runtime_version
    pyinstaller_version = $Config.pyinstaller_version
    ffmpeg_version = $Config.ffmpeg.version
    ffmpeg_sha256 = $FfmpegHash
    built_at_utc = [DateTime]::UtcNow.ToString('o')
}
$BuildIdentity | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $Staging 'build-identity.json')
Write-Host "Release runtime ready: $DistPath"
