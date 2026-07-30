[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [Parameter(Mandatory = $true)]
    [string]$Owner,
    [Parameter(Mandatory = $true)]
    [string]$Repository,
    [ValidateSet('stable', 'prerelease')]
    [string]$Channel = 'prerelease',
    [string]$IsccPath,
    [string]$SevenZipDirectory = 'C:\Program Files\7-Zip',
    [string]$CertificatePath,
    [string]$Thumbprint
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $IsccPath) {
    foreach ($Candidate in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe'),
        'C:\Program Files\Inno Setup 7\ISCC.exe',
        'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
    )) {
        if (Test-Path -LiteralPath $Candidate -PathType Leaf) {
            $IsccPath = $Candidate
            break
        }
    }
}
if (-not $IsccPath -or -not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
    throw 'Inno Setup compiler was not found. Install Inno Setup 7 or pass -IsccPath.'
}

$Vendor7Zip = Join-Path $Root 'packaging\vendor\7zip'
New-Item -ItemType Directory -Force $Vendor7Zip | Out-Null
foreach ($Name in @('7z.exe', '7z.dll')) {
    $Source = Join-Path $SevenZipDirectory $Name
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Missing 7-Zip installer dependency: $Source"
    }
    Copy-Item -LiteralPath $Source -Destination (Join-Path $Vendor7Zip $Name) -Force
}

$SignatureStatus = if ($Channel -eq 'stable') { 'signed' } else { 'unsigned_prerelease' }
if ($Channel -eq 'stable') {
    & (Join-Path $PSScriptRoot 'audit-dependencies.ps1') -FailOnAllowlisted
}
& (Join-Path $PSScriptRoot 'generate-release-manifest.ps1') `
    -Version $Version -Owner $Owner -Repository $Repository `
    -Channel $Channel -InstallerSignatureStatus $SignatureStatus

$InstallerScript = Join-Path $Root 'packaging\installer\ai-subtitle-studio.iss'
& $IsccPath $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw 'Inno Setup compilation failed.'
}
$InstallerPath = Join-Path $Root "release\AI-Subtitle-Studio-Setup-v$Version.exe"
if (-not (Test-Path -LiteralPath $InstallerPath -PathType Leaf)) {
    throw "Installer output was not created: $InstallerPath"
}

if ($Channel -eq 'stable') {
    if ($CertificatePath) {
        & (Join-Path $PSScriptRoot 'sign-release.ps1') -Path $InstallerPath -CertificatePath $CertificatePath
    }
    elseif ($Thumbprint) {
        & (Join-Path $PSScriptRoot 'sign-release.ps1') -Path $InstallerPath -Thumbprint $Thumbprint
    }
    else {
        throw 'Stable installer builds require -CertificatePath or -Thumbprint.'
    }
}
else {
    Write-Warning 'Installer is unsigned and may only be published as a pre-release.'
}

& (Join-Path $PSScriptRoot 'generate-release-manifest.ps1') `
    -Version $Version -Owner $Owner -Repository $Repository `
    -Channel $Channel -InstallerSignatureStatus $SignatureStatus
Write-Host "Installer candidate ready: $InstallerPath"
