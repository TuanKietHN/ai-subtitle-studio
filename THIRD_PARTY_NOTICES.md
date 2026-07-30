# Third-Party Notices

AI Subtitle Studio distributes or depends on third-party software. This file is
an inventory for release preparation, not a replacement for the license texts
shipped with each dependency.

| Component | Purpose | License / source |
|---|---|---|
| Python | Runtime | Python Software Foundation License — https://www.python.org/psf/ |
| PySide6 / Qt for Python | Desktop UI | LGPL-3.0-or-later / GPL options — https://doc.qt.io/qtforpython-6/licenses.html |
| WhisperX | Transcription/alignment | BSD-2-Clause — https://pypi.org/project/whisperx/ |
| PyTorch, TorchVision, TorchAudio | ML/CUDA runtime | BSD-style licenses — https://pytorch.org/ |
| faster-whisper | Whisper inference | MIT — https://github.com/SYSTRAN/faster-whisper |
| CTranslate2 | Inference runtime | MIT — https://github.com/OpenNMT/CTranslate2 |
| Pyannote Audio | VAD/audio pipeline | MIT — https://github.com/pyannote/pyannote-audio |
| httpx | HTTP client | BSD-3-Clause — https://www.python-httpx.org/ |
| keyring | OS credential integration | MIT — https://github.com/jaraco/keyring |
| PyInstaller | Frozen application builder | GPL-2.0-or-later with bootloader exception — https://pyinstaller.org/ |
| Inno Setup | Windows installer builder | Inno Setup license — https://jrsoftware.org/files/is/license.txt |
| FFmpeg | Audio extraction | LGPL/GPL depending on selected build — https://ffmpeg.org/legal.html |

The release build must generate a complete dependency inventory and include all
license files required by the exact wheels and FFmpeg build used. The FFmpeg
download URL, version, configuration/license variant, SHA-256, and corresponding
source offer/link must be recorded in release metadata.
