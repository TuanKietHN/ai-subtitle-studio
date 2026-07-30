[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$')]
    [string]$Version,
    [string]$DependencyManifestPath,
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $DependencyManifestPath) {
    $DependencyManifestPath = Join-Path $Root 'release-staging\build\dependency-manifest.txt'
}
if (-not $OutputPath) {
    $OutputPath = Join-Path $Root "release-staging\build\SBOM-v$Version.json"
}
if (-not (Test-Path -LiteralPath $DependencyManifestPath -PathType Leaf)) {
    throw "Dependency manifest was not found: $DependencyManifestPath"
}

$Components = @()
foreach ($Line in Get-Content -LiteralPath $DependencyManifestPath) {
    if ($Line -match '^([A-Za-z0-9_.-]+)==([^;\s]+)') {
        $Name = $Matches[1]
        $PackageVersion = $Matches[2]
        $NormalizedName = $Name.ToLowerInvariant().Replace('_', '-')
        $Components += [ordered]@{
            type = 'library'
            name = $Name
            version = $PackageVersion
            purl = "pkg:pypi/$NormalizedName@$PackageVersion"
        }
    }
}
$Sbom = [ordered]@{
    bomFormat = 'CycloneDX'
    specVersion = '1.6'
    serialNumber = 'urn:uuid:' + [guid]::NewGuid().ToString()
    version = 1
    metadata = [ordered]@{
        timestamp = [DateTime]::UtcNow.ToString('o')
        component = [ordered]@{
            type = 'application'
            name = 'ai-subtitle-studio'
            version = $Version
            purl = "pkg:pypi/ai-subtitle-studio@$Version"
        }
    }
    components = @($Components | Sort-Object name)
}
$OutputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force $OutputDirectory | Out-Null
$Sbom | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $OutputPath
Write-Host "Generated CycloneDX SBOM with $($Components.Count) components: $OutputPath"
