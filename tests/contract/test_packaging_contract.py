import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pyinstaller_spec_wires_hooks_resources_metadata_and_safe_options():
    spec = (ROOT / "packaging" / "ai-subtitle-studio.spec").read_text(encoding="utf-8")
    assert "packaging\" / \"hooks" in spec
    assert "runtime_environment.py" in spec
    assert "resources\" / \"models.json" in spec
    assert "THIRD_PARTY_NOTICES.md" in spec
    assert "copy_metadata" in spec
    assert "ffmpeg.exe" in spec
    assert '"whisperx"' in spec
    assert "icon=str(ASSETS / \"app.ico\")" in spec
    assert "version=str(ASSETS / \"version-info.txt\")" in spec
    assert spec.count("upx=False") >= 2
    assert "console=False" in spec


def test_whisperx_hook_covers_dynamic_runtime_dependencies():
    hook = (ROOT / "packaging" / "hooks" / "hook-whisperx.py").read_text(encoding="utf-8")
    for dependency in (
        "collect_all",
        "copy_metadata",
        "faster_whisper",
        "ctranslate2",
        "pyannote.audio",
        "torchvision",
        "torchaudio",
        "keyring.backends.Windows",
    ):
        assert dependency in hook


def test_packaging_assets_and_exclusion_rules_exist():
    icon = ROOT / "packaging" / "assets" / "app.ico"
    assert icon.read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert (ROOT / "packaging" / "assets" / "version-info.txt").is_file()
    smoke = (ROOT / "scripts" / "smoke-frozen.ps1").read_text(encoding="utf-8")
    for forbidden in ("IsRequiredWhisperxVadAsset", "pytorch_model", "safetensors", ".ckpt", ".onnx", ".sqlite"):
        assert forbidden in smoke
    config = json.loads((ROOT / "packaging" / "release-config.json").read_text(encoding="utf-8"))
    assert config["bundle"] == {
        "name": "ai-subtitle-studio",
        "entry_executable": "ai-subtitle-studio.exe",
        "mode": "onedir",
        "console": False,
        "upx": False,
    }
