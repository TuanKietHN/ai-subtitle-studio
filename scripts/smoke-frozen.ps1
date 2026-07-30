[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DistPath,
    [ValidateRange(10, 600)]
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
$ResolvedDist = (Resolve-Path -LiteralPath $DistPath).Path
$Executable = Join-Path $ResolvedDist 'ai-subtitle-studio.exe'
$Ffmpeg = Join-Path $ResolvedDist '_internal\bin\ffmpeg.exe'
$Models = Join-Path $ResolvedDist '_internal\resources\models.json'
foreach ($Required in @($Executable, $Ffmpeg, $Models)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw "Frozen runtime is missing required file: $Required"
    }
}

$Forbidden = Get-ChildItem -LiteralPath $ResolvedDist -File -Recurse | Where-Object {
    $RelativePath = $_.FullName.Substring($ResolvedDist.Length + 1).Replace('\', '/')
    $IsRequiredWhisperxVadAsset = $RelativePath -eq '_internal/whisperx/assets/pytorch_model.bin'
    $IsPrivateData = $_.Name -match '(?i)(\.sqlite3?$|\.env$|credentials.*\.json$)'
    $IsCachedModelWeight = (
        $RelativePath -match '(?i)(^|/)(models?|model_cache|huggingface|snapshots?)(/|$)' -and
        $_.Name -match '(?i)(pytorch_model.*\.bin$|model.*\.safetensors$|\.ckpt$|\.onnx$)'
    )
    $IsPrivateData -or ($IsCachedModelWeight -and -not $IsRequiredWhisperxVadAsset)
}
if ($Forbidden) {
    throw "Frozen runtime contains forbidden private/model data: $($Forbidden.FullName -join ', ')"
}

$SmokeRoot = Join-Path ([IO.Path]::GetTempPath()) ("ai-subtitle-studio-smoke-" + [guid]::NewGuid().ToString('N'))
$Profile = Join-Path $SmokeRoot 'profile'
$LocalAppData = Join-Path $SmokeRoot 'local'
New-Item -ItemType Directory -Force $Profile, $LocalAppData | Out-Null
$PreviousProfile = $env:USERPROFILE
$PreviousLocalAppData = $env:LOCALAPPDATA
try {
    $env:USERPROFILE = $Profile
    $env:LOCALAPPDATA = $LocalAppData
    $Process = Start-Process -FilePath $Executable -ArgumentList '--smoke-test' -PassThru -WindowStyle Hidden
    if (-not $Process.WaitForExit($TimeoutSeconds * 1000)) {
        $Process.Kill()
        throw "Frozen smoke-test exceeded $TimeoutSeconds seconds."
    }
    if ($Process.ExitCode -ne 0) {
        $SmokeLog = Join-Path $LocalAppData 'AI Subtitle Studio\logs\ai-subtitle-studio.log'
        if (Test-Path -LiteralPath $SmokeLog) {
            Write-Error (Get-Content -Raw -LiteralPath $SmokeLog) -ErrorAction Continue
        }
        throw "Frozen smoke-test exited with code $($Process.ExitCode)."
    }
    $ExpectedData = Join-Path $LocalAppData 'AI Subtitle Studio'
    if (-not (Test-Path -LiteralPath $ExpectedData -PathType Container)) {
        throw "Frozen smoke-test did not initialize user data at $ExpectedData."
    }
    if ($ExpectedData.StartsWith($ResolvedDist, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Frozen runtime wrote persistent data inside the installation directory.'
    }
    $FfmpegVersionOutput = & $Ffmpeg -version
    $FfmpegExitCode = $LASTEXITCODE
    if ($FfmpegExitCode -ne 0) {
        throw 'Bundled ffmpeg failed its version check.'
    }
    Write-Host ($FfmpegVersionOutput | Select-Object -First 1)
}
finally {
    $env:USERPROFILE = $PreviousProfile
    $env:LOCALAPPDATA = $PreviousLocalAppData
    $ResolvedSmokeRoot = [IO.Path]::GetFullPath($SmokeRoot)
    $ResolvedTempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    if ($ResolvedSmokeRoot.StartsWith($ResolvedTempRoot, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $ResolvedSmokeRoot)) {
        Remove-Item -LiteralPath $ResolvedSmokeRoot -Recurse -Force
    }
}
Write-Host "Frozen smoke-test passed: $ResolvedDist"
