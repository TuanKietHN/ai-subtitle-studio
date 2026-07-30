from pathlib import Path


def test_whisperx_and_torch_pins_in_pyproject_only():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "whisperx==3.8.6" in pyproject
    assert "checked 2026-07-30" in pyproject
    assert "torch~=2.8.0" in pyproject
    assert "torchvision~=0.23.0" in pyproject
    assert "torchaudio~=2.8.0" in pyproject
    assert not Path("requirements.txt").exists() or "whisperx" not in Path("requirements.txt").read_text(encoding="utf-8").lower()


def test_cuda_torch_install_steps_are_pinned():
    setup_script = Path("scripts/setup-windows.ps1").read_text(encoding="utf-8")
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    expected = '"torch~=2.8.0" "torchvision~=0.23.0" "torchaudio~=2.8.0" --index-url https://download.pytorch.org/whl/cu128'
    assert expected in setup_script
    assert expected in dockerfile
