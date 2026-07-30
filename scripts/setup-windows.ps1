$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $ProjectRoot

try {
    python -m venv .venv
    . .\.venv\Scripts\Activate.ps1

    python -m pip install --upgrade pip
    pip install "torch~=2.8.0" "torchvision~=0.23.0" "torchaudio~=2.8.0" --index-url https://download.pytorch.org/whl/cu128
    pip install -e ".[dev]"
}
finally {
    Pop-Location
}
