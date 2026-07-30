[CmdletBinding(DefaultParameterSetName = 'Certificate')]
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Path,
    [Parameter(ParameterSetName = 'Certificate', Mandatory = $true)]
    [string]$CertificatePath,
    [Parameter(ParameterSetName = 'Thumbprint', Mandatory = $true)]
    [ValidatePattern('^[0-9A-Fa-f]{40}$')]
    [string]$Thumbprint,
    [string]$TimestampUrl = 'http://timestamp.digicert.com',
    [string]$SignToolPath
)

$ErrorActionPreference = 'Stop'
if (-not $SignToolPath) {
    $SignToolPath = Get-ChildItem -LiteralPath 'C:\Program Files (x86)\Windows Kits\10\bin' -Filter signtool.exe -File -Recurse |
        Where-Object FullName -Match '\\x64\\' |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $SignToolPath -or -not (Test-Path -LiteralPath $SignToolPath -PathType Leaf)) {
    throw 'Could not locate the x64 Windows SDK SignTool.'
}

$ImportedCertificate = $null
$SigningThumbprint = $Thumbprint
try {
    if ($PSCmdlet.ParameterSetName -eq 'Certificate') {
        $ResolvedCertificatePath = (Resolve-Path -LiteralPath $CertificatePath).Path
        $ImportArguments = @{
            FilePath = $ResolvedCertificatePath
            CertStoreLocation = 'Cert:\CurrentUser\My'
        }
        if ($env:AI_SUBTITLE_SIGNING_PASSWORD) {
            $ImportArguments.Password = ConvertTo-SecureString `
                -String $env:AI_SUBTITLE_SIGNING_PASSWORD `
                -AsPlainText `
                -Force
        }
        $ImportedCertificate = Import-PfxCertificate @ImportArguments
        if (-not $ImportedCertificate -or -not $ImportedCertificate.HasPrivateKey) {
            throw 'The imported signing certificate does not contain a private key.'
        }
        $SigningThumbprint = $ImportedCertificate.Thumbprint
        Remove-Item Env:AI_SUBTITLE_SIGNING_PASSWORD -ErrorAction SilentlyContinue
    }

    foreach ($Target in $Path) {
        $ResolvedTarget = (Resolve-Path -LiteralPath $Target).Path
        $Arguments = @(
            'sign',
            '/fd', 'SHA256',
            '/td', 'SHA256',
            '/tr', $TimestampUrl,
            '/sha1', $SigningThumbprint,
            $ResolvedTarget
        )
        & $SignToolPath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Authenticode signing failed: $ResolvedTarget"
        }
        & $SignToolPath verify /pa /all $ResolvedTarget
        if ($LASTEXITCODE -ne 0) {
            throw "Authenticode verification failed: $ResolvedTarget"
        }
    }
}
finally {
    if ($ImportedCertificate) {
        $StorePath = "Cert:\CurrentUser\My\$($ImportedCertificate.Thumbprint)"
        if (Test-Path -LiteralPath $StorePath) {
            Remove-Item -LiteralPath $StorePath -Force
        }
    }
}
