# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata

ROOT = Path.cwd()
ASSETS = ROOT / "packaging" / "assets"
VENDOR_FFMPEG = ROOT / "packaging" / "vendor" / "ffmpeg" / "bin" / "ffmpeg.exe"

block_cipher = None

if not VENDOR_FFMPEG.is_file():
    raise SystemExit(
        f"Missing pinned ffmpeg input: {VENDOR_FFMPEG}. "
        "Run scripts/build-release.ps1 with -FfmpegPath."
    )

datas = [
    (str(ROOT / "resources" / "models.json"), "resources"),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    (str(ROOT / "README.md"), "."),
]
for distribution in ("ai-subtitle-studio", "whisperx", "torch", "faster-whisper"):
    try:
        datas += copy_metadata(distribution)
    except Exception:
        pass

a = Analysis(
    [str(ROOT / "src" / "ai_subtitle_studio" / "app.py")],
    pathex=[str(ROOT / "src")],
    binaries=[(str(VENDOR_FFMPEG), "bin")],
    datas=datas,
    hiddenimports=[
        "ai_subtitle_studio",
        "whisperx",
        "faster_whisper",
        "ctranslate2",
        "pyannote.audio",
        "torch",
        "torchvision",
        "torchaudio",
        "httpx",
        "keyring.backends.Windows",
    ],
    hookspath=[str(ROOT / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "runtime_hooks" / "runtime_environment.py")],
    excludes=[
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "tests",
        "whisper_model_weights",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ai-subtitle-studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ASSETS / "app.ico"),
    version=str(ASSETS / "version-info.txt"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ai-subtitle-studio",
)
