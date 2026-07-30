$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $ProjectRoot

try {
    git rev-parse --git-dir | Out-Null

    $forbidden = @(
        '(^|/)outputs/.+',
        '\.(sqlite|sqlite3|db)(-.+)?$',
        '(^|/)model_cache/',
        '(^|/)models_cache/',
        '(^|/)dist/',
        '(^|/)build/',
        '(^|/)release/',
        '(^|/)release-staging/',
        '(^|/)packaging/vendor/',
        '\.(exe|dll|msi|msix|appx|appxbundle|cab|iso|zip|tar|tgz)$',
        '\.7z(\.\d+)?$',
        '\.(mp4|mkv|mov|avi|webm|wav|mp3|flac|m4a|srt|vtt|ass)$',
        '\.(pfx|p12|pem|key|cer|crt|jks|keystore)$',
        '\.(log|dmp)$',
        '(^|/)(credentials|service-account).+\.json$',
        '(^|/)secrets/',
        '(^|/)signing/',
        '(^|/)\.env($|\.)'
    )

    $tracked = @(git ls-files)
    $violations = foreach ($path in $tracked) {
        foreach ($pattern in $forbidden) {
            if ($path -match $pattern -and $path -ne 'outputs/.gitkeep') {
                $path
                break
            }
        }
    }

    if ($violations) {
        throw "Forbidden generated/private files are tracked:`n$($violations -join "`n")"
    }

    Write-Host "Repository hygiene check passed for $($tracked.Count) tracked files."
}
finally {
    Pop-Location
}
