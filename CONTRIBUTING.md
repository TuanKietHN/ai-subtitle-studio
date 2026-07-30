# Contributing

The repository is private by default until the owner selects a source license.
Contributions must preserve the project constitution and release gates.

## Development setup

Use Windows and Python 3.11 or 3.13:

```powershell
.\scripts\setup-windows.ps1
python -m pytest tests\unit tests\contract tests\integration tests\gui
```

Do not commit model weights, generated subtitles, local databases, logs,
credentials, signing material, build output, or release assets.

## Change workflow

1. Create a focused branch.
2. Add or update tests before implementation when behavior changes.
3. Run the complete automated suite.
4. Update the matching spec/contract/task documentation.
5. Open a pull request and wait for required CI checks.

Changes touching STT must preserve:

- WhisperX as the engine.
- Mandatory `vad_method="pyannote"` with no public VAD control.
- Config-driven model selection with `large-v3` as default.
- One active GPU STT job.
- Runtime package/GPU information in System Info.

Release signing credentials and GitHub write tokens must never be exposed to
pull-request workflows.
