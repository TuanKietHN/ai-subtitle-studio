"""PyInstaller collection hook for WhisperX and its dynamic runtime edges."""

from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = collect_all("whisperx", include_py_files=True)

for distribution in (
    "whisperx",
    "faster-whisper",
    "ctranslate2",
    "pyannote.audio",
    "huggingface-hub",
    "transformers",
    "keyring",
):
    try:
        datas += copy_metadata(distribution)
    except Exception:
        # Optional metadata is verified by the frozen smoke-test. Keeping this
        # hook tolerant makes analysis errors readable on partially built envs.
        pass

hiddenimports += [
    "faster_whisper",
    "ctranslate2",
    "pyannote.audio",
    "torch",
    "torchvision",
    "torchaudio",
    "transformers",
    "httpx",
    "keyring.backends.Windows",
]
