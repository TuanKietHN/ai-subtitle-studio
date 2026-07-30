$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $ProjectRoot

try {
    git rev-parse --git-dir | Out-Null

    $forbidden = @(
        '(^|/)outputs/.+',
        '\.(sqlite|sqlite3|db)$',
        '(^|/)model_cache/',
        '(^|/)dist/',
        '(^|/)build/',
        '(^|/)release/',
        '\.(pfx|p12)$',
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
