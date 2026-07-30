# Implementation Plan: Desktop Subtitle Studio Release Readiness

**Branch**: `001-desktop-subtitle-studio` | **Updated**: 2026-07-30 | **Spec**: [spec.md](./spec.md) | **Target release**: `v0.1.0`

**Input**: Hoàn thiện ứng dụng hiện có, đưa source lên GitHub an toàn, đóng gói Windows, cung cấp installer dễ dùng và tự động hóa phát hành qua GitHub Releases.

## Summary

Hoàn thiện AI Subtitle Studio từ trạng thái source/test chạy được thành sản phẩm Windows có thể cài đặt và phát hành lặp lại. Kế hoạch giữ nguyên Python + PySide6 + WhisperX + Torch CUDA, sửa các blocker của môi trường frozen, chuẩn hóa nơi lưu dữ liệu người dùng, bundle `ffmpeg`, bổ sung logging/chẩn đoán, hoàn thiện PyInstaller `onedir`, tạo Inno Setup online installer, thiết lập Git/GitHub/CI/CD, kiểm thử trên máy Windows sạch và phát hành các asset có checksum.

Do Torch CUDA tạo runtime nhiều gigabyte trong khi mỗi GitHub Release asset phải nhỏ hơn 2 GiB, artifact chính cho người dùng là một online installer nhỏ. Installer tải các archive runtime được chia dưới 1.9 GiB, kiểm SHA-256, giải nén vào thư mục cài đặt theo user, tạo shortcut và hỗ trợ uninstall/upgrade. Whisper model không nằm trong installer; app tải model ở lần sử dụng đầu.

## Current Baseline

- Source tree, service layer, PySide6 UI, persistence, worker queue và tests đã tồn tại.
- Lần kiểm tra gần nhất ngày 2026-07-30: `86 passed` trên Python 3.13.7.
- `whisperx==3.8.6`, Torch/TorchVision/TorchAudio `2.8.x` CUDA 12.8 đang chạy trong môi trường phát triển.
- PyPI vẫn ghi nhận `3.8.6` là bản WhisperX stable mới nhất ngày 2026-07-30; `3.8.7rc1` là pre-release và không được dùng.
- Thư mục `.git` đang tồn tại nhưng không có `HEAD`/`config`; repository chưa được khởi tạo hợp lệ.
- PyInstaller spec hiện chỉ là scaffold: chưa thu thập import động WhisperX, chưa bundle `ffmpeg`, chưa có icon/version metadata/runtime hook.
- `outputs/` có dữ liệu người dùng nhưng chưa được ignore.
- App đang mặc định đặt SQLite/output/model cache dựa trên source/bundle root; model cache setting chưa được truyền vào `TranscriptionRequest`.
- Chưa có GitHub workflows, installer, release manifest, checksum, third-party notices, code signing hoặc clean-machine validation.

## Technical Context

**Language/Version**: Python 3.11 là interpreter chuẩn để tạo release artifact. Python 3.11 và 3.13 được dùng trong test matrix nhẹ vì metadata WhisperX hỗ trợ `>=3.10,<3.14`. Không trộn package global với release venv.

**Primary Dependencies**: PySide6, `whisperx==3.8.6`, `torch~=2.8.0`, `torchvision~=0.23.0`, `torchaudio~=2.8.0`, httpx, keyring, PyInstaller 6.x, Inno Setup 6.x, ffmpeg, pytest và pytest-qt.

**Dependency Reproducibility**:

- `pyproject.toml` tiếp tục là source dependency cấp cao.
- Tạo release lock cho Python 3.11/Windows x64, pin chính xác package build/runtime và lưu hash khi công cụ hỗ trợ.
- Cài Torch/TorchVision/TorchAudio từ index CUDA 12.8 trước, sau đó cài phần còn lại.
- Release workflow xác nhận `pip check`, version runtime và dependency manifest trước khi build.
- Không build release từ Python/package global của máy phát triển.

**Storage**:

- QSettings: tùy chọn không bí mật.
- Windows Credential Manager/keyring: API key.
- `%LOCALAPPDATA%\AI Subtitle Studio\data`: SQLite và state.
- `%LOCALAPPDATA%\AI Subtitle Studio\models`: model cache mặc định.
- `%LOCALAPPDATA%\AI Subtitle Studio\logs`: rolling logs và crash diagnostics.
- `%USERPROFILE%\Documents\AI Subtitle Studio\Outputs`: output mặc định.
- Environment overrides hiện có được giữ cho test, Docker và hỗ trợ kỹ thuật.

**Packaging**:

- PyInstaller `onedir`, `console=False`, `upx=False`.
- Không bundle Whisper model.
- Bundle `models.json`, icon, version metadata, licenses/notices và `ffmpeg.exe`.
- Custom PyInstaller hooks/runtime hook thu thập WhisperX và dependency import động, package metadata, Qt plugins và native DLL cần thiết.
- Loại test, cache, model weights, import library `.lib`, module Qt không dùng và tài liệu phát triển khỏi runtime.
- Runtime `onedir` được đóng thành archive nhiều volume, mỗi volume mục tiêu tối đa 1.8 GiB và bắt buộc dưới 1.9 GiB.

**Installer**:

- Inno Setup online installer x64, per-user, `PrivilegesRequired=lowest`.
- Cài dưới `%LOCALAPPDATA%\Programs\AI Subtitle Studio`.
- Tải archive từ GitHub Release qua HTTPS, kiểm SHA-256 bắt buộc trước khi giải nén.
- Tạo Start Menu shortcut, optional desktop shortcut, Add/Remove Programs entry và uninstaller.
- Stable `AppId` để upgrade tại chỗ; không xóa dữ liệu người dùng khi uninstall trừ khi người dùng chủ động chọn.

**CI/CD**:

- Pull request/push CI dùng Windows runner và dependency test nhẹ để chạy nhanh.
- Full release build chạy trên clean, protected Windows x64 self-hosted runner có tối thiểu 40 GiB trống; không chạy mã PR không tin cậy trên runner này.
- Release workflow chỉ chạy từ tag `v*` hoặc `workflow_dispatch` có approval.
- Workflow tạo draft release, upload installer/runtime parts/manifest/checksums/notices, chạy verification rồi mới publish.
- `GITHUB_TOKEN` chỉ được cấp `contents: write` trong release job.

**Target Platform**: Windows 10/11 x64, NVIDIA GPU và driver tương thích runtime CUDA được bundle. Windows ARM và CPU-only STT nằm ngoài `v0.1.0`.

**Performance/UX Goals**:

- UI responsive trong toàn bộ pipeline.
- Installer hiển thị tổng dung lượng tải, tiến độ và lỗi mạng có thể retry.
- App khởi động lần đầu không yêu cầu terminal hoặc Python cài sẵn.
- App hiển thị thông báo rõ ràng nếu thiếu NVIDIA GPU/driver hoặc thiếu dung lượng cho model.
- Startup smoke test của frozen app hoàn tất dưới 30 giây trên máy validation sau khi antivirus cache đã ổn định.

**Security and Privacy**:

- Không commit API key, SQLite, output người dùng, model, log hoặc build artifact.
- Installer/runtime downloads phải có SHA-256; phát hành stable yêu cầu Authenticode cho installer và app executable.
- Nếu chưa có signing certificate, chỉ được publish GitHub pre-release kèm cảnh báo SmartScreen.
- API key không xuất hiện trong log, error, release artifact hoặc test fixture thật.
- Dependency audit và secret scan là release gates.

**Scale/Scope**: Một người dùng local; một GPU STT job; runtime nhiều phần nhưng một installer đầu vào; không có auto-updater trong `v0.1.0`; cập nhật qua installer phiên bản mới.

## Constitution Check

*GATE: Phải pass trước khi thực hiện và kiểm tra lại sau thiết kế.*

- **WhisperX stable pin**: PASS. `whisperx==3.8.6` vẫn là stable mới nhất được kiểm tra trên PyPI ngày 2026-07-30; pre-release bị loại.
- **Mandatory VAD**: PASS. Constitution 1.0.1, spec, contract, code và tests cùng yêu cầu Pyannote VAD bắt buộc qua `vad_method="pyannote"`; không có public VAD field/toggle và không truyền keyword `vad_filter` lỗi thời.
- **Model config**: PASS. `large-v3` vẫn là mặc định; `models.json` được bundle như resource; model weights không bundle.
- **System Info**: PASS. Frozen build phải copy package metadata để `importlib.metadata.version()` trả version runtime thật.
- **Interfaces**: PASS. Các fix packaging/data paths không bypass `STTEngine` hoặc `TranslationProvider`.
- **Worker execution**: PASS. Logging, model download, ffmpeg và installer không đưa công việc nặng lên Qt UI thread.
- **Single GPU STT job**: PASS. Frozen/GPU manual test phải xác nhận GPU lock vẫn serialize STT.

**Post-design re-check**: PASS. Release artifact contract, research addendum, data model và quickstart giữ nguyên toàn bộ invariant; G0 đã hoàn tất ngày 2026-07-30.

## Release Architecture

```text
Git tag v0.1.0
    |
    v
Protected release workflow
    |
    +--> test + dependency/secret/license checks
    |
    +--> PyInstaller onedir runtime
    |       |
    |       +--> frozen smoke tests
    |       +--> archive volumes < 1.9 GiB
    |
    +--> release-manifest.json + SHA256SUMS.txt
    |
    +--> Inno Setup online installer
            |
            +--> Authenticode sign
            +--> clean-VM install/upgrade/uninstall tests
            |
            v
       Draft GitHub Release
            |
            +--> manual GPU/API acceptance
            |
            v
       Publish Release
```

## Project Structure

### Documentation

```text
README.md
CHANGELOG.md
SECURITY.md
CONTRIBUTING.md
THIRD_PARTY_NOTICES.md
specs/001-desktop-subtitle-studio/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── release-artifacts.md
│   └── ...existing contracts
└── tasks.md
```

### Source and Packaging

```text
src/ai_subtitle_studio/
├── app.py
├── paths.py                    # frozen/dev resource and user-data paths
├── logging_config.py           # rolling file logs/startup diagnostics
└── ...existing modules

packaging/
├── ai-subtitle-studio.spec
├── hooks/
│   └── hook-whisperx.py
├── runtime_hooks/
├── installer/
│   └── ai-subtitle-studio.iss
├── assets/
│   ├── app.ico
│   └── version-info.txt
└── release-manifest.schema.json

scripts/
├── setup-windows.ps1
├── build-release.ps1
├── smoke-frozen.ps1
├── package-runtime.ps1
├── generate-release-manifest.ps1
└── verify-release.ps1

.github/
├── workflows/
│   ├── ci.yml
│   └── release-windows.yml
├── dependabot.yml
└── release.yml
```

**Structure Decision**: Giữ một desktop package hiện có; chỉ thêm lớp path/logging và toolchain phát hành. Không tạo client/server, service cloud hoặc updater riêng trong `v0.1.0`.

## Implementation Phases and Exit Gates

### Phase G0 — Constitution and STT Contract Reconciliation

1. Dùng workflow constitution để xác nhận invariant theo API stable hiện tại: Pyannote VAD bắt buộc thông qua `vad_method="pyannote"`, không có UI/config/CLI/request field cho phép tắt hoặc đổi VAD.
2. Amend constitution với lý do kỹ thuật và Sync Impact Report; không giảm yêu cầu chất lượng hay khả năng kiểm soát invariant.
3. Đồng bộ `spec.md`, `research.md`, `contracts/stt-engine-contract.md`, `tasks.md`, quickstart và test wording.
4. Xác nhận wrapper là điểm duy nhất chọn `vad_method` và mọi đường transcribe đều đi qua wrapper.
5. Chạy contract tests chứng minh không có VAD field công khai và `load_model` luôn nhận `vad_method="pyannote"`.

**Exit gate G0**:

- Constitution, spec, contract, task và code mô tả cùng một API/invariant.
- Không còn yêu cầu literal không được WhisperX 3.8.6 sử dụng.
- Constitution Check được đánh giá lại thành PASS trước Phase R0.

### Phase R0 — Repository Hygiene and Release Governance

1. Cập nhật `.gitignore` cho `outputs/**`, `.env*`, installer staging, release archives, local signing files và generated manifests.
2. Giữ `.gitkeep` nếu cần thư mục output rỗng; không commit các `.srt` hiện có.
3. Chạy secret scan và rà history trước commit đầu tiên.
4. Chọn trạng thái repository mặc định là **private**. Chỉ chuyển public sau khi chủ sở hữu chọn license nguồn và hoàn tất third-party notices.
5. Thêm README release-oriented, CHANGELOG, SECURITY, CONTRIBUTING và notices.
6. Chuẩn hóa version về một source trong `pyproject.toml`; app, PyInstaller, installer, tag và manifest đọc cùng version.
7. Khởi tạo Git bằng `git init -b main`, kiểm tra staged files, tạo initial commit sạch, rồi gắn remote GitHub.

**Exit gate R0**:

- `git status` sạch sau commit.
- Không có output/model/database/API key/build artifact trong index.
- Version thống nhất.
- Repository có tài liệu cài đặt, quyền riêng tư và hỗ trợ tối thiểu.

### Phase R1 — Runtime and Frozen-App Correctness

1. Thêm path resolver phân biệt source resource, frozen resource và user-writable data.
2. Di chuyển default SQLite/model/log/output khỏi bundle root.
3. Truyền `model_cache_dir` và GPU selection vào transcription request/runtime environment đúng contract.
4. Resolve `ffmpeg` theo thứ tự: explicit setting, bundled executable, PATH; hiển thị nguồn đang dùng trong System Info.
5. Thêm rolling file logging, startup exception dialog và đường dẫn “Mở thư mục log”.
6. Copy distribution metadata để System Info đọc đúng app/WhisperX/faster-whisper version trong frozen build.
7. Thêm frozen smoke mode không mở event loop vô hạn: kiểm resource, writable paths, imports, SQLite migration, keyring, Qt plugin, ffmpeg và GPU diagnostics.
8. Thêm tests cho path resolver, model cache propagation, bundled ffmpeg resolution, logging redaction và smoke mode.

**Exit gate R1**:

- Full source tests pass.
- Frozen smoke contract pass.
- App không ghi vào `_MEIPASS`, `_internal` hoặc `Program Files`.
- Model cache setting được dùng thật bởi WhisperX.
- Startup failure tạo log và thông báo có thể hành động.

### Phase R2 — Reproducible PyInstaller Runtime

1. Tạo clean Python 3.11 release venv.
2. Pin release dependencies và kiểm `pip check`.
3. Hoàn thiện spec/hook cho import động WhisperX, Pyannote, Faster-Whisper, CTranslate2, Torch, keyring backend, httpx certificates và package metadata.
4. Bundle `models.json`, icon/version metadata, ffmpeg và notices.
5. `upx=False`; chỉ include Qt modules/plugins được dùng.
6. Không include model weights, cache, `.lib` development artifacts, tests hoặc sample outputs.
7. Build bằng script duy nhất có `--clean`, deterministic staging directory và fail-fast.
8. Ghi file inventory, dependency versions, build timestamp UTC, commit SHA và sizes.
9. Chạy frozen smoke test từ `dist`, sau đó chạy trên Windows Sandbox/VM không có Python.

**Exit gate R2**:

- Executable mở UI trên clean Windows VM.
- WhisperX import thành công từ frozen runtime.
- `models.json`, Qt platform plugin, keyring và bundled ffmpeg hoạt động.
- Không có model hoặc dữ liệu cá nhân trong bundle.
- Runtime inventory không có file đơn lẻ vượt giới hạn phát hành.

### Phase R3 — Installer and Large Runtime Delivery

1. Đóng `onedir` thành multi-volume 7z, mục tiêu 1.8 GiB/volume.
2. Sinh `release-manifest.json` và `SHA256SUMS.txt` từ đúng commit/build.
3. Inno Setup installer lấy URL, size và SHA-256 từ generated include/manifest.
4. Installer tải các volume qua HTTPS, kiểm checksum bắt buộc, retry khi mạng lỗi và hủy sạch file tạm.
5. Cài per-user, tạo shortcut/uninstaller, giữ data/model/output khi upgrade/uninstall mặc định.
6. Kiểm đủ dung lượng trước tải và trước giải nén.
7. Sign `ai-subtitle-studio.exe`, installer và uninstaller; verify signature sau signing.
8. Test fresh install, repair/reinstall, upgrade từ bản trước, uninstall và interrupted download.

**Exit gate R3**:

- Người dùng chỉ cần tải `AI-Subtitle-Studio-Setup-v0.1.0.exe`.
- Mọi runtime part < 1.9 GiB và có SHA-256.
- Installer cài không cần admin và chạy app không cần Python hệ thống.
- Corrupt/missing asset bị từ chối trước cài.
- Upgrade giữ settings, credentials, database, model và output.

### Phase R4 — GitHub CI/CD and Repository Controls

1. `ci.yml` chạy format/static checks phù hợp, unit/contract/integration/gui tests trên Windows.
2. Tách test dependency nhẹ để CI không tải Torch CUDA nhiều GB cho mọi PR.
3. Thêm dependency review, secret scan và Dependabot.
4. Bật branch protection: required CI, không force-push `main`, review trước merge khi có cộng tác viên.
5. `release-windows.yml` chỉ nhận protected tag/manual approval; build full trên clean self-hosted runner.
6. Workflow tạo draft release, không overwrite immutable asset cùng version.
7. Upload installer, runtime volumes, manifest, checksums, notices, SBOM và provenance/attestation khi khả dụng.
8. Verify toàn bộ asset tải lại từ draft release trước publish.
9. Không cấp write token hoặc signing secret cho pull request jobs.

**Exit gate R4**:

- PR/push CI xanh.
- Release workflow tái tạo artifact từ tag.
- Asset names/version/checksum khớp contract.
- Self-hosted runner không chạy untrusted code.
- GitHub Release vẫn ở draft cho đến khi R5 pass.

### Phase R5 — Product Acceptance and Public Release

1. Clean Windows 10/11 x64 install test.
2. NVIDIA GPU test với ít nhất hai `.mp4`: download model, queue tuần tự, cancel/retry/recovery, English SRT.
3. Google và DeepSeek test bằng credential test riêng, không đưa key vào log.
4. Vietnamese/bilingual edit/export test.
5. No-GPU behavior test.
6. Subtitle Edit integration test nếu executable được cấu hình.
7. Antivirus/SmartScreen/signature observation và installer download retry test.
8. Review release notes: prerequisites, download size, disk size, first-model download, known issues, privacy, uninstall.
9. Publish pre-release nếu chưa ký số hoặc còn known issue không chặn; chỉ đánh dấu stable/latest khi mọi stable gate pass.

**Exit gate R5 / Definition of Done**:

- Gate G0 đã đồng bộ constitution/spec/contract với VAD API stable.
- 86+ automated tests pass và test mới cho release correctness pass.
- Source repo sạch, không có secret/dữ liệu người dùng/binary lớn.
- Installer một-click cài thành công trên clean Windows.
- GPU STT, translation, edit, export, persistence và recovery pass manual acceptance.
- Installer/app được ký số cho stable release.
- GitHub Release có installer, runtime parts, SHA256, manifest, SBOM/notices và release notes.
- Latest release URL trong README tải đúng installer.
- Previous release vẫn có thể cài lại để rollback.

## Git and GitHub Publication Sequence

1. Hoàn thành R0-R2 trên local branch.
2. Khởi tạo repository và commit source-only.
3. Tạo GitHub repository private, thêm remote và push `main`.
4. Bật Actions/branch protection/secrets/environment.
5. Merge release tooling qua pull request đã pass CI.
6. Tạo tag annotated `v0.1.0-rc.1`; workflow tạo draft/pre-release.
7. Hoàn tất R3-R5 trên release candidate.
8. Sửa lỗi bằng commit/tag RC mới; không thay asset của tag cũ.
9. Khi stable gates pass, tạo tag `v0.1.0`, publish release và cập nhật README latest-download link.

## Versioning, Rollback and Artifact Policy

- Semantic Versioning: `MAJOR.MINOR.PATCH`; RC dùng `-rc.N`.
- Một tag tương ứng đúng một commit và một bộ asset immutable.
- Không rebuild rồi upload đè cùng tên/version.
- Release lỗi được đánh dấu pre-release/deprecated; không xóa ngay nếu cần audit.
- Rollback bằng installer của release trước; data schema migration phải backward-safe hoặc có backup trước migration.
- Installer tạo backup SQLite trước upgrade có migration.
- Model cache và output không thuộc installer ownership.

## Risk Register

| Risk | Impact | Mitigation | Gate |
|---|---|---|---|
| WhisperX stable tương lai đổi API VAD | Contract/code có thể lệch constitution | Bắt buộc amend constitution/contract trước khi nâng version | G0 |
| WhisperX import động bị thiếu trong bundle | STT chỉ lỗi sau khi người dùng chạy | Custom hook + frozen import/STT smoke | R2 |
| Torch CUDA runtime vượt 2 GiB | Không upload được một asset | Multi-volume <1.9 GiB + online installer | R3 |
| GitHub runner thiếu disk/time | Release build thất bại | Protected self-hosted clean runner >=40 GiB | R4 |
| App ghi vào bundle/Program Files | Mất dữ liệu hoặc permission error | QStandardPaths/path resolver + clean VM tests | R1 |
| ffmpeg thiếu hoặc sai license | Audio extraction lỗi/pháp lý | Pinned binary + SHA256 + notices/source link | R2 |
| Unsigned executable bị SmartScreen | Người dùng không tin/cài khó | Authenticode stable gate; unsigned chỉ pre-release | R3/R5 |
| API key lọt log/repo | Security incident | Keyring + redaction tests + secret scan | R0/R1/R4 |
| Model cache setting không có tác dụng | Tải model sai nơi, đầy disk | Propagate into request + integration test | R1 |
| Release asset bị hỏng/đổi | Cài đặt lỗi hoặc supply-chain risk | SHA-256, signature, immutable tag/assets | R3/R4 |
| Public repo chưa có license | Quyền sử dụng source không rõ | Private-by-default; public gate cần owner license decision | R0 |

## Complexity Tracking

| Decision | Why Required | Simpler Alternative Rejected |
|---|---|---|
| PyInstaller `onedir` | Native ML/Qt runtime lớn, dễ debug và test | `onefile` phải giải nén nhiều GB mỗi lần và khó chẩn đoán |
| Online installer + runtime volumes | GitHub giới hạn mỗi asset dưới 2 GiB nhưng Torch CUDA lớn hơn | Commit binary/Git LFS hoặc yêu cầu người dùng ghép file thủ công |
| Self-hosted release runner | Full CUDA build cần disk lớn và môi trường kiểm soát | Build full trên mọi PR/hosted runner tốn thời gian và dễ hết disk |
| Separate light CI dependencies | Tests phần lớn dùng mocks/contracts | Tải Torch CUDA nhiều GB cho mỗi PR không tạo thêm tín hiệu tương xứng |

Không có vi phạm constitution. Độ phức tạp bổ sung chỉ nằm ở delivery toolchain và được yêu cầu trực tiếp bởi kích thước runtime, giới hạn GitHub và trải nghiệm cài đặt không dùng dòng lệnh.
